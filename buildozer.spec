[app]

# (str) Title of your application
title = Crypto Trading Bot

# (str) Package name
package.name = cryptobot

# (str) Package domain (needed for android/ios packaging)
package.domain = org.narendra.bot

# (str) Source code where the main.py live
# अब हमारा main file main.py है।
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,spec

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = __pycache__, .buildozer, bin, venv, tests

# (str) Application versioning (method 1)
version = 1.0

# (list) Application requirements
# Kivy App के लिए सभी ज़रूरी libraries.
requirements = python3,kivy,kivymd,python-binance,requests

# (list) Supported orientations
orientation = portrait

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET

# (int) Target Android API, should be as high as possible.
android.api = 31

# (int) Minimum API your APK / AAB will support.
android.minapi = 24

# (str) Android NDK version to use
android.ndk = 25b

# (bool) If True, then automatically accept SDK license
android.accept_sdk_license = True

# (list) The Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

#
# Python for android (p4a) specific
#
# (str) python-for-android branch to use, defaults to master
# हम इसे develop पर set कर रहे हैं ताकि latest fixes मिलें।
p4a.branch = develop

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1