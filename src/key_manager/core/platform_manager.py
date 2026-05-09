"""Platform list management with lazy loading.

No import-time side effects. Call get_platform_list() to access platforms;
custom platforms are loaded from storage on first access.
"""

_loaded = False


def _ensure_loaded():
    global _loaded
    if not _loaded:
        from .platforms import load_custom_platforms
        load_custom_platforms()
        _loaded = True


def get_platform_list() -> list:
    """Get the current list of all platforms (lazy-loaded)."""
    _ensure_loaded()
    from .platforms import get_platform_list as _get_list
    return _get_list()


def get_total() -> int:
    """Get total platform count."""
    return len(get_platform_list())


def refresh():
    """Reload custom platforms from storage. Call after add/edit/delete."""
    global _loaded
    from .platforms import load_custom_platforms
    load_custom_platforms()
    _loaded = True
