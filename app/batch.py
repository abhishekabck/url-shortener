import asyncio
from app.models import URL
from app.database import SessionLocal
from sqlalchemy.dialects.postgresql import insert
from app.cache import (get_chunked_data,
                       update_dirty_set,
                       redis_client_2)


def update_or_insert_chunked_data_to_database(db, chunk_size=500):
    records = get_chunked_data(max_chunk_size=chunk_size)
    if not records:
        return
    stmt = insert(URL).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["short_code"],
        set_={
            "click_count": stmt.excluded.click_count,
            "original_url": stmt.excluded.original_url,
        }
    )
    try:
        db.execute(stmt)
        db.commit()
    except Exception as e:
        db.rollback()
        update_dirty_set([r["short_code"] for r in records])
        print(f"Batch update failed: {e}")


async def batch_sync_loop():
    while True:
        await asyncio.sleep(60)
        db = SessionLocal()
        try:
            accuired = redis_client_2.set("batch_lock", "1", nx=True, ex=300)
            if not accuired:
                continue
            update_or_insert_chunked_data_to_database(db)
        finally:
            redis_client_2.delete("batch_lock")
            db.close()
