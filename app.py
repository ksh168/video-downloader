from dotenv import load_dotenv

from utils.url_sanitizer import sanitize_url

load_dotenv()

import os

from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

from flask_socketio import SocketIO

from utils.upload_to_s3 import upload_to_s3_and_get_url
from utils.cleanup_s3 import init_cleanup_scheduler

from downloader.video_downloader import VideoDownloader
from routers.video_router import init_video_routes
from routers.socket_router import init_socket_routes
from utils.logger import setup_logging


def create_app():
    app = Flask(__name__, template_folder="templates")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    # Set up rate limiting
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
    )

    # Initialize SocketIO
    socketio = SocketIO(app)
    init_socket_routes(socketio)

    # Register blueprints
    video_routes = init_video_routes(app, socketio)
    app.register_blueprint(video_routes)

    # Set up logging
    setup_logging(app)

    # Initialize the cleanup scheduler
    init_cleanup_scheduler()

    return app, socketio


app, socketio = create_app()


# Add this route before the download API route
@app.route("/", methods=["GET"])
def index():
    """
    Render the main download page
    """
    return render_template("index.html")


def download_video_task(url, client_id):
    try:
        downloader = VideoDownloader()
        # Add client_id to the downloader instance
        downloader.client_id = client_id
        result = downloader.download(url)

        # Check if download was successful
        if not result["success"]:
            app.logger.error(f"Download failed: {result.get('error', 'Unknown error')}")
        else:
            app.logger.info(f"Successfully downloaded video: {result['filename']}")

        return result
    except Exception as e:
        app.logger.exception("Unexpected error during download")
        return {"success": False, "error": str(e), "filename": None}


@app.route("/download", methods=["POST"])
# @limiter.limit("100 per hour")  # Additional rate limiting for this specific endpoint
def download_video_api():
    """
    API endpoint to download a video and return the file.

    Expected JSON payload:
    {
        "url": "video_url_to_download",
        "client_id": "unique_client_id"
    }
    """
    # Log the request
    app.logger.info(f"Download request received from {get_remote_address()}")

    # Get request data
    data = request.get_json()
    if not data:
        app.logger.warning("Empty request body")
        return jsonify({"success": False, "error": "Invalid request"}), 400

    # # Validate API key
    # api_key = data.get("api_key")
    # if not api_key or api_key != os.environ.get("HARDCODED_API_KEY"):
    #     app.logger.warning(
    #         f"Invalid API key attempt from {get_remote_address()} with key: {api_key}"
    #     )
    #     return jsonify({"success": False, "error": "Invalid API key"}), 403

    # Extract URL
    url = sanitize_url(data.get("url"))
    if not url:
        app.logger.warning("Download request without URL")
        return jsonify({"success": False, "error": "No URL provided"}), 400

    client_id = data.get("client_id")
    if not client_id:
        return jsonify({"success": False, "error": "No client ID provided"}), 400

    download_req = download_video_task(url, client_id)

    # Check if download was successful
    if not download_req.get("success"):
        return (
            jsonify(
                {"success": False, "error": download_req.get("error", "Unknown error")}
            ),
            500,
        )

    # Upload the downloaded file to blob Storage
    filename = download_req.get("filename")
    if filename:
        download_url = upload_to_s3_and_get_url(
            filename,
            os.path.basename(filename),
            download_directory=download_req.get("download_directory"),
        )
        if download_url:
            return jsonify({"success": True, "download_url": download_url})

    return jsonify({"success": False, "error": "Failed to upload file"}), 500


# Error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify(error="Rate limit exceeded", description=str(e.description)), 429


@app.errorhandler(500)
def internal_error_handler(e):
    app.logger.error(f"Unhandled exception: {str(e)}")
    return jsonify(error="Internal server error"), 500


if __name__ == "__main__":
    socketio.run(app, port=3001, debug=False)
