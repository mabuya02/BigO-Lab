from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Re-export engine & session factory for convenience
from app.db.database import engine, SessionLocal  # noqa: E402, F401

__all__ = ["Base", "engine", "SessionLocal"]
