from app.cache import get_all_cached_click_counts, bulk_update
from sqlalchemy import case, update
from app.models import URL
from fastapi import Depends
from app.database import SessionLocal
import asyncio

update_query = lambda counts: (
    update(URL)
    .where(URL.short_code.in_(counts.keys()))
    .values(
        click_count=case(
            counts,
            value=URL.short_code,
            else_=URL.click_count  # keep existing if not in batch
        )
    )
)


def chunked_dict(d, size):
    items = list(d.items())
    for i in range(0, len(items), size):
        yield dict(items[i:i+size])

def update_counts_in_db(db):
    counts = get_all_cached_click_counts()
    if not counts:
        return
    for chunk in chunked_dict(counts, 200):
        try:
            db.execute(update_query(chunk))
            db.commit()
        except Exception as e:
            print(f"Batch chunk failed: {e}")


async def click_count_increment_batch():
    while True:
        await asyncio.sleep(60)
        db = SessionLocal()
        try:
            update_counts_in_db(db)
        finally:
            db.close()