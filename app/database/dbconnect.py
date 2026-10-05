# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine, text
# pyrefly: ignore [missing-import]
from sqlalchemy.exc import SQLAlchemyError

from config import get_settings


settings = get_settings()

# Centralized, environment-driven database configuration.
DATABASE_URL = settings.database_url

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=settings.db_pool_pre_ping,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=False,
)


def check_connection() -> bool:
    """Return True when PostgreSQL can execute a lightweight query."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


def test_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            db_version = result.scalar()
            print(
                "Successfully connected to PostgreSQL!\n"
                f"Database Version: {db_version}"
            )
    except SQLAlchemyError as e:
        print(f"Error connecting to PostgreSQL database: {e}")


if __name__ == "__main__":
    test_connection()
