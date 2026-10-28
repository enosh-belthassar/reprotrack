"""Cryptographic primitives, password hashing, and token generation."""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

# Dummy hash used to equalize timing when authenticating non-existent users
DUMMY_PASSWORD_HASH = ph.hash("reprotrack_timing_dummy_value_2026")


def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against an Argon2id hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError):
        return False


def dummy_verify_password(plain_password: str) -> None:
    """Perform dummy hash verification to prevent user enumeration through timing differences."""
    try:
        ph.verify(DUMMY_PASSWORD_HASH, plain_password)
    except (VerifyMismatchError, VerificationError):
        pass


def generate_opaque_token() -> str:
    """Generate a high-entropy cryptographically secure random opaque session token (256+ bits)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Compute one-way SHA-256 hash of a session token for safe storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
