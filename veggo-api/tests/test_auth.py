import pytest
from app.schemas.auth import clean_sl_phone, RegisterRequest
from app.utils.security import create_access_token, decode_access_token, hash_password, verify_google_id_token, verify_password


def test_password_hashing():
    pwd = "SecretPassword123!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_flow():
    payload = {"sub": "user_12345", "role": "USER"}
    token = create_access_token(payload)
    assert isinstance(token, str)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user_12345"
    assert decoded["role"] == "USER"


def test_sri_lankan_phone_validation():
    # Valid formats
    assert clean_sl_phone("0771234567") == "0771234567"
    assert clean_sl_phone("+94771234567") == "0771234567"
    assert clean_sl_phone("94712345678") == "0712345678"
    assert clean_sl_phone("078-1234567") == "0781234567"

    # Invalid formats
    with pytest.raises(ValueError):
        clean_sl_phone("123456")

    with pytest.raises(ValueError):
        clean_sl_phone("0991234567")  # invalid operator code


@pytest.mark.asyncio
async def test_google_id_token_mock():
    # Verify mock development token claims without requiring external network
    claims = await verify_google_id_token("mock-google-token-testuser")
    assert claims["email"] == "testuser@example.com"
    assert claims["email_verified"] is True
    assert "sub" in claims
