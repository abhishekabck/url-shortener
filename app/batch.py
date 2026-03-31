from app.cache import get_all_cached_click_counts, bulk_update
from sqlalchemy import case, update
from app.models import URL
from fastapi import Depends
from app.database import SessionLocal
import asyncio

update_query = lambda counts:(update(URL)
    .where(URL.short_code.in_(counts.keys()))
    .values(
        click_count=URL.click_count + case(
            counts,
            value=URL.short_code,
            else_=0
        )
    )
)
def update_fallback(counts):
    bulk_update(counts)

def update_counts_in_db(db):
    counts = get_all_cached_click_counts()
    if counts:
        query = update_query(counts)
        try:
            db.execute(query)
            db.commit()
        except Exception as e:
            print("Bulk update failed..")
            update_fallback(counts)


async def click_count_increment_batch():
    while True:
        await asyncio.sleep(60)
        db = SessionLocal()
        try:
            update_counts_in_db(db)
        finally:
            db.close()