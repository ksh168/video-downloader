import os
import redis
from utils.file_handling.hash_generator import generate_url_hash

class RedisClient:
    def __init__(self):
        self.redis = redis.Redis(
            host = os.getenv("REDIS_HOST"),
            port = os.getenv("REDIS_PORT"),
            username = os.getenv("REDIS_USERNAME"),
            password = os.getenv("REDIS_PASSWORD"),
            ssl=True,  # Enable SSL
            ssl_cert_reqs=None  # Adjust as needed, e.g., ssl.CERT_NONE for no verification
        )
        self.retry_key_prefix = "vdq-"
        self.default_expiry = int(os.getenv("DEFAULT_EXPIRY", 60*60*24*1))  # 1 day
        try:
            self.redis.ping()
            print("Redis connection successful")
        except redis.ConnectionError:
            print("Redis connection failed")
            raise Exception("Redis connection failed")

    def _get_retry_key(self, url: str) -> str:
        """Generate Redis key for retry count"""
        url_hash = generate_url_hash(url)
        return f"{self.retry_key_prefix}{url_hash}"

    def get_retry_count(self, url: str) -> int:
        """Get current retry count for URL"""
        key = self._get_retry_key(url)
        count = self.redis.get(key)
        return int(count) if count else 0

    def increment_retry_count(self, url: str) -> int:
        """Increment retry count for URL"""
        key = self._get_retry_key(url)
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.default_expiry)
        result = pipe.execute()
        return result[0]  # Return new count

    def reset_retry_count(self, url: str):
        """Reset retry count for URL"""
        key = self._get_retry_key(url)
        self.redis.delete(key) 