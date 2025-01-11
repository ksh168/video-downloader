from strategies.base_strategy import DownloadStrategy
from typing import Dict, Any
import yt_dlp
import os
from flask import current_app as app
import traceback

class ProxyDownloadStrategy(DownloadStrategy):
    """Download through a proxy"""
    def download(self, url: str, opts: Dict[str, Any], ydl_class=yt_dlp.YoutubeDL) -> Dict[str, Any]:
        try:
            proxy_url = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
            if not proxy_url:
                raise ValueError("No proxy URL configured in environment variables")
            
            opts["proxy"] = proxy_url
            return super().download(url, opts, ydl_class)
        except Exception as e:
            app.logger.error(f"Proxy setup failed: {str(e)}")
            app.logger.error(traceback.format_exc())
            return {"success": False, "error": f"Proxy failed: {str(e)}"} 