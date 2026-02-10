#!/usr/bin/env python3
"""
Vault management tool for Signup Manager.

Encrypts secrets with a master password using PBKDF2 key derivation + Fernet
encryption, so secrets never exist in plaintext on disk.

Usage:
    python vault.py create                     # Generate keys, encrypt with master password
    python vault.py create --file /path/.vault # Custom output path
    python vault.py show                       # Decrypt and display vault contents
"""

import argparse
import base64
import getpass
import json
import os
import secrets
import sys

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

VAULT_ITERATIONS = 600_000  # OWASP recommended minimum for PBKDF2-SHA256


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a Fernet key from a master password using PBKDF2-HMAC-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=VAULT_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def create_vault(vault_path: str):
    """Interactively create an encrypted vault file."""
    print("=" * 55)
    print(" Signup Manager - Vault Creator")
    print("=" * 55)
    print()

    if os.path.exists(vault_path):
        confirm = input(f"{vault_path} already exists. Overwrite? [y/N]: ")
        if confirm.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    # Get master password
    while True:
        password = getpass.getpass("Enter master password (min 12 chars): ")
        if len(password) < 12:
            print("Password must be at least 12 characters.")
            continue
        confirm = getpass.getpass("Confirm master password: ")
        if password != confirm:
            print("Passwords do not match. Try again.")
            continue
        break

    # Get admin password
    while True:
        admin_pass = getpass.getpass("Set initial admin password (min 8 chars): ")
        if len(admin_pass) < 8:
            print("Must be at least 8 characters. Try again.")
            continue
        break

    # Generate cryptographic keys
    secret_key = secrets.token_hex(32)
    encryption_key = Fernet.generate_key().decode()
    blind_index_salt = secrets.token_hex(16)

    vault_secrets = {
        "SECRET_KEY": secret_key,
        "ENCRYPTION_KEY": encryption_key,
        "EMAIL_BLIND_INDEX_SALT": blind_index_salt,
        "FIRST_RUN_ADMIN_USER": "admin",
        "FIRST_RUN_ADMIN_PASSWORD": admin_pass,
    }

    # Encrypt with master password
    salt = os.urandom(32)
    key = derive_key(password, salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(json.dumps(vault_secrets).encode())

    vault_data = {
        "version": 1,
        "salt": base64.b64encode(salt).decode(),
        "iterations": VAULT_ITERATIONS,
        "data": encrypted.decode(),
    }

    os.makedirs(os.path.dirname(vault_path) or ".", exist_ok=True)
    with open(vault_path, "w") as f:
        json.dump(vault_data, f, indent=2)
    os.chmod(vault_path, 0o600)

    print()
    print(f"Vault created: {vault_path}")
    print()
    print("IMPORTANT:")
    print("  1. Remember your master password - it cannot be recovered")
    print("  2. The encryption key CANNOT be changed after data is encrypted")
    print("  3. Back up the vault file to a secure location")
    print("  4. You will enter the master password each time the app starts")
    print()


def show_vault(vault_path: str):
    """Decrypt and display vault contents."""
    if not os.path.exists(vault_path):
        print(f"Vault not found: {vault_path}")
        sys.exit(1)

    password = getpass.getpass("Master password: ")

    with open(vault_path) as f:
        vault_data = json.load(f)

    salt = base64.b64decode(vault_data["salt"])
    key = derive_key(password, salt)

    try:
        fernet = Fernet(key)
        decrypted = fernet.decrypt(vault_data["data"].encode())
        secrets_dict = json.loads(decrypted)
        print()
        for k, v in secrets_dict.items():
            print(f"  {k}={v}")
        print()
    except Exception:
        print("Invalid master password.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Signup Manager vault tool")
    parser.add_argument("command", choices=["create", "show"],
                        help="create: generate keys and encrypt; show: decrypt and display")
    parser.add_argument("--file", default=".vault", help="Vault file path (default: .vault)")
    args = parser.parse_args()

    if args.command == "create":
        create_vault(args.file)
    elif args.command == "show":
        show_vault(args.file)


if __name__ == "__main__":
    main()
