"""App-wide configuration: fonts, window size, color constants."""

import os
import sys

from kivy.core.text import LabelBase
from kivy.metrics import dp
from kivy.utils import platform as kivy_platform

# ----------------------------------------------------------
#  Font registration (platform-aware)
# ----------------------------------------------------------
_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def _register_fonts():
    """Register fonts based on the current platform."""
    if kivy_platform == "android":
        # Use bundled fonts on Android
        LabelBase.register(
            name="Roboto",
            fn_regular=os.path.join(_FONT_DIR, "NotoSansSC-Regular.ttf"),
            fn_bold=os.path.join(_FONT_DIR, "NotoSansSC-Bold.ttf"),
        )
        LabelBase.register(
            name="Symbol",
            fn_regular=os.path.join(_FONT_DIR, "NotoSansSymbols2-Regular.ttf"),
        )
    elif sys.platform == "win32":
        # Use system fonts on Windows
        LabelBase.register(
            name="Roboto",
            fn_regular="C:/Windows/Fonts/msyh.ttc",
            fn_bold="C:/Windows/Fonts/msyhbd.ttc",
        )
        LabelBase.register(
            name="Symbol",
            fn_regular="C:/Windows/Fonts/seguisym.ttf",
        )
    # On other platforms (Linux/macOS), Kivy's default Roboto is used


_register_fonts()

# ----------------------------------------------------------
#  Window size (desktop only)
# ----------------------------------------------------------
if kivy_platform not in ("android", "ios"):
    from kivy.core.window import Window
    Window.size = (dp(360), dp(640))

# ----------------------------------------------------------
#  Platform accent colors
# ----------------------------------------------------------
PLATFORM_COLORS = {
    "deepseek": (0.31, 0.27, 0.90, 1),
    "openai":   (0.06, 0.64, 0.50, 1),
    "bailian":  (0.98, 0.45, 0.09, 1),
    "mimo":     (0.55, 0.36, 0.76, 1),
}

# Default color for custom platforms
DEFAULT_CUSTOM_COLOR = (0.4, 0.4, 0.4, 1)

# Load custom platforms from storage
from platforms import load_custom_platforms, get_platform_list
load_custom_platforms()


def get_platforms():
    """Return current platform list (refreshable)."""
    return get_platform_list()


def get_total():
    """Return current total platform count."""
    return len(get_platform_list())


# For backward compat
PLATFORM_LIST = get_platforms()
TOTAL = get_total()


def refresh_platforms():
    """Reload platforms from storage. Call after adding/removing custom platforms."""
    global PLATFORM_LIST, TOTAL
    load_custom_platforms()
    PLATFORM_LIST = get_platform_list()
    TOTAL = len(PLATFORM_LIST)


def accent_bg(color):
    r, g, b, _ = color
    return (r, g, b, 0.09)


def accent_icon_bg(color):
    r, g, b, _ = color
    return (r, g, b, 0.12)
