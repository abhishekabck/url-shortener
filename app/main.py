from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from app.database import get_db, Base, engine, SessionLocal
from app.schemas import URLCreate, URLResponse, URLStats
from app import crud
from app.cache import warm_redis_from_db
import os
import time
from app.batch import click_count_increment_batch
from contextlib import asynccontextmanager
import asyncio



@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        warm_redis_from_db(db)
    finally:
        db.close()
    task = asyncio.create_task(click_count_increment_batch())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)


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
    raise Exception("Count not connect to database.")
wait_for_db()
Base.metadata.create_all(bind=engine)


@app.post('/shorten', response_model=URLResponse, status_code=201)
def create_short_url(request: URLCreate, db: Session = Depends(get_db)):
    url_object = crud.create_short_url(db, request.original_url)
    short_url = os.getenv("HOST_URL") + f"/{url_object.short_code}"
    return URLResponse(
        short_code=url_object.short_code,
        original_url=url_object.original_url,
        short_url=short_url,
        created_at=url_object.created_at
    )

@app.get("/{short_code}/stats", response_model=URLStats)
def get_stats(short_code: str, db: Session = Depends(get_db)):
    url_stats = crud.get_url_stats(db, short_code)
    if url_stats is None:
        raise HTTPException(status_code=404, detail="Invalid short code")
    return url_stats

@app.get("/{short_code}")
async def redirect_url(short_code: str, db: Session = Depends(get_db)):
    original_url = crud.get_url_by_code(db, short_code)
    if original_url is None:
        raise HTTPException(status_code=404, detail="Invalid short_url")
    await crud.increment_click_count(db, short_code)
    return RedirectResponse(original_url, status_code=302)

