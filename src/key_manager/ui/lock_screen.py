"""Lock screen - password setup, unlock, and biometric authentication."""

from kivy.clock import Clock
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.screenmanager import Screen

from ..core import storage
from ..biometric import (
    is_biometric_available,
    has_stored_password,
    store_password_for_biometric,
    get_stored_password,
    authenticate_biometric,
)


class LockScreen(Screen):
    is_setup = BooleanProperty(False)
    error_text = StringProperty("")
    biometric_available = BooleanProperty(False)

    def on_enter(self, *args):
        self.is_setup = not storage.is_password_set()
        self.error_text = ""
        self._set_content_visible(True)
        # Clear password field
        if hasattr(self, 'ids') and 'password_input' in self.ids:
            self.ids.password_input.text = ""
            if 'confirm_input' in self.ids:
                self.ids.confirm_input.text = ""
        self.biometric_available = (
            not self.is_setup
            and is_biometric_available()
            and has_stored_password()
        )
        # Don't auto-trigger biometric - let user see the lock screen first
        # They can tap "Use Fingerprint" button when ready

    def on_submit(self):
        password = self.ids.password_input.text.strip()

        if not password:
            self.error_text = "Password is required"
            return

        if self.is_setup:
            confirm = self.ids.confirm_input.text.strip()
            if password != confirm:
                self.error_text = "Passwords do not match"
                return
            if len(password) < 4:
                self.error_text = "Password must be at least 4 characters"
                return
            # Save and unlock
            storage.save_password_hash(password)
            storage.set_password(password)
            # Store for biometric if available
            if is_biometric_available():
                store_password_for_biometric(password)
            self._go_home()
        else:
            # Verify
            if storage.check_password(password):
                storage.set_password(password)
                # Update biometric store
                if is_biometric_available():
                    store_password_for_biometric(password)
                self._go_home()
            else:
                self.error_text = "Wrong password"

    def _try_biometric(self):
        """Attempt biometric authentication."""
        # Hide form content before system dialog appears
        # so when app resumes, user sees clean background instead of form flash
        self._set_content_visible(False)

        def on_success():
            password = get_stored_password()
            if password and storage.check_password(password):
                storage.set_password(password)
                # Navigate after a brief moment for smooth transition
                Clock.schedule_once(lambda dt: self._go_home(), 0.1)
            else:
                self._set_content_visible(True)
                self.error_text = "Biometric unlock failed, use password"

        def on_failure(msg):
            self._set_content_visible(True)
            if "Use Password" not in msg:
                self.error_text = msg

        authenticate_biometric(on_success, on_failure)

    def _set_content_visible(self, visible):
        """Show/hide the lock screen form content."""
        container = self.ids.get('lock_content', None)
        if container:
            container.opacity = 1 if visible else 0

    def on_biometric_tap(self):
        """Manual biometric trigger (tap fingerprint button)."""
        if self.biometric_available:
            self.error_text = ""
            self._try_biometric()

    def _go_home(self):
        from ..core.events import bus
        bus.dispatch('on_navigate', 'home', no_transition=True)
