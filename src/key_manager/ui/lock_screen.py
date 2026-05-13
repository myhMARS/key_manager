"""Lock screen - password setup, unlock, and biometric authentication."""

from kivy.clock import Clock
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.screenmanager import Screen

from ..core import storage
from ..biometric import (
    is_biometric_available,
    has_stored_password,
    biometric_ready_reason,
    store_password_for_biometric,
    get_stored_password,
    authenticate_biometric,
)


class LockScreen(Screen):
    is_setup = BooleanProperty(False)
    error_text = StringProperty("")
    biometric_available = BooleanProperty(False)
    biometric_button_text = StringProperty("")
    biometric_ready = BooleanProperty(False)

    def on_enter(self, *args):
        self.is_setup = not storage.is_password_set()
        self.error_text = ""
        self._set_content_visible(True)
        # Clear password field
        if hasattr(self, 'ids') and 'password_input' in self.ids:
            self.ids.password_input.text = ""
            if 'confirm_input' in self.ids:
                self.ids.confirm_input.text = ""

        reason = biometric_ready_reason() if not self.is_setup else None
        if self.is_setup:
            if is_biometric_available():
                self.biometric_available = True
                self.biometric_ready = False
                self.biometric_button_text = "Fingerprint unlock will be available after setup"
            else:
                self.biometric_available = False
                self.biometric_button_text = ""
        elif reason == "ready":
            self.biometric_available = True
            self.biometric_ready = True
            self.biometric_button_text = "Use Fingerprint"
        elif reason == "not_stored":
            self.biometric_available = True
            self.biometric_ready = False
            self.biometric_button_text = "Unlock with password to enable fingerprint"
        else:
            self.biometric_available = False
            self.biometric_ready = False
            self.biometric_button_text = ""

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
            # Store for biometric if device supports it
            if is_biometric_available():
                if store_password_for_biometric(password):
                    self.biometric_ready = True
                    self.biometric_button_text = "Use Fingerprint"
            self._go_home()
        else:
            # Verify
            if storage.check_password(password):
                storage.set_password(password)
                # Update biometric store
                if is_biometric_available():
                    if store_password_for_biometric(password):
                        self.biometric_ready = True
                        self.biometric_button_text = "Use Fingerprint"
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
        if not self.biometric_ready:
            return
        if self.biometric_available:
            self.error_text = ""
            self._try_biometric()

    def _go_home(self):
        from ..core import storage
        storage.migrate_masked_fields()
        from ..core.events import bus
        bus.dispatch('on_navigate', 'home', no_transition=True)
