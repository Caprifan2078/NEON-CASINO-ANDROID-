#!/usr/bin/env bash
# Run emulator QA from the S5 snapshot, not from the older repository root.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root/s5src"
test -s app/build.gradle
test -s tests/android_smoke.sh
test -s app/build/outputs/apk/debug/app-debug.apk
gradle --no-daemon :app:assembleDebugAndroidTest
test -s app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
bash tests/android_smoke.sh
