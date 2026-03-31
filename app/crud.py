import random
import string
from app.cache import get_cached_url, set_cached_url, increment_cached_click_count, get_cached_click_count
from app.models import URL
from app.schemas import URLStats


CHARACTERS = string.ascii_lowercase + string.ascii_uppercase + string.digits

def generate_short_code(length=6):
    return ''.join(random.choices(CHARACTERS, k=length))

def create_short_url(db, original_url) -> None:
    short_code = generate_short_code()
    while db.query(URL).filter(URL.short_code == short_code).first():
        short_code = generate_short_code()
    url_object = URL(
        short_code = short_code,
        original_url = str(original_url)
    )
    db.add(url_object)
    db.commit()
    db.refresh(url_object)
    return url_object

def get_url_by_code(db, short_code) -> None | str:
    cached = get_cached_url(short_code)
    if cached:
        return cached

    url_obj = db.query(URL).filter(URL.short_code==short_code).filter().first()
    if url_obj is None:
        return None
    
    set_cached_url(short_code, url_obj.original_url)
    return url_obj.original_url

async def increment_click_count(db, short_code):
    increment_cached_click_count(short_code)

def get_url_stats(db, short_code):
    obj = db.query(URL).filter(URL.short_code == short_code).first()
    if not obj:
        return None
    return URLStats(
        short_code=obj.short_code,
        original_url=obj.original_url,
        click_count=obj.click_count + get_cached_click_count(short_code),
        created_at=obj.created_at
    )