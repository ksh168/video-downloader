import os
import sys
import uuid
import subprocess
import traceback
import yt_dlp
from typing import Dict, Optional, Any
from utils.random_impersonate import random_impersonate_target
from flask import current_app

from utils.redis.redis_connection import RedisClient
from strategies.direct_hit_strategy import DirectHitDownloadStrategy
from strategies.impersonate_strategy import ImpersonateDownloadStrategy


class VideoDownloader:
    """
    Class for downloading videos from a given URL.
    """

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the VideoDownloader with a custom or default output directory.

        :param output_dir: Directory to save downloaded videos.
                            If None, creates a 'downloads' folder in current directory.
        """
        self.logger = get_logger()
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

    def _progress_hook(self, d):
        if d["status"] == "downloading":
            progress = d.get("_percent_str", "0%").strip()
            speed = d.get("_speed_str", "0KiB/s").strip()
            eta = d.get("_eta_str", "N/A")
            total_bytes = d.get("total_bytes_estimate", d.get("total_bytes", 0))
            downloaded = d.get("downloaded_bytes", 0)

            # Format the progress message
            progress_msg = (
                f"\n[download] {progress} of {self._format_bytes(total_bytes)} "
                f"at {speed} ETA {eta}"
            )
            print(progress_msg)

    def _format_bytes(self, bytes):
        """Convert bytes to human readable string"""
        if bytes is None:
            return "N/A"
        for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
            if abs(bytes) < 1024.0:
                return f"{bytes:3.2f}B" if unit == "" else f"{bytes:3.2f}{unit}B"
            bytes /= 1024.0
        return f"{bytes:.2f}YiB"

    def check_and_increment_retry_count(self, url: str) -> Dict[str, Any]:
        """Check and increment the retry count for a given URL"""
        self.redis_client = RedisClient()
        retry_count = self.redis_client.get_retry_count(url)
        if retry_count >= int(os.getenv("MAX_URL_RETRIES")):
            return {"allowed": False, "error": "Max retry attempts exceeded"}
        else:
            self.redis_client.increment_retry_count(url)
            return {"allowed": True, "retry_count": retry_count}

    def download(self, url: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Download a video from the given URL by first attempting a direct hit
        and then falling back to impersonation if needed.

        :param url: URL of the video to download.
        :param options: Optional dictionary of yt-dlp download options.
        :return: Dictionary containing download information.
        """
        # Default download options WITHOUT impersonation
        default_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]",
            "outtmpl": os.path.join(self.output_dir, "%(title).50s.%(ext)s"),
            "merge_output_format": "mp4",
            "verbose": True,
            "progress_hooks": [self._progress_hook],
            "nooverwrites": True,
            "windowsfilenames": True,  # Ensure Windows compatibility
        }

        # Update default options with user-provided options, if any
        if options:
            default_opts.update(options)

        # Create strategy instances
        direct_strategy = DirectHitDownloadStrategy(self.logger)
        impersonate_strategy = ImpersonateDownloadStrategy(self.logger)

        # First attempt: try direct hit
        try:
            info_dict = direct_strategy.download(url, default_opts.copy())
            return {
                "success": True,
                "title": info_dict.get("title"),
                "filename": info_dict.get("filename"),
                "url": url,
                "extractor": info_dict.get("extractor"),
                "download_directory": self.output_dir,
            }
        except Exception as e_direct:
            self.logger.error(f"Direct download failed: {str(e_direct)}")
            self.logger.info("Retrying with impersonation...")

        # Second attempt: try impersonation strategy
        try:
            info_dict = impersonate_strategy.download(url, default_opts.copy())
            return {
                "success": True,
                "title": info_dict.get("title"),
                "filename": info_dict.get("filename"),
                "url": url,
                "extractor": info_dict.get("extractor"),
                "download_directory": self.output_dir,
            }
        except Exception as e_impersonate:
            self.logger.error(f"Error downloading video with impersonation: {str(e_impersonate)}")
            self.logger.error(traceback.format_exc())
            return {"success": False, "error": str(e_impersonate), "url": url}


def get_logger():
    try:
        return current_app.logger
    except RuntimeError:
        import logging

        logger = logging.getLogger("video_downloader")
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger


def download_video_task(url, client_id=None):
    logger = get_logger()
    try:
        downloader = VideoDownloader()

        retry_count = downloader.check_and_increment_retry_count(url)
        if not retry_count["allowed"]:
            logger.error(retry_count["error"])
            return {"success": False, "error": retry_count["error"], "allowed": False}

        result = downloader.download(url)

        # Check if download was successful
        if not result["success"]:
            logger.error(f"Download failed: {result.get('error', 'Unknown error')}")
        else:
            logger.info(f"Successfully downloaded video: {result['filename']}")

        return result
    except Exception as e:
        logger.exception("Unexpected error during download")
        return {"success": False, "error": str(e), "filename": None}
