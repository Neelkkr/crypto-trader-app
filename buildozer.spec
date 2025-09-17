[app]

# (str) Title of your application
title = Crypto Trading Bot # <-- YEH BADLO

# (str) Package name
package.name = cryptobot # <-- YEH BADLO

# (str) Package domain (needed for android/ios packaging)
package.domain = org.narendra.bot # <-- YEH BADLO

# (str) Source code where the main.py live
# हमारा main file gui.py है, तो हम उसे यहाँ बताएंगे।
main.py = gui.py
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,spec

# (list) Source files to exclude (let empty to not exclude anything)
# matplotlib और pandas को build से हटा रहे हैं ताकि build फेल न हो।
source.exclude_exts = venv,json

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = __pycache__, .buildozer, bin, venv, tests

# (str) Application versioning (method 1)
version = 1.0

# (list) Application requirements
# ज़रूरी libraries यहाँ डालो। matplotlib और pandas को हटा दिया है।
requirements = python3,kivy,kivymd,python-binance,requests # <-- SABSE ZARURI

# (list) Supported orientations
orientation = portrait

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
# Internet की permission यहाँ दी है।
android.permissions = INTERNET # <-- BAHUT ZARURI

# (int) Target Android API, should be as high as possible.
android.api = 31

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (bool) If True, then automatically accept SDK license
android.accept_sdk_license = True

# (list) The Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1