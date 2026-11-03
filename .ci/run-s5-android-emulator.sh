#!/usr/bin/env bash
# Run emulator QA from the S5 snapshot, not from the older repository root.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root/s5src"
test -s app/build.gradle
# Patch the Android-only navigation stress test from the immutable S5 snapshot.
# This retains the 44 per-game checks but avoids one blocking 44-click JS task.
cd "$repo_root"
python3 .ci/patch-s5-webview-test.py
python3 .ci/enable-preupgrade-probe.py
cd "$repo_root/s5src"
test -s tests/android_smoke.sh
test -s app/build/outputs/apk/debug/app-debug.apk
gradle --no-daemon :app:assembleDebugAndroidTest
test -s app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
bash tests/android_smoke.sh
