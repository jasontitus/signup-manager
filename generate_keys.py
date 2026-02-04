#!/usr/bin/env python3
"""
Generate secure keys for the Signup Manager.
Run this script and copy the output to your .env file.
"""

from cryptography.fernet import Fernet
import secrets

print("=" * 60)
print("Signup Manager - Security Keys Generator")
print("=" * 60)
print("\nCopy these values to your .env file:\n")
print("-" * 60)

secret_key = secrets.token_hex(32)
encryption_key = Fernet.generate_key().decode()
email_salt = secrets.token_hex(16)

print(f"SECRET_KEY={secret_key}")
print(f"ENCRYPTION_KEY={encryption_key}")
print(f"EMAIL_BLIND_INDEX_SALT={email_salt}")

print("-" * 60)
print("\nIMPORTANT:")
print("1. Keep these keys SECRET and SECURE")
print("2. NEVER commit the .env file to version control")
print("3. BACKUP the encryption key - data cannot be recovered without it")
print("4. Do NOT change the encryption key after encrypting data")
print("=" * 60)
