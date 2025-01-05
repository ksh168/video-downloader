import os

PROXY_PROVIDERS = {
    "scrapingdog": {
        "url": os.getenv("PROXY_API_URL"),
        "api_key_env": os.getenv("PROXY_API_KEY"),
        "params": {
            "render": "true",
            "premium": "true"
        }
    },
    # Add more proxy providers here as needed
}

# List of proxy providers to try in order
PROXY_PROVIDER_ORDER = ["scrapingdog"]

# Maximum number of proxy retry attempts
MAX_PROXY_RETRIES = 3 