"""Biometric/device authentication support for Android.

Uses Android KeyguardManager.createConfirmDeviceCredentialIntent()
which supports fingerprint, face, PIN, pattern - whatever the user has set up.
Falls back gracefully on non-Android platforms.
"""

import base64

from kivy.utils import platform as kivy_platform


def _get_prefs():
    """Get Android SharedPreferences for biometric password storage."""
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Context = autoclass('android.content.Context')
    activity = PythonActivity.mActivity
    return activity.getSharedPreferences("km_biometric", Context.MODE_PRIVATE)


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
    except Exception as e:
        print(f"[biometric] is_biometric_available check failed: {e}")
        return False


def has_stored_password() -> bool:
    """Check if a password is stored for biometric unlock."""
    if kivy_platform != 'android':
        return False
    try:
        prefs = _get_prefs()
        return prefs.contains("enc_password")
    except Exception as e:
        print(f"[biometric] has_stored_password check failed: {e}")
        return False


def biometric_ready_reason() -> str:
    """Return a diagnostic string explaining biometric readiness.

    Used by the lock screen to show the user why biometric is or isn't available.
    """
    if kivy_platform != 'android':
        return "not_android"
    try:
        if not is_biometric_available():
            return "no_device_lock"
        if not has_stored_password():
            return "not_stored"
        return "ready"
    except Exception as e:
        print(f"[biometric] biometric_ready_reason failed: {e}")
        return "error"


def store_password_for_biometric(password: str) -> bool:
    """Store password encrypted with device-bound key in SharedPreferences.

    Returns True on success, False on failure.
    Uses commit() for synchronous disk persistence.
    """
    if kivy_platform != 'android':
        return False
    try:
        encrypted = _encrypt_for_storage(password)
        prefs = _get_prefs()
        editor = prefs.edit()
        editor.putString("enc_password", encrypted)
        editor.commit()
        return True
    except Exception as e:
        print(f"[biometric] store_password_for_biometric failed: {e}")
        return False


def get_stored_password() -> str:
    """Retrieve and decrypt the stored password after device auth succeeds."""
    if kivy_platform != 'android':
        return ""
    try:
        prefs = _get_prefs()
        encoded = prefs.getString("enc_password", "")
        if encoded:
            return _decrypt_from_storage(encoded)
        return ""
    except Exception as e:
        print(f"[biometric] get_stored_password failed: {e}")
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


_KEYSTORE_KEY = None
_KEYSTORE_ERROR = None
_USE_SOFTWARE_FALLBACK = False


def _init_keystore_key():
    """Generate or retrieve an encryption key for biometric password storage.

    On API 23+ uses Android Keystore (hardware-backed, non-exportable).
    On API 21-22 falls back to a key derived from ANDROID_ID (software).

    Returns the key on success, or None if unavailable.
    """
    global _KEYSTORE_KEY, _KEYSTORE_ERROR, _USE_SOFTWARE_FALLBACK
    if _KEYSTORE_KEY is not None:
        return _KEYSTORE_KEY
    if _KEYSTORE_ERROR is not None:
        return None

    # --- Try hardware Keystore (API 23+) ---
    try:
        from jnius import autoclass

        KeyStore = autoclass('java.security.KeyStore')
        KeyGenerator = autoclass('javax.crypto.KeyGenerator')
        KeyGenParameterSpec = autoclass('android.security.keystore.KeyGenParameterSpec')
        KeyProperties = autoclass('android.security.keystore.KeyProperties')

        # KeyGenParameterSpec.Builder only exists on API 23+
        if not hasattr(KeyGenParameterSpec, 'Builder'):
            raise RuntimeError("KeyGenParameterSpec.Builder not available")

        ANDROID_KEYSTORE = "AndroidKeyStore"
        KEY_ALIAS = "km_biometric_key"

        key_store = KeyStore.getInstance(ANDROID_KEYSTORE)
        key_store.load(None)

        if not key_store.containsAlias(KEY_ALIAS):
            key_gen = KeyGenerator.getInstance(
                KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)

            spec_builder = KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT,
            )
            spec_builder.setBlockModes([KeyProperties.BLOCK_MODE_GCM])
            spec_builder.setEncryptionPaddings([KeyProperties.ENCRYPTION_PADDING_NONE])
            spec_builder.setKeySize(256)

            key_gen.init(spec_builder.build())
            key_gen.generateKey()

        _KEYSTORE_KEY = key_store.getKey(KEY_ALIAS, None)
        return _KEYSTORE_KEY

    except Exception:
        pass

    # --- Software fallback (API < 23) ---
    try:
        from jnius import autoclass
        from .core.crypto import derive_key

        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Settings = autoclass('android.provider.Settings$Secure')
        activity = PythonActivity.mActivity
        android_id = Settings.getString(
            activity.getContentResolver(), "android_id")

        seed = f"{android_id}:org.keymanager.keymanager"
        _KEYSTORE_KEY = derive_key(seed, b'km_bio_salt', 100_000)
        _USE_SOFTWARE_FALLBACK = True
        return _KEYSTORE_KEY

    except Exception as e:
        _KEYSTORE_ERROR = str(e)
        return None


def _encrypt_for_storage(plaintext: str) -> str:
    """Encrypt password with Android Keystore key (or software fallback)."""
    key = _init_keystore_key()
    if key is None:
        raise RuntimeError(f"Keystore unavailable: {_KEYSTORE_ERROR}")

    if _USE_SOFTWARE_FALLBACK:
        from .core.crypto import encrypt_raw
        payload = encrypt_raw(plaintext.encode('utf-8'), key)
        return base64.b64encode(payload).decode('ascii')

    from jnius import autoclass

    Cipher = autoclass('javax.crypto.Cipher')
    cipher = Cipher.getInstance("AES/GCM/NoPadding")
    cipher.init(Cipher.ENCRYPT_MODE, key)
    # Let Android generate the IV; GCM output: iv[12] + ciphertext + tag[16]
    ciphertext = cipher.doFinal(plaintext.encode('utf-8'))
    return base64.b64encode(bytes(ciphertext)).decode('ascii')


def _decrypt_from_storage(encoded: str) -> str:
    """Decrypt password with Android Keystore key (or software fallback)."""
    key = _init_keystore_key()
    if key is None:
        raise RuntimeError(f"Keystore unavailable: {_KEYSTORE_ERROR}")

    if _USE_SOFTWARE_FALLBACK:
        from .core.crypto import decrypt_raw
        payload = base64.b64decode(encoded)
        return decrypt_raw(payload, key).decode('utf-8')

    from jnius import autoclass

    Cipher = autoclass('javax.crypto.Cipher')
    GCMParameterSpec = autoclass('javax.crypto.spec.GCMParameterSpec')

    raw = base64.b64decode(encoded)
    iv = raw[:12]
    tagged_ciphertext = raw[12:]

    cipher = Cipher.getInstance("AES/GCM/NoPadding")
    spec = GCMParameterSpec(128, iv)
    cipher.init(Cipher.DECRYPT_MODE, key, spec)
    plaintext_bytes = cipher.doFinal(tagged_ciphertext)
    return bytes(plaintext_bytes).decode('utf-8')
