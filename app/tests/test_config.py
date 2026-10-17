import pytest
from pydantic import ValidationError

from config import Settings



def test_database_url_is_required(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)



def test_cors_origin_list_parses_comma_separated_origins():
    settings = Settings(
        database_url="postgresql://user:password@localhost:5432/testdb",
        cors_origins="http://localhost:5173, https://example.com, ",
        _env_file=None,
    )

    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "https://example.com",
    ]


def test_database_checkpoint_url_uses_dedicated_url_when_configured():
    settings = Settings(
        database_url="postgresql://user:password@localhost:5432/app",
        langgraph_checkpoint_db_url=(
            "postgresql://user:password@localhost:5432/checkpoints"
        ),
        _env_file=None,
    )

    assert settings.database_checkpoint_url == (
        "postgresql://user:password@localhost:5432/checkpoints"
    )


def test_database_checkpoint_url_falls_back_to_database_url():
    settings = Settings(
        database_url="postgresql://user:password@localhost:5432/app",
        langgraph_checkpoint_db_url=None,
        _env_file=None,
    )

    assert settings.database_checkpoint_url == (
        "postgresql://user:password@localhost:5432/app"
    )
