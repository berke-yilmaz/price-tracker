import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_cached_product(key):
    """Redis'ten ürün bilgisini al"""
    cached = redis_client.get(f"product:{key}")
    if cached:
        return json.loads(cached)
    return None

def cache_product(key, product, ttl=86400):
    """Ürün bilgisini Redis'e kaydet (24 saat TTL)"""
    redis_client.setex(
        f"product:{key}",
        ttl,
        json.dumps(product)
    )