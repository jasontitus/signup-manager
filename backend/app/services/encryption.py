from cryptography.fernet import Fernet
from typing import Optional


class EncryptionService:
    """Service for encrypting and decrypting PII fields using Fernet symmetric encryption.

    Supports two modes:
    - Direct: initialized immediately from settings (dev with .env)
    - Deferred: initialized later via initialize() after vault unlock
    """

    def __init__(self):
        self._cipher: Optional[Fernet] = None

    def initialize(self, key: str):
        """Initialize the cipher with the given Fernet key."""
        self._cipher = Fernet(key.encode())

    @property
    def cipher(self) -> Fernet:
        if self._cipher is None:
            raise RuntimeError("Encryption service not initialized. Unlock the vault first.")
        return self._cipher

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string and return the ciphertext as a string."""
        if not plaintext:
            return ""
        encrypted_bytes = self.cipher.encrypt(plaintext.encode())
        return encrypted_bytes.decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a ciphertext string and return the plaintext."""
        if not ciphertext:
            return ""
        decrypted_bytes = self.cipher.decrypt(ciphertext.encode())
        return decrypted_bytes.decode()


# Singleton instance
encryption_service = EncryptionService()
