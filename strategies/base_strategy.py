from typing import Dict, Any
import yt_dlp
import traceback
from flask import current_app as app

class DownloadStrategy:
    """Base class for download strategies"""
    def download(self, url: str, opts: Dict[str, Any], ydl_class=yt_dlp.YoutubeDL) -> Dict[str, Any]:
        try:
            with ydl_class(opts) as ydl:
                # Download with progress hooks
                info_dict = ydl.extract_info(url, download=True)
                return {
                    "success": True,
                    "info_dict": info_dict,
                    "ydl": ydl
                }
        except Exception as e:
            app.logger.error(f"Download failed in {self.__class__.__name__}: {str(e)}")
            app.logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)} 