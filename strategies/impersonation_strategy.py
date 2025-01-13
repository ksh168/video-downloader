from strategies.base_strategy import DownloadStrategy
from typing import Dict, Any
import yt_dlp
from flask import current_app as app
import traceback
from utils.impersonate import random_impersonate_target

class ImpersonationDownloadStrategy(DownloadStrategy):
    """Download with browser impersonation"""
    def download(self, url: str, opts: Dict[str, Any], ydl_class=yt_dlp.YoutubeDL) -> Dict[str, Any]:
        try:
            opts["impersonate"] = random_impersonate_target()
            return super().download(url, opts, ydl_class)
        except Exception as e:
            app.logger.error(f"Impersonation setup failed: {str(e)}")
            app.logger.error(traceback.format_exc())
            return {"success": False, "error": f"Impersonation failed: {str(e)}"} 