import redis
import os
from sqlalchemy import select
from app.models import URL

redis_client = redis.from_url(os.getenv("REDIS_URL") + "/0")
redis_client_counts = redis.from_url(os.getenv("REDIS_URL") + "/1")
URL_TTL = 3600

## URL CHACHE PART

def get_cached_url(short_code) -> str | None:
    result = redis_client.get(short_code)
    if result is None:
        return None
    else:
        return result.decode("utf-8")

def set_cached_url(short_code, original_url) -> None:
    result = redis_client.setex(short_code, URL_TTL, original_url)

def delete_cached_url(short_code):
    redis_client.delete(short_code)
    

## COUNT CACHE PART
def increment_cached_click_count(short_code) -> None:
    redis_client_counts.incr(f"clicks:{short_code}")
    
def get_cached_click_count(short_code) -> int:
    count = redis_client_counts.get(f"clicks:{short_code}")
    if not count:
        return 0
    return int(count.decode("utf-8"))

def get_all_cached_click_counts() -> list[list[str, int]]:
    counts = {}
    keys = redis_client_counts.keys("clicks:*")
    for key in keys:
        short_code = key.decode("utf-8").replace("clicks:", "")
        count = redis_client_counts.get(key)
        if count:
                count = int(count.decode('utf-8'))
                counts[short_code] = count
    
    return counts

def bulk_update(counts):
    for key in counts:
        redis_client_counts.incr(f"clicks:{key}", counts[key])

def warm_redis_from_db(db):
    urls = db.query(URL.short_code, URL.click_count).all()
    for short_code, click_count in urls:
        key = f"clicks:{short_code}"
        redis_client_counts.setnx(key, click_count)