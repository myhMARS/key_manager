"""Backward-compatible re-exports.

Actual logic lives in:
  - setup.py          (fonts, window size — import-time side effects)
  - theme.py          (colors, accent utilities)
  - platform_manager.py (platform list, lazy loading)
"""

# Re-export theme
from theme import PLATFORM_COLORS, DEFAULT_CUSTOM_COLOR, accent_bg, accent_icon_bg

# Re-export platform manager
from platform_manager import get_platform_list, get_total, refresh as refresh_platforms
