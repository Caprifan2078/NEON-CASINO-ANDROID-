#!/bin/bash
set -u
cd "$(dirname "$0")"
SDK="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
ADB="$(command -v adb 2>/dev/null || true)"
if [ -z "$ADB" ] && [ -x "$SDK/platform-tools/adb" ]; then ADB="$SDK/platform-tools/adb"; fi
if [ -z "$ADB" ]; then
  echo 'Не найден adb. Установите Android Studio → SDK Manager → Android SDK Platform-Tools.'
  read -r -p 'Нажмите Enter для выхода... ' _
  exit 1
fi
APK='app/build/outputs/apk/debug/app-debug.apk'
if [ ! -f "$APK" ]; then
  echo 'Сначала соберите APK в Android Studio через Build → Build APK(s).'
  read -r -p 'Нажмите Enter для выхода... ' _
  exit 1
fi
LOG="$(pwd)/ANDROID_INSTALL_RESULT.txt"
{
 echo "NEON CASINO install test: $(date)"
 echo "APK: $APK"
 "$ADB" devices -l
 echo 'Installing the separate QA package; NO uninstall will be performed.'
 "$ADB" install -r "$APK"
} 2>&1 | tee "$LOG"
echo "
Результат записан в: $LOG"
read -r -p 'Нажмите Enter для выхода... ' _
