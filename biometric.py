"""Biometric/device authentication support for Android.

Uses Android KeyguardManager.createConfirmDeviceCredentialIntent()
which supports fingerprint, face, PIN, pattern - whatever the user has set up.
Falls back gracefully on non-Android platforms.
"""

import base64
from kivy.utils import platform as kivy_platform


def is_biometric_available() -> bool:
    """Check if device credential authentication is available."""
    if kivy_platform != 'android':
        return False
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Context = autoclass('android.content.Context')
        activity = PythonActivity.mActivity
        km = activity.getSystemService(Context.KEYGUARD_SERVICE)
        # isDeviceSecure() returns True if PIN/pattern/password/biometric is set
        return km.isDeviceSecure()
    except Exception:
        return False


def has_stored_password() -> bool:
    """Check if a password is stored for biometric unlock."""
    if kivy_platform != 'android':
        return False
    try:
        prefs = _get_prefs()
        return prefs.contains("enc_password")
    except Exception:
        return False


def store_password_for_biometric(password: str):
    """Store password for biometric unlock in app-private SharedPreferences."""
    if kivy_platform != 'android':
        return
    try:
        encoded = base64.b64encode(password.encode('utf-8')).decode('ascii')
        prefs = _get_prefs()
        editor = prefs.edit()
        editor.putString("enc_password", encoded)
        editor.apply()
    except Exception:
        pass


def get_stored_password() -> str:
    """Retrieve the stored password after device auth succeeds."""
    if kivy_platform != 'android':
        return ""
    try:
        prefs = _get_prefs()
        encoded = prefs.getString("enc_password", "")
        if encoded:
            return base64.b64decode(encoded.encode('ascii')).decode('utf-8')
        return ""
    except Exception:
        return ""


def clear_stored_password():
    """Remove stored biometric password."""
    if kivy_platform != 'android':
        return
    try:
        prefs = _get_prefs()
        editor = prefs.edit()
        editor.remove("enc_password")
        editor.apply()
    except Exception:
        pass


def authenticate_biometric(on_success, on_failure):
    """Launch device credential confirmation (fingerprint/face/PIN).
    
    Uses startActivityForResult with KeyguardManager intent.
    """
    if kivy_platform != 'android':
        on_failure("Not available")
        return

    try:
        from jnius import autoclass
        from android import activity as android_activity
        from kivy.clock import Clock

        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Context = autoclass('android.content.Context')
        Intent = autoclass('android.content.Intent')

        activity = PythonActivity.mActivity
        km = activity.getSystemService(Context.KEYGUARD_SERVICE)

        REQUEST_CODE = 7789

        intent = km.createConfirmDeviceCredentialIntent(
            "Unlock Key Manager",
            "Authenticate to access your keys"
        )

        if intent is None:
            on_failure("No device lock set")
            return

        def on_activity_result(request_code, result_code, data):
            if request_code != REQUEST_CODE:
                return
            # RESULT_OK = -1
            if result_code == -1:
                Clock.schedule_once(lambda dt: on_success(), 0)
            else:
                Clock.schedule_once(lambda dt: on_failure("Authentication cancelled"), 0)
            # Unbind after use
            android_activity.unbind(on_activity_result=on_activity_result)

        android_activity.bind(on_activity_result=on_activity_result)
        activity.startActivityForResult(intent, REQUEST_CODE)

    except Exception as e:
        on_failure(f"Auth error: {e}")


def _get_prefs():
    """Get Android SharedPreferences."""
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Context = autoclass('android.content.Context')
    activity = PythonActivity.mActivity
    return activity.getSharedPreferences("km_biometric", Context.MODE_PRIVATE)
