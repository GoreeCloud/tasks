#!/bin/sh
# Inspect a compiled GoreeCloud Tasks debug APK without installing it.
set -eu

if [ "$#" -ne 1 ] || [ ! -s "$1" ]; then
  echo "Usage: sh android/tests/verify_debug_apk.sh /path/to/app-debug.apk" >&2
  exit 2
fi

apk=$1
sdk=${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}
if [ -z "$sdk" ]; then
  echo "ANDROID_HOME or ANDROID_SDK_ROOT is required" >&2
  exit 2
fi
aapt="$sdk/build-tools/35.0.0/aapt"
apksigner="$sdk/build-tools/35.0.0/apksigner"
if [ ! -x "$aapt" ] || [ ! -x "$apksigner" ]; then
  echo "Android 35 build tools are required" >&2
  exit 2
fi

"$apksigner" verify --verbose "$apk"

badging=$("$aapt" dump badging "$apk")
case "$badging" in
  *"package: name='com.goreecloud.tasks'"*) ;;
  *) echo "Unexpected Android package ID" >&2; exit 1 ;;
esac
case "$badging" in
  *"sdkVersion:'26'"*) ;;
  *) echo "Unexpected minimum Android SDK" >&2; exit 1 ;;
esac
case "$badging" in
  *"targetSdkVersion:'35'"*) ;;
  *) echo "Unexpected target Android SDK" >&2; exit 1 ;;
esac

permissions=$("$aapt" dump permissions "$apk")
if printf '%s\n' "$permissions" | grep -Eq "uses-permission: name='android.permission.(INTERNET|READ_EXTERNAL_STORAGE|WRITE_EXTERNAL_STORAGE|MANAGE_EXTERNAL_STORAGE|READ_MEDIA_[A-Z_]+|REQUEST_INSTALL_PACKAGES)'"; then
  echo "Disallowed network, media, storage or package-install permission" >&2
  exit 1
fi

manifest=$("$aapt" dump xmltree "$apk" AndroidManifest.xml)
if ! printf '%s\n' "$manifest" | grep -Eq 'android:allowBackup.*0x0$'; then
  echo "Android automatic app backup must remain disabled" >&2
  exit 1
fi

sha256sum "$apk"
echo "GOREECLOUD_TASKS_APK_POLICY_PASS"
