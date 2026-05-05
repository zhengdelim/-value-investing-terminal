from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import redis as redis_lib
from .config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

redis_client = redis_lib.from_url(settings.redis_url, decode_responses=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
