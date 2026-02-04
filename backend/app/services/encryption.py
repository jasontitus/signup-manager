from cryptography.fernet import Fernet
from app.config import settings


class EncryptionService:
    """Service for encrypting and decrypting PII fields using Fernet symmetric encryption."""

    def __init__(self):
        self.cipher = Fernet(settings.ENCRYPTION_KEY.encode())

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
