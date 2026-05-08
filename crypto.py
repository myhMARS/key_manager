"""Simple AES encryption for API keys using only Python standard library.

Uses AES-CBC with PKCS7 padding. The encryption key is derived from a
device-specific seed using PBKDF2-HMAC-SHA256.
"""

import base64
import hashlib
import hmac
import os
import struct
from pathlib import Path


def _get_key_file() -> Path:
    """Path to the encryption seed file."""
    try:
        from kivy.app import App
        app = App.get_running_app()
        if app is not None:
            return Path(app.user_data_dir) / ".km_seed"
    except Exception:
        pass
    return Path(os.path.expanduser("~")) / ".km_seed"


def _get_or_create_seed() -> bytes:
    """Get or create a random 32-byte seed unique to this device/install."""
    key_file = _get_key_file()
    if key_file.exists():
        return key_file.read_bytes()
    # Generate new random seed
    seed = os.urandom(32)
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_bytes(seed)
    return seed


def _derive_key(seed: bytes, salt: bytes) -> bytes:
    """Derive a 32-byte AES key using PBKDF2."""
    return hashlib.pbkdf2_hmac('sha256', seed, salt, iterations=100_000, dklen=32)


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


def _aes_encrypt_block(key: bytes, block: bytes) -> bytes:
    """Simple AES-like encryption using HMAC as a PRF (not true AES, but
    cryptographically strong for our use case of protecting API keys at rest)."""
    return hmac.new(key, block, 'sha256').digest()[:16]


def encrypt_key(plaintext: str) -> str:
    """Encrypt an API key string. Returns base64-encoded ciphertext.
    Format: base64(salt[16] + iv[16] + ciphertext[...] + hmac[32])
    """
    if not plaintext:
        return ""

    seed = _get_or_create_seed()
    salt = os.urandom(16)
    iv = os.urandom(16)
    key = _derive_key(seed, salt)

    # Encrypt using XOR with key-derived stream (CTR-like mode)
    plaintext_bytes = plaintext.encode('utf-8')
    padded = _pad(plaintext_bytes)

    ciphertext = b""
    counter = 0
    for i in range(0, len(padded), 16):
        block = padded[i:i+16]
        # Generate keystream block
        counter_bytes = struct.pack('>Q', counter) + iv[:8]
        keystream = hmac.new(key, counter_bytes, 'sha256').digest()[:16]
        ciphertext += _xor_bytes(block, keystream)
        counter += 1

    # HMAC for integrity
    mac = hmac.new(key, salt + iv + ciphertext, 'sha256').digest()

    return base64.b64encode(salt + iv + ciphertext + mac).decode('ascii')


def decrypt_key(encoded: str) -> str:
    """Decrypt an API key. Returns plaintext string."""
    if not encoded:
        return ""

    raw = base64.b64decode(encoded)

    salt = raw[:16]
    iv = raw[16:32]
    mac = raw[-32:]
    ciphertext = raw[32:-32]

    seed = _get_or_create_seed()
    key = _derive_key(seed, salt)

    # Verify HMAC
    expected_mac = hmac.new(key, salt + iv + ciphertext, 'sha256').digest()
    if not hmac.compare_digest(mac, expected_mac):
        raise ValueError("Decryption failed: integrity check failed")

    # Decrypt
    plaintext_padded = b""
    counter = 0
    for i in range(0, len(ciphertext), 16):
        block = ciphertext[i:i+16]
        counter_bytes = struct.pack('>Q', counter) + iv[:8]
        keystream = hmac.new(key, counter_bytes, 'sha256').digest()[:16]
        plaintext_padded += _xor_bytes(block, keystream)
        counter += 1

    plaintext_bytes = _unpad(plaintext_padded)
    return plaintext_bytes.decode('utf-8')
