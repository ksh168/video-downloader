import requests
import os
from typing import Optional, Dict, Any
import yt_dlp
import json


def try_download_with_proxy(
    url: str, ydl_opts: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Attempt to download using ScrapingDog proxy service
    """
    try:
        # First get the webpage content through ScrapingDog
        scraping_response = requests.get(
            os.getenv("PROXY_API_URL"),
            params={
                "api_key": os.getenv("PROXY_API_KEY"),
                "url": url,
                "render": "true",
                "premium": "true",
            },
            timeout=60,
        )

        if not scraping_response.ok:
            print(f"ScrapingDog API failed with status {scraping_response.status_code}")
            return None

        # Now try the download with the original URL but using the ScrapingDog cookies/headers
        if "set-cookie" in scraping_response.headers:
            ydl_opts.update(
                {
                    "http_headers": {
                        **ydl_opts.get("http_headers", {}),
                        "Cookie": scraping_response.headers["set-cookie"],
                    }
                }
            )

        # Attempt download with the enhanced options
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            if info_dict:
                return {
                    "success": True,
                    "info_dict": info_dict,
                    "method": "scraping_service",
                }

    except Exception as e:
        print(f"Scraping service download failed: {str(e)}")

    return None
