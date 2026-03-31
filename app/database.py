from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,        # max persistent connections
    max_overflow=10,    # extra connections beyond pool_size under load
    pool_timeout=30,    # seconds to wait for a connection before error
    pool_recycle=1800   # recycle connections after 30 mins (prevents stale connections)
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
    )

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()