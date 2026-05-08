"""AES encryption for API keys using password-derived key.

Uses PBKDF2-HMAC-SHA256 to derive key from user password.
Each key is encrypted with a unique salt+IV, so the same plaintext
produces different ciphertext each time.

No external dependencies - pure Python standard library.
"""

import base64
import hashlib
import hmac
import os
import struct


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 32-byte AES key from password using PBKDF2."""
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        iterations=200_000,
        dklen=32,
    )


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


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def encrypt_key(plaintext: str, password: str) -> str:
    """Encrypt an API key with the user's password.
    Returns base64-encoded string: salt[16] + iv[16] + ciphertext + hmac[32]
    """
    if not plaintext:
        return ""

    salt = os.urandom(16)
    iv = os.urandom(16)
    key = _derive_key(password, salt)

    plaintext_bytes = plaintext.encode('utf-8')
    padded = _pad(plaintext_bytes)

    # CTR-mode encryption
    ciphertext = b""
    counter = 0
    for i in range(0, len(padded), 16):
        block = padded[i:i + 16]
        counter_bytes = struct.pack('>Q', counter) + iv[:8]
        keystream = hmac.new(key, counter_bytes, 'sha256').digest()[:16]
        ciphertext += _xor_bytes(block, keystream)
        counter += 1

    # HMAC for integrity
    mac = hmac.new(key, salt + iv + ciphertext, 'sha256').digest()

    return base64.b64encode(salt + iv + ciphertext + mac).decode('ascii')


def decrypt_key(encoded: str, password: str) -> str:
    """Decrypt an API key with the user's password."""
    if not encoded:
        return ""

    raw = base64.b64decode(encoded)

    salt = raw[:16]
    iv = raw[16:32]
    mac = raw[-32:]
    ciphertext = raw[32:-32]

    key = _derive_key(password, salt)

    # Verify HMAC
    expected_mac = hmac.new(key, salt + iv + ciphertext, 'sha256').digest()
    if not hmac.compare_digest(mac, expected_mac):
        raise ValueError("Wrong password or corrupted data")

    # Decrypt
    plaintext_padded = b""
    counter = 0
    for i in range(0, len(ciphertext), 16):
        block = ciphertext[i:i + 16]
        counter_bytes = struct.pack('>Q', counter) + iv[:8]
        keystream = hmac.new(key, counter_bytes, 'sha256').digest()[:16]
        plaintext_padded += _xor_bytes(block, keystream)
        counter += 1

    plaintext_bytes = _unpad(plaintext_padded)
    return plaintext_bytes.decode('utf-8')


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


def hash_password(password: str) -> str:
    """Create a verifiable hash of the password (for unlock check).
    Stores salt[16] + hash[32] as base64.
    """
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                            salt, iterations=200_000, dklen=32)
    return base64.b64encode(salt + h).decode('ascii')
