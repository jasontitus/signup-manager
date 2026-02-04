import pytest
from app.services.encryption import encryption_service


def test_encrypt_decrypt_round_trip():
    """Test that encryption and decryption work correctly."""
    plaintext = "sensitive-data@example.com"

    # Encrypt
    ciphertext = encryption_service.encrypt(plaintext)

    # Verify it's different
    assert ciphertext != plaintext

    # Decrypt
    decrypted = encryption_service.decrypt(ciphertext)

    # Verify it matches original
    assert decrypted == plaintext


def test_encrypt_empty_string():
    """Test encryption of empty string."""
    plaintext = ""
    ciphertext = encryption_service.encrypt(plaintext)
    decrypted = encryption_service.decrypt(ciphertext)
    assert decrypted == ""


def test_different_plaintexts_produce_different_ciphertexts():
    """Test that different inputs produce different encrypted outputs."""
    plaintext1 = "test1@example.com"
    plaintext2 = "test2@example.com"

    ciphertext1 = encryption_service.encrypt(plaintext1)
    ciphertext2 = encryption_service.encrypt(plaintext2)

    assert ciphertext1 != ciphertext2
