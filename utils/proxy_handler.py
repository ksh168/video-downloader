import requests
import os
from typing import Optional, Dict, Any
import yt_dlp
from .proxy_config import PROXY_PROVIDERS, PROXY_PROVIDER_ORDER, MAX_PROXY_RETRIES

def try_download_with_proxy(
    url: str, ydl_opts: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Attempt to download using various proxy services in sequence
    """
    for attempt in range(MAX_PROXY_RETRIES):
        for provider_name in PROXY_PROVIDER_ORDER:
            provider = PROXY_PROVIDERS.get(provider_name)
            if not provider:
                print(f"Provider {provider_name} not found in configuration")
                continue

            print(
                f"Attempting download with {provider_name} (attempt {attempt + 1}/{MAX_PROXY_RETRIES})"
            )
            result = _try_provider(url, ydl_opts.copy(), provider, provider_name)

            if result:
                print(f"Successfully downloaded using {provider_name}")
                return result

            print(f"Failed to download with {provider_name}")

    print("All proxy download attempts failed")
    return None


def _try_provider(
    url: str, ydl_opts: Dict[str, Any], provider: Dict[str, Any], provider_name: str
) -> Optional[Dict[str, Any]]:
    """
    Attempt download using a specific proxy provider
    """
    api_key = provider["api_key_env"]
    if not api_key:
        print("Missing PROXY_API_KEY environment variable")
        return None

    try:
        # Get webpage content through proxy service for initial headers/cookies
        params = {"api_key": api_key, "url": url, **provider.get("params", {})}
        
        scraping_response = requests.get(provider["url"], params=params, timeout=60)

        if not scraping_response.ok:
            print(f"Proxy API failed with status {scraping_response.status_code}")
            return None

        # Update yt-dlp options with proxy response data
        if "set-cookie" in scraping_response.headers:
            ydl_opts.update({
                "http_headers": {
                    **ydl_opts.get("http_headers", {}),
                    "Cookie": scraping_response.headers["set-cookie"],
                }
            })

        # Add proxy-specific headers
        ydl_opts["http_headers"] = ydl_opts.get("http_headers", {})
        ydl_opts["http_headers"].update({
            "X-Forwarded-For": scraping_response.headers.get("X-Forwarded-For", ""),
            "X-Real-IP": scraping_response.headers.get("X-Real-IP", ""),
            "Referer": url,
        })

        # Attempt download with enhanced options
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            if info_dict:
                return {
                    "success": True,
                    "info_dict": info_dict,
                    "method": f"proxy_{provider_name}",
                }

    except Exception as e:
        print(f"Proxy download failed with {provider_name}: {str(e)}")

    return None
