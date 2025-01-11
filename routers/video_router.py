from flask import Blueprint, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from services.video_service import VideoService
from utils.url_sanitizer import sanitize_url
from flask import current_app as app

def init_video_routes(app, socketio):
    video_router = Blueprint('video', __name__)
    video_service = VideoService(socketio)
    
    @video_router.route("/", methods=["GET"])
    def index():
        """Render the main download page"""
        return render_template("index.html")

    @video_router.route("/download", methods=["POST"])
    def download_video():
        """API endpoint to download a video"""
        app.logger.info(f"Download request received from {get_remote_address()}")

        data = request.get_json()
        if not data:
            app.logger.warning("Empty request body")
            return jsonify({"success": False, "error": "Invalid request"}), 400

        url = sanitize_url(data.get("url"))
        if not url:
            app.logger.warning("Download request without URL")
            return jsonify({"success": False, "error": "No URL provided"}), 400

        client_id = data.get("client_id")
        if not client_id:
            return jsonify({"success": False, "error": "No client ID provided"}), 400

        return video_service.handle_download_request(url, client_id)

    @video_router.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify(error="Rate limit exceeded", description=str(e.description)), 429

    @video_router.errorhandler(500)
    def internal_error_handler(e):
        app.logger.error(f"Unhandled exception: {str(e)}")
        return jsonify(error="Internal server error"), 500 

    return video_router 