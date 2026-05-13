"""Global background key validation service.

Validates all API keys across all platforms at app startup and caches results.
The cache is consumed by PlatformScreen to show key status without re-verifying.
"""

import threading
import httpx

# (platform_id, key_index) -> "valid" | "invalid" | "error" | "checking"
_status_cache = {}
_generation = 0
_lock = threading.Lock()


def get_status(platform_id, key_index):
    with _lock:
        return _status_cache.get((platform_id, key_index), "unknown")


def set_status(platform_id, key_index, status):
    with _lock:
        _status_cache[(platform_id, key_index)] = status


def validate_all():
    """Validate every key for every platform in a single background thread."""
    global _generation
    with _lock:
        _generation += 1
        gen = _generation

    from . import platform_manager
    from . import storage

    platforms = platform_manager.get_platform_list()

    def _run():
        for plat in platforms:
            if not plat.has_validation:
                continue

            # Read metadata without decrypting
            keys = storage.get_keys(plat.id, decrypt=False)
            for idx, k in enumerate(keys):
                with _lock:
                    if _generation != gen:
                        return

                # Decrypt right before use; raw is overwritten each iteration
                raw, ok = storage.try_decrypt(k["encrypted_key"])
                if not ok or not raw:
                    set_status(plat.id, idx, "error")
                    continue

                set_status(plat.id, idx, "checking")

                try:
                    headers = {"Authorization": plat.auth_header.format(api_key=raw)}
                    with httpx.Client(timeout=8) as client:
                        resp = client.get(plat.validation_url, headers=headers)
                        valid = resp.status_code == 200
                        set_status(plat.id, idx, "valid" if valid else "invalid")
                except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError):
                    set_status(plat.id, idx, "error")
                except Exception:
                    set_status(plat.id, idx, "invalid")

    threading.Thread(target=_run, daemon=True).start()


def on_key_deleted(platform_id, deleted_index):
    """Cancel background validation, then shift cache entries down."""
    global _generation
    with _lock:
        _generation += 1  # cancel running validate_all to avoid stale indices
        _status_cache.pop((platform_id, deleted_index), None)
        to_shift = [
            (idx, _status_cache.pop((platform_id, idx)))
            for idx in sorted(
                [i for (pid, i) in _status_cache if pid == platform_id and i > deleted_index]
            )
        ]
        for old_idx, status in to_shift:
            _status_cache[(platform_id, old_idx - 1)] = status


def cancel():
    global _generation
    with _lock:
        _generation += 1
