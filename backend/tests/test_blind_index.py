"""Tests for the blind index service."""

from app.services.blind_index import generate_blind_index


def test_consistent_hash_for_same_email():
    """Same email always produces the same blind index."""
    idx1 = generate_blind_index("test@example.com")
    idx2 = generate_blind_index("test@example.com")
    assert idx1 == idx2
    assert len(idx1) == 64  # SHA-256 hex digest


def test_different_emails_produce_different_hashes():
    """Different emails produce different blind indexes."""
    idx1 = generate_blind_index("alice@example.com")
    idx2 = generate_blind_index("bob@example.com")
    assert idx1 != idx2


def test_normalizes_case():
    """Email is normalized to lowercase before hashing."""
    idx_lower = generate_blind_index("Test@Example.COM")
    idx_upper = generate_blind_index("test@example.com")
    assert idx_lower == idx_upper


def test_strips_whitespace():
    """Leading/trailing whitespace is stripped."""
    idx_clean = generate_blind_index("test@example.com")
    idx_padded = generate_blind_index("  test@example.com  ")
    assert idx_clean == idx_padded


def test_empty_string_returns_empty():
    """Empty email returns empty string."""
    assert generate_blind_index("") == ""


def test_none_returns_empty():
    """None input returns empty string."""
    assert generate_blind_index(None) == ""
