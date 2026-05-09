"""App initialization: font registration and window sizing.

This is the ONLY module with import-time side effects.
Import it once at app startup (in main.py).
"""

import os
import sys

from kivy.core.text import LabelBase
from kivy.metrics import dp
from kivy.utils import platform as kivy_platform

_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "fonts")


def _register_fonts():
    if kivy_platform == "android":
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
        LabelBase.register(
            name="Roboto",
            fn_regular="C:/Windows/Fonts/msyh.ttc",
            fn_bold="C:/Windows/Fonts/msyhbd.ttc",
        )
        LabelBase.register(
            name="Symbol",
            fn_regular="C:/Windows/Fonts/seguisym.ttf",
        )


_register_fonts()

if kivy_platform not in ("android", "ios"):
    from kivy.core.window import Window
    Window.size = (dp(360), dp(640))
