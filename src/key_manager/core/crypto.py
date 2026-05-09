"""Cryptographic primitives for the app.

Provides:
- Low-level: encrypt_raw / decrypt_raw (key-based, reusable)
- High-level: encrypt_key / decrypt_key (password-based, for API keys)
- Password hashing: hash_password / verify_password

No external dependencies - pure Python standard library.
"""

import base64
import hashlib
import hmac
import os
import struct


# ==============================================================
#  Low-level primitives (HMAC-CTR + PKCS7 + HMAC integrity)
# ==============================================================

def _pad(data: bytes) -> bytes:
    """PKCS7 padding to 16-byte boundary."""
    pad_len = 16 - (len(data) % 16)
    return data + bytes([pad_len] * pad_len)


def _unpad(data: bytes) -> bytes:
    """Remove PKCS7 padding."""
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 16:
        raise ValueError("Invalid padding")
    if data[-pad_len:] != bytes([pad_len] * pad_len):
        raise ValueError("Invalid padding")
    return data[:-pad_len]


def encrypt_raw(plaintext: bytes, key: bytes) -> bytes:
    """Encrypt bytes with a 32-byte key.
    Returns: iv[16] + ciphertext + hmac[32]
    """
    iv = os.urandom(16)
    padded = _pad(plaintext)

    # CTR-mode encryption using HMAC as PRF
    ciphertext = b""
    for i in range(0, len(padded), 16):
        block = padded[i:i + 16]
        counter_bytes = struct.pack('>Q', i // 16) + iv[:8]
        keystream = hmac.new(key, counter_bytes, 'sha256').digest()[:16]
        ciphertext += bytes(a ^ b for a, b in zip(block, keystream))

    # HMAC-SHA256 for integrity
    mac = hmac.new(key, iv + ciphertext, 'sha256').digest()

    return iv + ciphertext + mac


def decrypt_raw(data: bytes, key: bytes) -> bytes:
    """Decrypt bytes produced by encrypt_raw.
    Raises ValueError on integrity failure or bad padding.
    """
    if len(data) < 64:  # iv(16) + min_block(16) + mac(32)
        raise ValueError("Data too short")

    iv = data[:16]
    mac = data[-32:]
    ciphertext = data[16:-32]

    # Verify HMAC
    expected_mac = hmac.new(key, iv + ciphertext, 'sha256').digest()
    if not hmac.compare_digest(mac, expected_mac):
        raise ValueError("Integrity check failed")

    # Decrypt
    plaintext_padded = b""
    for i in range(0, len(ciphertext), 16):
        block = ciphertext[i:i + 16]
        counter_bytes = struct.pack('>Q', i // 16) + iv[:8]
        keystream = hmac.new(key, counter_bytes, 'sha256').digest()[:16]
        plaintext_padded += bytes(a ^ b for a, b in zip(block, keystream))

    return _unpad(plaintext_padded)


# ==============================================================
#  Password-based key derivation
# ==============================================================

def derive_key(password: str, salt: bytes, iterations: int = 200_000) -> bytes:
    """Derive a 32-byte key from password using PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), salt,
        iterations=iterations, dklen=32,
    )


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
    h = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                            salt, iterations=200_000, dklen=32)
    return base64.b64encode(salt + h).decode('ascii')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against stored hash."""
    try:
        raw = base64.b64decode(password_hash)
        salt = raw[:16]
        stored_hash = raw[16:]
        computed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                       salt, iterations=200_000, dklen=32)
        return hmac.compare_digest(stored_hash, computed)
    except Exception:
        return False
