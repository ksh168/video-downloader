import os
import uuid
import subprocess
import sys
from typing import Dict, Optional, Any
from flask import current_app as app
from flask_socketio import SocketIO
from strategies.base_strategy import DownloadStrategy
from strategies.direct_strategy import DirectDownloadStrategy
from strategies.impersonation_strategy import ImpersonationDownloadStrategy
from strategies.proxy_strategy import ProxyDownloadStrategy

class VideoDownloader:
    def __init__(self, socketio: SocketIO, output_dir: Optional[str] = None):
        self.socketio = socketio
        self.strategies = [
            DirectDownloadStrategy(),
            ImpersonationDownloadStrategy(),
            # ProxyDownloadStrategy()
        ]
        base_output_dir = output_dir or os.path.join(os.getcwd(), "downloads")
        unique_session_id = str(uuid.uuid4())[:8]
        self.output_dir = os.path.join(base_output_dir, unique_session_id)
        os.makedirs(self.output_dir, exist_ok=True)
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Check if ffmpeg is installed, provide installation instructions if not."""
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self._print_ffmpeg_instructions()

    def _print_ffmpeg_instructions(self):
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

    def download(self, url: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Try downloading using different strategies until one succeeds"""
        default_opts = {
            "format": "best",
            "outtmpl": os.path.join(self.output_dir, "%(title).50s.%(ext)s"),
            # "merge_output_format": "mp4",
            "verbose": True,
            "progress_hooks": [self._progress_hook],
            "postprocessor_hooks": [self._progress_hook],
            "nooverwrites": True,
            "windowsfilenames": True,
            # "quiet": False,
            # "noprogress": False,
        }

        if options:
            default_opts.update(options)

        for strategy in self.strategies:
            strategy_name = strategy.__class__.__name__
            app.logger.info(f"Attempting download with {strategy_name}")
            result = strategy.download(url, default_opts)

            if result["success"]:
                app.logger.info(f"Download successful with {strategy_name}")
                return self._create_success_response(result["info_dict"], 
                                                  result["ydl"], url)
            
            app.logger.warning(f"{strategy_name} failed: {result.get('error')}")

        return {
            "success": False,
            "error": "All download strategies failed",
            "url": url
        }

    def _create_success_response(self, info_dict: Dict, ydl: Any, url: str) -> Dict[str, Any]:
        return {
            "success": True,
            "title": info_dict.get("title"),
            "filename": ydl.prepare_filename(info_dict),
            "url": url,
            "extractor": info_dict.get("extractor"),
            "download_directory": self.output_dir,
        }

    def _progress_hook(self, d: Dict[str, Any]) -> None:
        """Handle download progress updates"""
        if hasattr(self, 'client_id'):
            if d['status'] == 'downloading':
                downloaded_bytes = d.get('downloaded_bytes', 0)
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                
                if total_bytes:
                    percent = (downloaded_bytes / total_bytes) * 100
                    app.logger.debug(f"Progress: {percent:.1f}% ({downloaded_bytes}/{total_bytes} bytes)")
                    self.socketio.emit(
                        'download_progress',
                        {'progress': percent},
                        room=self.client_id
                    )
            elif d['status'] == 'finished':
                app.logger.info("Download finished")
                self.socketio.emit(
                    'download_progress',
                    {'progress': 100},
                    room=self.client_id
                )