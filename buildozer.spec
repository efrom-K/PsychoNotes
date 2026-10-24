[app]
title = PsychoNotes
package.name = psychonotes
package.domain = io.github.efrom_k
source.dir = .
source.include_exts = py,kv,otf,png
source.exclude_dirs = tools,docs,.venv,bin,.buildozer
source.exclude_patterns = test_*.py
version = 2.0.0
requirements = python3,kivy==2.3.1
icon.filename = %(source.dir)s/assets/icon.png
orientation = portrait
fullscreen = 0
android.api = 34
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = False
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
