"""Key Manager - Application entry point."""

import os

import config  # noqa: F401 - registers fonts and sets window size

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import FadeTransition, ScreenManager

from ui.widgets import SnackBar  # noqa: F401 - needed for kv
from ui.home_screen import HomeScreen
from ui.platform_screen import PlatformScreen

# Load all kv files (use os.path for cross-platform compatibility)
_BASE = os.path.dirname(os.path.abspath(__file__))
Builder.load_file(os.path.join(_BASE, 'ui', 'kv', 'widgets.kv'))
Builder.load_file(os.path.join(_BASE, 'ui', 'kv', 'popups.kv'))
Builder.load_file(os.path.join(_BASE, 'ui', 'kv', 'home.kv'))
Builder.load_file(os.path.join(_BASE, 'ui', 'kv', 'platform.kv'))


class KeyManagerApp(App):
    sm = ObjectProperty(None)

    def build(self):
        root = FloatLayout()

        self.sm = ScreenManager(
            size_hint=(1, 1),
            transition=FadeTransition(duration=0.15),
        )
        self.sm.add_widget(HomeScreen())
        self.sm.add_widget(PlatformScreen())
        root.add_widget(self.sm)

        self._root = root
        return root

    def on_start(self):
        """Hide Android loading screen as soon as the app is ready."""
        try:
            from android import hide_loading_screen
            hide_loading_screen()
        except ImportError:
            pass

    def show_snackbar(self, message, snack_type="success"):
        s = SnackBar()
        s.show(self._root, message, snack_type)


if __name__ == "__main__":
    KeyManagerApp().run()
