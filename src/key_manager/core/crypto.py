"""Cryptographic primitives for the app.

Provides:
- Low-level: encrypt_raw / decrypt_raw (key-based, reusable)
- High-level: encrypt_key / decrypt_key (password-based, for API keys)
- Password hashing: hash_password / verify_password

All primitives use the cryptography library — no custom implementations.
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


# Older cryptography versions (< 3.0) require an explicit backend argument.
# Detect once at import time so we never pay the overhead again.
_NEEDS_BACKEND = None


def _detect_backend():
    global _NEEDS_BACKEND
    if _NEEDS_BACKEND is not None:
        return _NEEDS_BACKEND
    try:
        PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=16,
            salt=b'\x00' * 16,
            iterations=1,
        )
        _NEEDS_BACKEND = False
    except TypeError:
        _NEEDS_BACKEND = True
    return _NEEDS_BACKEND


def _create_kdf(*, algorithm, length, salt, iterations):
    """Create PBKDF2HMAC, compatible with old and new cryptography versions."""
    if _detect_backend():
        from cryptography.hazmat.backends import default_backend
        return PBKDF2HMAC(
            algorithm=algorithm, length=length, salt=salt,
            iterations=iterations, backend=default_backend(),
        )
    return PBKDF2HMAC(
        algorithm=algorithm, length=length, salt=salt,
        iterations=iterations,
    )


# ==============================================================
#  Low-level primitives (AES-256-GCM)
# ==============================================================

def encrypt_raw(plaintext: bytes, key: bytes) -> bytes:
    """Encrypt bytes with a 32-byte key using AES-256-GCM.
    Returns: nonce[12] + ciphertext_with_tag
    """
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt_raw(data: bytes, key: bytes) -> bytes:
    """Decrypt bytes produced by encrypt_raw.
    Raises InvalidTag on integrity failure or bad data.
    """
    if len(data) < 28:  # nonce(12) + min_ct(1) + tag(16)
        raise ValueError("Data too short")
    nonce = data[:12]
    ciphertext = data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


# ==============================================================
#  Password-based key derivation
# ==============================================================

def derive_key(password: str, salt: bytes, iterations: int = 200_000) -> bytes:
    """Derive a 32-byte key from password using PBKDF2-HMAC-SHA256."""
    kdf = _create_kdf(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(password.encode('utf-8'))


# ==============================================================
#  High-level: password-based encrypt/decrypt for API keys
# ==============================================================

def encrypt_key(plaintext: str, password: str) -> str:
    """Encrypt an API key with the user's password.
    Returns base64 string: salt[16] + encrypted_payload
    """
    if not plaintext:
        return ""

    salt = os.urandom(16)
    key = derive_key(password, salt)
    payload = encrypt_raw(plaintext.encode('utf-8'), key)

    return base64.b64encode(salt + payload).decode('ascii')


def decrypt_key(encoded: str, password: str) -> str:
    """Decrypt an API key with the user's password."""
    if not encoded:
        return ""

    raw = base64.b64decode(encoded)
    salt = raw[:16]
    payload = raw[16:]

    key = derive_key(password, salt)
    plaintext_bytes = decrypt_raw(payload, key)

    return plaintext_bytes.decode('utf-8')


# ==============================================================
#  Password hashing (for verifying unlock)
# ==============================================================

def hash_password(password: str) -> str:
    """Create a verifiable hash. Stores base64(salt[16] + hash[32])."""
    salt = os.urandom(16)
    kdf = _create_kdf(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    h = kdf.derive(password.encode('utf-8'))
    return base64.b64encode(salt + h).decode('ascii')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against stored hash."""
    try:
        raw = base64.b64decode(password_hash)
        salt = raw[:16]
        stored_hash = raw[16:]
        kdf = _create_kdf(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=200_000,
        )
        kdf.verify(password.encode('utf-8'), stored_hash)
        return True
    except Exception:
        return False
