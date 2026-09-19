[app]
title = Plant Doctor
package.name = plantdoctor
package.domain = com.plantdoctor
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt
source.exclude_exts = spec,pyc,pyo,pyd,log,md
source.exclude_dirs = .git,.idea,.venv,venv,__pycache__,bin,tests,ai_model,data
source.exclude_patterns = .buildozer/*,photos/*,ai_model/*.pth,ai_model/data/*,*.git/*,*.DS_Store
version = 1.0.0
requirements = python3,kivy==2.3.0,requests,charset_normalizer,idna,urllib3,certifi,pyjnius,android,pillow,qrcode,numpy,opencv
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,CAMERA,READ_EXTERNAL_STORAGE,READ_MEDIA_IMAGES
android.features = android.hardware.camera,android.hardware.camera.autofocus
android.api = 33
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24
android.accept_sdk_license = True
android.private_storage = True
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.presplash_color = #2E7D32
android.release_artifact = apk
android.debug_artifact = apk
android.manifest.orientation = portrait
android.copy_libs = 1
android.logcat_filters = *:S python:D PythonActivity:D
android.extra_manifest_application_arguments = src/android/extra_manifest_application_arguments.xml
android.extra_manifest_xml = src/android/extra_manifest.xml
android.add_src = src/android
p4a.local_recipes = 
p4a.bootstrap = sdl2
[buildozer]
log_level = 2
warn_on_root = 1
