"""Persistent storage for API keys with password-based encryption."""

import json
import os
from datetime import datetime
from pathlib import Path

from .crypto import encrypt_key, decrypt_key, hash_password, verify_password


# Module-level password cache (set after unlock)
_password: str = ""


def set_password(password: str):
    """Set the active password for encrypt/decrypt operations."""
    global _password
    _password = password


def get_password() -> str:
    return _password


def _get_data_dir() -> Path:
    """Return the writable app data directory, works on desktop and Android."""
    try:
        from kivy.app import App
        app = App.get_running_app()
        if app is not None:
            return Path(app.user_data_dir)
    except Exception:
        pass
    return Path(os.path.expanduser("~"))


def _config_path() -> Path:
    return _get_data_dir() / ".key_manager_config.json"


def _default_config() -> dict:
    return {
        "platforms": {
            "deepseek": {"keys": []},
            "openai": {"keys": []},
            "bailian": {"keys": []},
            "mimo": {"keys": []},
        }
    }


def read_config() -> dict:
    try:
        data = json.loads(_config_path().read_text(encoding="utf-8"))
        for pid in _default_config()["platforms"]:
            if pid not in data.get("platforms", {}):
                data.setdefault("platforms", {})[pid] = {"keys": []}
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return _default_config()


def write_config(data: dict):
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_password_set() -> bool:
    """Check if a master password has been configured."""
    cfg = read_config()
    return bool(cfg.get("password_hash"))


def save_password_hash(password: str):
    """Store the password hash in config (called on first setup)."""
    cfg = read_config()
    cfg["password_hash"] = hash_password(password)
    write_config(cfg)


def check_password(password: str) -> bool:
    """Verify password against stored hash."""
    cfg = read_config()
    stored_hash = cfg.get("password_hash", "")
    if not stored_hash:
        return False
    return verify_password(password, stored_hash)


class DecryptionError(Exception):
    """Raised when a key cannot be decrypted."""
    pass


def get_keys(platform_id: str) -> list:
    """Get decrypted keys. Each key dict has 'key' and 'decrypt_ok' fields."""
    cfg = read_config()
    keys = cfg.get("platforms", {}).get(platform_id, {}).get("keys", [])
    for k in keys:
        try:
            k["key"] = decrypt_key(k["key"], _password)
            k["decrypt_ok"] = True
        except (ValueError, Exception):
            k["key"] = ""
            k["decrypt_ok"] = False
    return keys


def add_key(platform_id: str, name: str, key: str):
    cfg = read_config()
    cfg.setdefault("platforms", {}).setdefault(platform_id, {})
    cfg["platforms"][platform_id].setdefault("keys", [])
    cfg["platforms"][platform_id]["keys"].append({
        "name": name,
        "key": encrypt_key(key, _password),
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    })
    write_config(cfg)


def delete_key(platform_id: str, index: int):
    cfg = read_config()
    keys = cfg.get("platforms", {}).get(platform_id, {}).get("keys", [])
    if 0 <= index < len(keys):
        keys.pop(index)
        write_config(cfg)


def key_count(platform_id: str) -> int:
    """Count keys without decrypting them (fast)."""
    cfg = read_config()
    return len(cfg.get("platforms", {}).get(platform_id, {}).get("keys", []))


def rename_key(platform_id: str, index: int, new_name: str):
    cfg = read_config()
    keys = cfg.get("platforms", {}).get(platform_id, {}).get("keys", [])
    if 0 <= index < len(keys):
        keys[index]["name"] = new_name
        write_config(cfg)


# ----------------------------------------------------------
#  Custom platforms
# ----------------------------------------------------------

def get_custom_platforms() -> list:
    """Return list of user-defined custom platforms."""
    cfg = read_config()
    return cfg.get("custom_platforms", [])


def add_custom_platform(name: str, base_url: str = "", verify_url: str = "",
                        balance_url: str = "", auth_header: str = "Bearer {api_key}"):
    """Add a new custom platform."""
    cfg = read_config()
    customs = cfg.setdefault("custom_platforms", [])

    # Generate a unique id
    pid = name.lower().replace(" ", "_")
    # Avoid duplicates
    existing_ids = [p["id"] for p in customs]
    if pid in existing_ids:
        pid = f"{pid}_{len(existing_ids)}"

    customs.append({
        "id": pid,
        "name": name,
        "base_url": base_url,
        "verify_url": verify_url,
        "balance_url": balance_url,
        "auth_header": auth_header,
    })

    # Also init keys storage for this platform
    cfg.setdefault("platforms", {})[pid] = {"keys": []}
    write_config(cfg)
    return pid


def delete_custom_platform(platform_id: str):
    """Delete a custom platform and its keys."""
    cfg = read_config()
    customs = cfg.get("custom_platforms", [])
    cfg["custom_platforms"] = [p for p in customs if p["id"] != platform_id]
    cfg.get("platforms", {}).pop(platform_id, None)
    write_config(cfg)


def update_custom_platform(platform_id: str, name: str = None, base_url: str = None,
                           verify_url: str = None, balance_url: str = None,
                           auth_header: str = None):
    """Update fields of an existing custom platform."""
    cfg = read_config()
    customs = cfg.get("custom_platforms", [])
    for p in customs:
        if p["id"] == platform_id:
            if name is not None:
                p["name"] = name
            if base_url is not None:
                p["base_url"] = base_url
            if verify_url is not None:
                p["verify_url"] = verify_url
            if balance_url is not None:
                p["balance_url"] = balance_url
            if auth_header is not None:
                p["auth_header"] = auth_header
            break
    write_config(cfg)


def search_key_names(query: str) -> list:
    """Search key names across all platforms without decrypting keys.
    Returns [(platform_id, key_name), ...] — fast, no crypto involved."""
    query = query.strip().lower()
    if not query:
        return []
    cfg = read_config()
    results = []
    for pid, pdata in cfg.get("platforms", {}).items():
        for k in pdata.get("keys", []):
            if query in k.get("name", "").lower():
                results.append((pid, k["name"]))
    return results
