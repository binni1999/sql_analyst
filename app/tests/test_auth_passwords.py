"""Unit tests for DataPilot password hashing; no database required."""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://test:test@127.0.0.1:5432/test")
os.environ.setdefault("READONLY_DATABASE_URL", "postgresql+psycopg2://test:test@127.0.0.1:5432/test")
os.environ.setdefault("ENVIRONMENT", "test")

from services.auth_service import _password_hash, _verify_password


def test_password_hash_verifies_correct_password():
    encoded = _password_hash("StrongPass123")
    assert encoded != "StrongPass123"
    assert _verify_password("StrongPass123", encoded)


def test_password_hash_rejects_wrong_password():
    encoded = _password_hash("StrongPass123")
    assert not _verify_password("WrongPass123", encoded)


def test_password_hash_uses_unique_salts():
    first = _password_hash("StrongPass123")
    second = _password_hash("StrongPass123")
    assert first != second
    assert _verify_password("StrongPass123", first)
    assert _verify_password("StrongPass123", second)
