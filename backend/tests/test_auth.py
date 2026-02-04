import pytest
from app.services.auth import hash_password, verify_password, create_access_token, verify_token


def test_password_hashing():
    """Test password hashing."""
    password = "test-password-123"
    hashed = hash_password(password)

    # Verify hash is different from plaintext
    assert hashed != password

    # Verify password can be verified
    assert verify_password(password, hashed) is True

    # Verify wrong password fails
    assert verify_password("wrong-password", hashed) is False


def test_jwt_token_creation_and_verification():
    """Test JWT token creation and verification."""
    payload = {"sub": "123", "username": "testuser"}

    # Create token
    token = create_access_token(payload)

    # Verify token
    decoded = verify_token(token)

    assert decoded is not None
    assert decoded["sub"] == "123"
    assert decoded["username"] == "testuser"
    assert "exp" in decoded


def test_jwt_invalid_token():
    """Test that invalid tokens are rejected."""
    invalid_token = "invalid.token.here"

    decoded = verify_token(invalid_token)

    assert decoded is None
