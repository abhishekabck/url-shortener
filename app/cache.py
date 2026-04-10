import os
import redis
from typing import Any

from redis.crc import key_slot

from app.models import URL
from app.url_exceptions import CacheKeyNotFoundException

redis_client = redis.from_url(os.getenv("REDIS_URL") + "/0")
redis_client_2 = redis.from_url(os.getenv("REDIS_URL") + "/1")

get_key = lambda short_code: f"USER:{short_code}"
dirty_set_key = "Pending:BatchQueue"

def set_url_hash(short_code, data: dict[str, Any]):
    key = get_key(short_code)
    exist = redis_client.exists(key)
    if exist:
        return False
    redis_client.hset(key, mapping=data)
    return True


def get_url_hash(short_code: str):
    key = get_key(short_code)
    raw_data = redis_client.hgetall(key)
    if not raw_data:
        raise CacheKeyNotFoundException(key)
    return {k.decode(): v.decode() for k,v in raw_data.items()}

def get_key_from_url_hash(short_code, key1):
    key = get_key(short_code)
    return redis_client.hget(key, key1)

def get_all_short_codes():
    keys = redis_client.keys("USER:*")
    short_codes = {key.decode().split(":")[1]: None for key in keys}
    return short_codes

def add_to_dirty_set(short_code):
    redis_client_2.sadd(dirty_set_key, short_code)


def increment_count_in_cache(short_code):
    key = get_key(short_code)
    return redis_client.hincrby(key, "click_count", 1)


def get_chunked_data(max_chunk_size=500):
    records = list()
    chunked_short_codes = redis_client_2.spop(dirty_set_key, count=max_chunk_size)
    for short_code in chunked_short_codes:
        short_code = short_code.decode()
        record = get_url_hash(short_code)
        record["short_code"] = short_code
        records.append(record)
    return records

def update_dirty_set(short_codes: list[str]):
    redis_client_2.sadd(dirty_set_key, *short_codes)

def warm_redis_from_db(db):
    records = db.query(URL).all()
    if not records:
        return
    for record in records:
        set_url_hash(record.short_code,
                     data={
                         "original_url": record.original_url,
                         "click_count": str(record.click_count),
                         "created_at": record.created_at,
                     })
