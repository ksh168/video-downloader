import hashlib

def generate_url_hash(url: str) -> str:
    """
    Generate a SHA256 hash for the given URL
    
    :param url: URL to hash
    :return: SHA256 hash as a string
    """
    return hashlib.sha256(url.encode()).hexdigest()
