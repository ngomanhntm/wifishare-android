[app]

# (str) Title of your application
title = Test Kivy App

# (str) Package name
package.name = testkivyapp

# (str) Package domain (needed for android/ios packaging)
package.domain = org.test

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas

# (str) Application versioning (method 1)
version = 0.1

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

[android]

# (str) Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
# You can also specify multiple archs separated by comma: armeabi-v7a,arm64-v8a
arch = arm64-v8a

# (int) Target Android API, should be as high as possible.
api = 33

# (int) Minimum API your APK will support.
minapi = 21

# (str) Android NDK version to use
ndk = 25b

# (str) Android SDK version to use
sdk = 33

# (bool) Use --private data storage (True) or --dir public storage (False)
private_storage = True
