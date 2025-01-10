import traceback
from dotenv import load_dotenv

from utils.impersonate import random_impersonate_target
from utils.url_sanitizer import sanitize_url

load_dotenv()

import os
import sys
import uuid
import logging
from logging.handlers import RotatingFileHandler

import yt_dlp
import subprocess
from typing import Dict, Optional, Any

from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

# from threading import Thread
from flask_socketio import SocketIO

from utils.upload_to_s3 import upload_to_s3_and_get_url
from flask_socketio import join_room
from utils.cleanup_s3 import init_cleanup_scheduler

# from prometheus_flask_exporter import PrometheusMetrics


# Configure logging
def setup_logging(app):
    """Set up logging for the application."""
    # Ensure logs directory exists
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Configure file handler
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"), maxBytes=10240, backupCount=10
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        )
    )
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)


class VideoDownloader:
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the VideoDownloader with a custom or default output directory.

        :param output_dir: Directory to save downloaded videos.
                            If None, creates a 'downloads' folder in current directory.
        """
        base_output_dir = output_dir or os.path.join(os.getcwd(), "downloads")

        # Create a unique subdirectory for each download session
        unique_session_id = str(uuid.uuid4())[:8]  # Use first 8 characters of UUID
        self.output_dir = os.path.join(base_output_dir, unique_session_id)

        # Ensure the unique directory is created
        os.makedirs(self.output_dir, exist_ok=True)

        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """
        Check if ffmpeg is installed, provide installation instructions if not.
        """
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("\n⚠️ WARNING: FFmpeg is not installed!")
            if sys.platform == "darwin":
                print("Install FFmpeg using Homebrew:")
                print("1. Install Homebrew (if not already installed):")
                print(
                    '   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
                )
                print("2. Install FFmpeg:")
                print("   brew install ffmpeg")
            elif sys.platform.startswith("linux"):
                print("Install FFmpeg using package manager:")
                print("For Ubuntu/Debian: sudo apt-get install ffmpeg")
                print("For Fedora: sudo dnf install ffmpeg")
            elif sys.platform == "win32":
                print("Download FFmpeg from: https://ffmpeg.org/download.html")
                print("Add FFmpeg to your system PATH")

            print("\nFFmpeg is required for merging video and audio streams.")
            print("Please install it and try again.\n")

    def download(
        self, url: str, options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Download a video from the given URL.

        :param url: URL of the video to download
        :param options: Optional dictionary of yt-dlp download options
        :return: Dictionary containing download information
        """
        # Default download options with headers and bypass configurations
        default_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]",
            "outtmpl": os.path.join(self.output_dir, "%(title)s.%(ext)s"),
            "merge_output_format": "mp4",
            # "no_color": True,
            "verbose": True,
            "progress_hooks": [self._progress_hook],
            "nooverwrites": True,
            # "http_headers": {
            #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            #     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            #     "Accept-Language": "en-US,en;q=0.5",
            #     "Referer": "https://www.google.com/",
            # },
            # "extractor_args": {
            #     "youtube": {
            #         "player_client": ["android"],
            #         "player_skip": ["webpage"],
            #     }
            # },
            # "force_generic_extractor": True,
            # "ignoreerrors": True,
            # "retries": 10,
            # "fragment_retries": 10,
            # "skip_unavailable_fragments": True,
            # "extract_flat": True,
            "impersonate": random_impersonate_target(),
            # "referer": url,  # Use the video URL as referer
            # "playlist_items": None,
            # "throttled_rate": "1M",  # Limit download speed to avoid detection
            # "sleep_interval": 5,  # Add delay between requests
            # "max_sleep_interval": 10,
            # "force_ipv4": False,
        }

        # Update default options with user-provided options
        if options:
            default_opts.update(options)

        try:
            with yt_dlp.YoutubeDL(default_opts) as ydl:
                # Extract video information
                info_dict = ydl.extract_info(url, download=True)
                app.logger.info(f"Downloaded video info: {info_dict}")
                # Prepare return information
                return {
                    "success": True,
                    "title": info_dict.get("title"),
                    "filename": ydl.prepare_filename(info_dict),
                    "url": url,
                    "extractor": info_dict.get("extractor"),
                    "download_directory": self.output_dir,
                }

        except Exception as e:
            app.logger.error(f"Error downloading video: {str(e)}")
            app.logger.error(traceback.format_exc())
            return {"success": False, "error": str(e), "url": url}

    def _progress_hook(self, d: Dict[str, Any]) -> None:
        """
        Internal progress hook for download tracking.
        """
        if d["status"] == "finished":
            print(f"Download complete: {d['filename']}")
            socketio.emit("download_progress", {"percent": 100}, room=self.client_id)

        elif d["status"] == "downloading":
            downloaded_bytes = d.get("downloaded_bytes", 0)
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            if total_bytes > 0:
                percent = downloaded_bytes / total_bytes * 100
                print(f"Downloading: {percent:.1f}%")
                socketio.emit(
                    "download_progress", {"percent": percent}, room=self.client_id
                )


def download_video(url: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function for quick video downloads.

    :param url: URL of the video to download
    :param output_dir: Optional directory to save the video
    :return: Download result dictionary
    """
    downloader = VideoDownloader(output_dir)
    return downloader.download(url)


# app = Flask(__name__)
app = Flask(__name__, template_folder=os.path.join(os.getcwd(), "templates"))

# Fix for running behind a proxy (like Nginx)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Set up rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "300 per hour"],
    storage_uri="memory://",
)

# Set up logging
setup_logging(app)

# Initialize the cleanup scheduler
init_cleanup_scheduler()


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


socketio = SocketIO(app)


@socketio.on("register_client")
def handle_client_registration(data):
    client_id = data.get("clientId")
    if client_id:
        # Join a room specific to this client
        join_room(client_id)


# def init_metrics(app):
#     metrics = PrometheusMetrics(app)
#     metrics.info('app_info', 'Application info', version='1.0.0')


if __name__ == "__main__":
    socketio.run(app, port=3001, debug=False)
