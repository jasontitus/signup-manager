import hashlib
from app.config import settings


def generate_blind_index(email: str) -> str:
    """
    Generate a blind index for an email address using SHA256.
    This allows duplicate checking without storing plaintext emails.
    """
    if not email:
        return ""

    # Normalize email: lowercase and strip whitespace
    normalized = email.lower().strip()

    # Create salted hash
    salted = f"{normalized}{settings.EMAIL_BLIND_INDEX_SALT}"
    hash_obj = hashlib.sha256(salted.encode())

    return hash_obj.hexdigest()
