from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import OperationalError
from app.database import Base, engine, SessionLocal
from app.schemas import URLCreate, URLResponse, URLStats
from app import crud
from app.cache import warm_redis_from_db
from app.batch import batch_sync_loop
import os
import time
from contextlib import asynccontextmanager
import asyncio

from app.url_exceptions import CacheKeyNotFoundException


def wait_for_db():
    retries = 10
    while retries > 0:
        try:
            with engine.connect():
                print("Database connected successfully")
                return
        except OperationalError:
            retries -= 1
            print(f"Database not ready, retrying....")
            time.sleep(3)
    raise Exception("Could not connect to database.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_db()
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        warm_redis_from_db(db)
    finally:
        db.close()
    task = asyncio.create_task(batch_sync_loop())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)



@app.post('/shorten', response_model=URLResponse, status_code=201)
def create_short_url(request: URLCreate):
    url_object = crud.create_short_url(str(request.original_url))
    short_url = os.getenv("HOST_URL") + f"/{url_object['short_code']}"
    return URLResponse(
        short_code=url_object["short_code"],
        original_url=url_object["original_url"],
        short_url=short_url,
        created_at=url_object["created_at"]
    )

@app.get("/{short_code}/stats", response_model=URLStats)
def get_stats(short_code: str):
    try:
        return crud.get_url_stats(short_code)
    except CacheKeyNotFoundException as e:
        raise HTTPException(status_code=404, detail="Invalid short code")

@app.get("/{short_code}")
async def redirect_url(short_code: str):
    original_url = crud.get_url_by_code(short_code)
    if original_url is None:
        raise HTTPException(status_code=404, detail="Invalid short_url")
    crud.increment_count(short_code)
    return RedirectResponse(original_url, status_code=302)



