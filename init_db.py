# init_db.py
from app.models import Base
from app.database import engine

Base.metadata.create_all(engine)
