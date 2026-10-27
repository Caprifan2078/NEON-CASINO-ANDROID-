#!/usr/bin/env bash
set -euo pipefail
apk='app/build/outputs/apk/debug/app-debug.apk'
package='com.neon.play.simulator.qa'
activity="$package/com.neon.play.simulator.MainActivity"
adb install -r "$apk"
adb shell am force-stop "$package" || true
adb logcat -c
adb shell am start -W -n "$activity"
ready=0
for attempt in $(seq 1 30); do
  if adb logcat -d -s NEON_QA:I '*:S' | grep -q 'WEB_READY_v1.7.4_games44'; then
    ready=1
    break
  fi
  if adb logcat -d -s AndroidRuntime:E '*:S' | grep -q 'FATAL EXCEPTION'; then
    echo 'FAIL: Android application crashed' >&2
    adb logcat -d -s AndroidRuntime:E '*:S' | tail -100
    exit 1
  fi
  sleep 1
done
if [[ "$ready" -ne 1 ]]; then
  echo 'FAIL: game did not report a ready screen on Android' >&2
  adb logcat -d -s NEON_QA:I NEON_QA:E AndroidRuntime:E '*:S' | tail -120
  exit 1
fi
if [[ -z "$(adb shell pidof "$package" | tr -d '\r')" ]]; then
  echo 'FAIL: Android app exited after reporting ready' >&2
  exit 1
fi
echo 'PASS: Android APK installed, launched, 44-game UI initialized'
