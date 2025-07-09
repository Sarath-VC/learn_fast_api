from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


POSTGRES_USER = "fastapi"
POSTGRES_PASSWORD = "fastapi"
POSTGRES_DB = "learn_fast_api"
POSTGRES_HOST = "localhost"  # or "db" if using Docker
POSTGRES_PORT = "5432"

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()