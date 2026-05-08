"""Persistent storage for API keys using JSON file with encryption."""

import json
import os
from datetime import datetime
from pathlib import Path

from crypto import encrypt_key, decrypt_key


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


def get_keys(platform_id: str) -> list:
    cfg = read_config()
    keys = cfg.get("platforms", {}).get(platform_id, {}).get("keys", [])
    # Decrypt keys on read
    for k in keys:
        k["key"] = decrypt_key(k["key"])
    return keys


def add_key(platform_id: str, name: str, key: str):
    cfg = read_config()
    cfg.setdefault("platforms", {}).setdefault(platform_id, {})
    cfg["platforms"][platform_id].setdefault("keys", [])
    cfg["platforms"][platform_id]["keys"].append({
        "name": name,
        "key": encrypt_key(key),
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
    return len(get_keys(platform_id))


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
