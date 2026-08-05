from types import SimpleNamespace

from app.services.auth_service import create_access_token, password_hash


def test_password_hash_does_not_store_plain_text() -> None:
    plain_password = 'inspection-123'
    hashed_password = password_hash.hash(plain_password)

    assert hashed_password != plain_password
    assert password_hash.verify(plain_password, hashed_password)


def test_access_token_contains_user_subject() -> None:
    user = SimpleNamespace(id=42, email='operator@aoi.local')

    token = create_access_token(user)  # type: ignore[arg-type]

    assert isinstance(token, str)
    assert token.count('.') == 2