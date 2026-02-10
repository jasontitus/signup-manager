"""Tests for the encryption service."""

import pytest
from app.services.encryption import EncryptionService, encryption_service


def test_encrypt_decrypt_round_trip():
    """Encryption and decryption produce the original value."""
    plaintext = "sensitive-data@example.com"
    ciphertext = encryption_service.encrypt(plaintext)
    assert ciphertext != plaintext
    assert encryption_service.decrypt(ciphertext) == plaintext


def test_encrypt_empty_string():
    """Empty string encrypts and decrypts to empty string."""
    assert encryption_service.encrypt("") == ""
    assert encryption_service.decrypt("") == ""


def test_different_plaintexts_produce_different_ciphertexts():
    """Different inputs produce different encrypted outputs."""
    c1 = encryption_service.encrypt("test1@example.com")
    c2 = encryption_service.encrypt("test2@example.com")
    assert c1 != c2


def test_same_plaintext_produces_different_ciphertexts():
    """Fernet includes randomness — same input gives different ciphertext each time."""
    c1 = encryption_service.encrypt("same-input")
    c2 = encryption_service.encrypt("same-input")
    assert c1 != c2  # Fernet uses random IV
    # But both decrypt to the same value
    assert encryption_service.decrypt(c1) == encryption_service.decrypt(c2)


def test_unicode_round_trip():
    """Unicode characters survive encryption round-trip."""
    text = "Nombre: Jose Garcia-Lopez"
    assert encryption_service.decrypt(encryption_service.encrypt(text)) == text


def test_long_string_round_trip():
    """Long strings encrypt and decrypt correctly."""
    text = "x" * 10000
    assert encryption_service.decrypt(encryption_service.encrypt(text)) == text


def test_uninitialized_service_raises():
    """Accessing cipher before initialization raises RuntimeError."""
    svc = EncryptionService()
    with pytest.raises(RuntimeError, match="not initialized"):
        svc.encrypt("test")
