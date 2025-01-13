from dotenv import load_dotenv
from utils.logger import setup_logging
from utils.queue_consumer import consume_messages
from utils.queue_producer import publish_message
from utils.url_sanitizer import sanitize_url

load_dotenv()

import os

from flask import Flask, request, jsonify, render_template
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

from utils.cleanup_s3 import init_cleanup_scheduler


app = Flask(__name__, template_folder=os.path.join(os.getcwd(), "templates"))

# Fix for running behind a proxy (like Nginx)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Set up logging
setup_logging(app)

# Initialize the cleanup scheduler
if os.environ.get("ENABLE_S3_CLEANUP", "False").lower() == "true":
    init_cleanup_scheduler()

if os.environ.get("ENABLE_QUEUE_CONSUMER", "False").lower() == "true":
    from utils.queue_consumer import consume_messages
    consume_messages()  # This will now run in a separate thread


# Add this route before the download API route
@app.route("/", methods=["GET"])
def index():
    """
    Render the main download page
    """
    return render_template("index.html")


@app.route("/enqueue_download", methods=["POST"])
def enqueue_video_download():
    """
    API endpoint to download a video and return the file.

    Expected JSON payload:
    {
        "url": "video_url_to_download",
        "client_id": "unique_client_id"
    }
    """
    ip_address = get_remote_address()
    # Log the request
    app.logger.info(f"Download request received from {ip_address}")

    # Get request data
    data = request.get_json()
    if not data:
        app.logger.warning("Empty request body")
        return jsonify({"success": False, "error": "Invalid request"}), 400

    # Extract URL
    url = sanitize_url(data.get("url"))
    if not url:
        app.logger.warning("Download request without URL")
        return jsonify({"success": False, "error": "No URL provided"}), 400

    publish_message({"url": url, "ip_address": ip_address})

    return jsonify({"success": True, "message": "Video download request enqueued"}), 200


@app.errorhandler(500)
def internal_error_handler(e):
    app.logger.error(f"Unhandled exception: {str(e)}")
    return jsonify(error="Internal server error"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3001, debug=False)
