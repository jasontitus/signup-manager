"""
Runtime vault manager. Decrypts the .vault file with a master password
and holds secrets in memory only.
"""

import base64
import json
import logging
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class VaultManager:
    """Manages the encrypted vault lifecycle at runtime."""

    def __init__(self):
        self._secrets: dict = {}
        self._unlocked = False

    @property
    def is_unlocked(self) -> bool:
        return self._unlocked

    @property
    def secrets(self) -> dict:
        if not self._unlocked:
            raise RuntimeError("Vault is locked")
        return self._secrets.copy()

    def get_vault_path(self) -> str:
        # Single source of truth: settings reads VAULT_FILE from the
        # environment or .env, with the same default as before.
        from app.config import settings
        return settings.VAULT_FILE

    def vault_exists(self) -> bool:
        return os.path.exists(self.get_vault_path())

    def unlock(self, master_password: str) -> bool:
        """Decrypt the vault with the master password.

        Returns True on success, False on wrong password.
        Raises FileNotFoundError if vault file is missing.
        """
        vault_path = self.get_vault_path()
        if not os.path.exists(vault_path):
            raise FileNotFoundError(f"Vault file not found: {vault_path}")

        with open(vault_path) as f:
            vault_data = json.load(f)

        salt = base64.b64decode(vault_data["salt"])
        iterations = vault_data.get("iterations", 600_000)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

        try:
            fernet = Fernet(key)
            decrypted = fernet.decrypt(vault_data["data"].encode())
        except InvalidToken:
            # Wrong master password (or tampered vault) — expected path
            return False

        try:
            self._secrets = json.loads(decrypted)
        except ValueError:
            # Password was right but the payload is corrupt — surface it
            # instead of reporting "invalid password" to the operator.
            logger.error("Vault decrypted but payload is not valid JSON — vault file is corrupt")
            raise RuntimeError("Vault file is corrupt: decrypted payload is not valid JSON")

        self._unlocked = True
        return True


vault_manager = VaultManager()
