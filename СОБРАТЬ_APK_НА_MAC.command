#!/bin/bash
# Build a standard APK with official Android SDK and Gradle. Not a hand-packed APK.
set -Eeuo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"
LOG="$ROOT/APK_BUILD_LOG.txt"
exec > >(tee -a "$LOG") 2>&1
fail() { echo; echo "ОШИБКА: $*"; echo "Подробности: $LOG"; exit 1; }
trap 'echo "ОШИБКА при сборке, строка $LINENO. Подробности: $LOG"' ERR
printf '\n======================================\n NEON CASINO ROYALE v1.7.4\n СТАНДАРТНАЯ СБОРКА ANDROID APK\n======================================\n'
if [[ "$(uname -s)" != "Darwin" ]]; then fail "Этот скрипт предназначен для MacBook (macOS)."; fi

# Use Android Studio JBR or an installed JDK 17.
if [[ -z "${JAVA_HOME:-}" ]] && [[ -d '/Applications/Android Studio.app/Contents/jbr/Contents/Home' ]]; then
  export JAVA_HOME='/Applications/Android Studio.app/Contents/jbr/Contents/Home'
fi
if [[ -z "${JAVA_HOME:-}" ]] && /usr/libexec/java_home -v 17 >/dev/null 2>&1; then
  export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
fi
if [[ -z "${JAVA_HOME:-}" ]]; then
  fail "Не найден Java JDK 17. Установи Android Studio и JDK 17, затем повтори."
fi
export PATH="$JAVA_HOME/bin:$PATH"
java -version 2>&1 | head -3

if [[ -z "${ANDROID_HOME:-}" ]] && [[ -n "${ANDROID_SDK_ROOT:-}" ]]; then export ANDROID_HOME="$ANDROID_SDK_ROOT"; fi
if [[ -z "${ANDROID_HOME:-}" ]]; then export ANDROID_HOME="$HOME/Library/Android/sdk"; fi
if [[ ! -d "$ANDROID_HOME" ]]; then
  fail "Android SDK отсутствует: $ANDROID_HOME. Открой Android Studio → Settings → Android SDK и установи SDK Platform 35 и Build Tools 35.0.0."
fi
export ANDROID_SDK_ROOT="$ANDROID_HOME"

find_sdkmanager() {
  local f
  for f in "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" "$ANDROID_HOME/cmdline-tools/bin/sdkmanager"; do
    [[ -x "$f" ]] && { printf '%s' "$f"; return 0; }
  done
  f=$(find "$ANDROID_HOME/cmdline-tools" -maxdepth 3 -name sdkmanager -type f -print -quit 2>/dev/null || true)
  [[ -n "$f" ]] && { printf '%s' "$f"; return 0; }
  return 1
}
SDKMANAGER=$(find_sdkmanager || true)
if [[ ! -f "$ANDROID_HOME/platforms/android-35/android.jar" || ! -x "$ANDROID_HOME/build-tools/35.0.0/apksigner" ]]; then
  if [[ -n "$SDKMANAGER" ]]; then
    echo 'Устанавливаю отсутствующие официальные компоненты Android SDK...'
    "$SDKMANAGER" --sdk_root="$ANDROID_HOME" 'platforms;android-35' 'build-tools;35.0.0' || fail "Невозможно загрузить SDK. В Android Studio установи API 35 и Build Tools 35.0.0."
  else
    fail "Не хватает Android SDK Platform 35 / Build Tools 35.0.0. Установи через Android Studio → SDK Manager."
  fi
fi

# Use installed Gradle or get official Gradle zip. Android Studio may not bundle a CLI gradle.
if command -v gradle >/dev/null 2>&1; then
  GRADLE=$(command -v gradle)
else
  CACHE="$HOME/.gradle/neon-casino-bootstrap"
  GRADLE="$CACHE/gradle-8.11.1/bin/gradle"
  if [[ ! -x "$GRADLE" ]]; then
    mkdir -p "$CACHE"
    echo 'Скачиваю официальный Gradle 8.11.1 для сборки (интернет нужен только при сборке)...'
    curl --retry 3 --fail --location --show-error --output "$CACHE/gradle.zip" 'https://services.gradle.org/distributions/gradle-8.11.1-bin.zip' || fail 'Не удалось скачать Gradle.'
    unzip -q -o "$CACHE/gradle.zip" -d "$CACHE" || fail 'Ошибка распаковки Gradle.'
    rm -f "$CACHE/gradle.zip"
  fi
fi
"$GRADLE" --version | head -18

echo 'Проверяю файлы проекта...'
if command -v python3 >/dev/null 2>&1; then
  python3 tools/check_project.py || fail 'Не прошла проверка структуры Android-проекта.'
  python3 tools/check_mobile.py || fail 'Не прошла проверка встроенной игры.'
fi

echo 'Создаю APK официальными Android Gradle Plugin и SDK...'
"$GRADLE" --no-daemon --console plain :app:assembleDebug || fail 'Android Gradle build завершился с ошибкой.'
APK="$ROOT/app/build/outputs/apk/debug/app-debug.apk"
[[ -s "$APK" ]] || fail "Нет собранного файла $APK"
TOOLS="$ANDROID_HOME/build-tools/35.0.0"
"$TOOLS/zipalign" -c -v 4 "$APK" || fail 'APK не выровнен zipalign.'
"$TOOLS/apksigner" verify --verbose --print-certs "$APK" || fail 'Подпись APK не прошла проверку.'
"$TOOLS/aapt" dump badging "$APK" | grep -E '^(package:|sdkVersion:|targetSdkVersion:|launchable-activity:)' || fail 'Не удалось прочитать AndroidManifest.'
if "$TOOLS/aapt" dump permissions "$APK" | grep -q 'android.permission.INTERNET'; then
  fail 'Неожиданное разрешение INTERNET!'
fi
if ! unzip -Z -1 "$APK" | grep -q '^assets/web/app.js$'; then fail 'В APK нет файлов игры.'; fi
OUTPUT="$ROOT/NEON_CASINO_ROYALE_v1_7_4_QA_ANDROID.apk"
cp "$APK" "$OUTPUT"
shasum -a 256 "$OUTPUT" || true
printf '\n======================================\n ГОТОВО — APK собран и проверен!\n %s\n======================================\n' "$OUTPUT"
open -R "$OUTPUT" || true
