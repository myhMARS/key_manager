"""Key Manager - Application entry point."""

import os
import sys

# Allow running from repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from key_manager import app_setup  # noqa: F401 - registers fonts, sets window size
from key_manager.core import config  # noqa: F401 - re-exports for other modules

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import FadeTransition, ScreenManager

from key_manager.ui.widgets import SnackBar  # noqa: F401 - needed for kv
from key_manager.ui.lock_screen import LockScreen
from key_manager.ui.home_screen import HomeScreen
from key_manager.ui.platform_screen import PlatformScreen
from key_manager.core.events import bus
from key_manager.core import platform_manager
from key_manager.core import storage
from key_manager.core import key_validator

# Load all kv files
_BASE = os.path.dirname(os.path.abspath(__file__))
_KV_DIR = os.path.join(_BASE, 'src', 'key_manager', 'ui', 'kv')
Builder.load_file(os.path.join(_KV_DIR, 'widgets.kv'))
Builder.load_file(os.path.join(_KV_DIR, 'popups.kv'))
Builder.load_file(os.path.join(_KV_DIR, 'lock.kv'))
Builder.load_file(os.path.join(_KV_DIR, 'home.kv'))
Builder.load_file(os.path.join(_KV_DIR, 'platform.kv'))


class KeyManagerApp(App):
    sm = ObjectProperty(None)

    def build(self):
        root = FloatLayout()

        self.sm = ScreenManager(
            size_hint=(1, 1),
            transition=FadeTransition(duration=0.12),
        )
        # Set a background color on the ScreenManager to prevent black flash
        from kivy.graphics import Color, Rectangle
        with self.sm.canvas.before:
            Color(0.96, 0.96, 0.96, 1)
            self._sm_bg = Rectangle(pos=self.sm.pos, size=self.sm.size)
        self.sm.bind(pos=lambda *a: setattr(self._sm_bg, 'pos', self.sm.pos))
        self.sm.bind(size=lambda *a: setattr(self._sm_bg, 'size', self.sm.size))

        self.sm.add_widget(LockScreen())
        self.sm.add_widget(HomeScreen())
        self.sm.add_widget(PlatformScreen())
        root.add_widget(self.sm)

        self._root = root
        return root

    def on_start(self):
        """Hide Android loading screen and wire up event bus."""
        try:
            from android import hide_loading_screen
            hide_loading_screen()
        except ImportError:
            pass

        self._startup_validated = False

        # Wire event bus for navigation
        bus.bind(on_navigate=self._on_navigate)
        bus.bind(on_key_deleted=self._on_key_changed)
        bus.bind(on_key_added=self._on_key_changed)
        bus.bind(on_key_renamed=self._on_key_changed)
        bus.bind(on_platform_added=self._on_platform_changed)
        bus.bind(on_platform_deleted=self._on_platform_deleted)
        bus.bind(on_platform_updated=self._on_platform_changed)

    def _on_navigate(self, _, screen_name, **kwargs):
        """Handle navigation events from any component."""
        no_transition = kwargs.pop('no_transition', False)

        if no_transition:
            from kivy.uix.screenmanager import NoTransition
            old_transition = self.sm.transition
            self.sm.transition = NoTransition()

        if screen_name == 'platform':
            platform_id = kwargs.get('platform_id', '')
            self.sm.get_screen('platform').load_platform(platform_id)
            self.sm.current = 'platform'
        elif screen_name == 'verify_key':
            platform_id = kwargs.get('platform_id', '')
            key = kwargs.get('key', '')
            screen = self.sm.get_screen('platform')
            if screen.platform_id == platform_id:
                screen.trigger_check(key)
        elif screen_name == 'home':
            self.sm.current = 'home'
            if not self._startup_validated:
                self._startup_validated = True
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: key_validator.validate_all(), 0.8)

        if no_transition:
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: setattr(self.sm, 'transition', old_transition), 0.1)

    def _on_key_changed(self, _, platform_id, **kwargs):
        """Handle key mutations: perform delete if needed, then refresh."""
        key_index = kwargs.get('key_index', None)
        if key_index is not None:
            storage.delete_key(platform_id, key_index)
            key_validator.on_key_deleted(platform_id, key_index)
        screen = self.sm.get_screen('platform')
        if screen.platform_id == platform_id:
            screen.refresh_keys()

    def _on_platform_changed(self, _, platform_id):
        """Rebuild home deck and reload platform screen after platform changes."""
        platform_manager.refresh()
        home = self.sm.get_screen('home')
        home.rebuild_deck()
        # Reload platform screen if it's showing the changed platform
        screen = self.sm.get_screen('platform')
        if screen.platform_id == platform_id:
            screen.load_platform(platform_id)

    def _on_platform_deleted(self, _, platform_id):
        """Handle platform deletion: delete data, navigate home, rebuild."""
        storage.delete_custom_platform(platform_id)
        platform_manager.refresh()
        self.sm.current = 'home'
        home = self.sm.get_screen('home')
        home.rebuild_deck()
        self.show_snackbar("Platform deleted", "warning")

    # ----------------------------------------------------------
    #  Auto-lock on pause/resume
    # ----------------------------------------------------------

    def on_pause(self):
        """App going to background — record timestamp."""
        import time
        self._pause_time = time.time()
        return True  # Allow pause (required for Android)

    def on_resume(self):
        """App returning from background — lock if timeout exceeded."""
        from kivy.clock import Clock

        def _check_lock(dt):
            try:
                import time
                pause_time = getattr(self, '_pause_time', 0)
                elapsed = time.time() - pause_time if pause_time else 0
                # Lock after 60 seconds in background
                if elapsed > 60 and self.sm and self.sm.current != 'lock':
                    storage.set_password("")  # Clear cached password
                    self.sm.current = 'lock'
            except Exception:
                pass

        # Defer to next frame to let Kivy fully restore
        Clock.schedule_once(_check_lock, 0.2)

    def show_snackbar(self, message, snack_type="success"):
        if not hasattr(self, '_snackbar'):
            self._snackbar = SnackBar()
        self._snackbar.show(self._root, message, snack_type)


if __name__ == "__main__":
    KeyManagerApp().run()
