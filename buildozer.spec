[app]

# App metadata
title = Key Manager
package.name = keymanager
package.domain = org.keymanager
version = 0.1.0

# Source
source.dir = .
source.include_exts = py,png,jpg,kv,ttf,ttc,json

# Entry point
entrypoint = main.py

# Requirements - pin python3 to let p4a choose, pure python deps listed
requirements = python3,kivy,pillow,certifi,httpx,httpcore,idna,sniffio,anyio,h11,pyjnius,android

# Android permissions
android.permissions = INTERNET,USE_BIOMETRIC,USE_FINGERPRINT

# Android API levels
android.minapi = 21
android.api = 34
android.ndk = 25b

# Architecture
android.archs = arm64-v8a

# Orientation
orientation = portrait

# Fullscreen (0 = respect status bar, content starts below it)
fullscreen = 0

# Icon
icon.filename = assets/icon/logo.png

# Presplash - use a minimal 1x1 pixel image matching app background
# to avoid the default Kivy "Loading..." screen
android.presplash_color = #F5F5F5
presplash.filename = assets/presplash.png

# Include files
source.include_patterns = assets/*,src/**/*

# Exclude unnecessary files
source.exclude_dirs = .venv,.idea,__pycache__,.git,.buildozer,bin,tests
source.exclude_patterns = *.pyc,*.pyo,uv.lock,*.md,*.spec

# Log level
log_level = 2

# Android specific
android.accept_sdk_license = True
android.enable_androidx = True

# Pin p4a to a known stable version that supports Python 3.11
p4a.version = 2024.01.21

[buildozer]
warn_on_root = 1
