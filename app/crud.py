import random
import string
from typing import Any
from app.models import URL
from app.schemas import URLStats
from app.cache import set_url_hash, add_to_dirty_set, get_key_from_url_hash, increment_count_in_cache, get_url_hash
from datetime import datetime, timezone
from app.url_exceptions import CacheKeyAlreadyExistsException


CHARACTERS = string.ascii_lowercase + string.ascii_uppercase + string.digits

def generate_short_code(length=6):
    return ''.join(random.choices(CHARACTERS, k=length))

def create_short_url(original_url: str) -> dict[str, Any]:
    while True:
        short_code = generate_short_code()
        data = {
            "original_url": original_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "click_count": 0
        }
        success =  set_url_hash(short_code, data)
        if success:
            break
    add_to_dirty_set(short_code)
    data["short_code"] = short_code
    return data

def get_url_by_code(short_code) -> None | str:
    data = get_key_from_url_hash(short_code, "original_url")
    if data:
        return data.decode()
    return None

def increment_count(short_code) -> int:
    return increment_count_in_cache(short_code)

def get_url_stats(short_code) -> URLStats:
    obj = get_url_hash(short_code)
    return URLStats(
        short_code=short_code,
        original_url=obj["original_url"],
        click_count=obj["click_count"],
        created_at=obj["created_at"]
    )