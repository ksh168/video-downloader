import re

def sanitize_url(url: str) -> str:
    # Ensure URL starts with http:// or https://
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Remove 'amp.' prefix if present in URL for any protocol
    if "://amp." in url:
        # Find the protocol separator and replace amp. with empty string
        protocol_end = url.find("://") + 3
        if url[protocol_end:].startswith("amp."):
            url = url[:protocol_end] + url[protocol_end + 4:]
    
    # Remove common tracking parameters
    tracking_params = [
        'utm_source', 'utm_medium', 'utm_campaign', 
        'utm_term', 'utm_content', 'fbclid',
        'gclid', 'msclkid', 'dclid', 'mc_eid'
    ]
    for param in tracking_params:
        url = re.sub(fr'[?&]{param}=[^&]*', '', url)
    
    # Remove trailing ? or & if they exist after parameter removal
    url = re.sub(r'[?&]$', '', url)
    
    # Remove URL fragment
    url = url.split('#')[0]
    
    return url