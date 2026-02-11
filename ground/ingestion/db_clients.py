import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ground.ingestion.ingestion_settings import get_ingestion_settings

settings = get_ingestion_settings()

DATABASE_URI = settings.postgres_uri

engine = create_engine(DATABASE_URI, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    with SessionLocal() as session:
        yield session


def get_redis_client():
    client = redis.Redis(host=settings.redis_host, port=settings.redis_port, db=settings.redis_db)
    try:
        yield client
    finally:
        client.close()



