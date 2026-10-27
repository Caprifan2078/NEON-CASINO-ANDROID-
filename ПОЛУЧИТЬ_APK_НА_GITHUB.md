# NEON CASINO ROYALE — собрать APK в GitHub Actions

В проект уже добавлен сценарий `.github/workflows/build-android.yml`.

1. Создай **пустой** репозиторий `NEON-CASINO-ANDROID` на github.com/new (можно Private).
2. Распакуй архив и загрузи **все файлы и папки** проекта в корень репозитория, включая скрытую `.github`. Не загружай только ZIP одним файлом.
3. Открой вкладку **Actions** → **NEON ROYALE — Build and install-test Android APK**. Если сборка не запустилась сама, нажми **Run workflow**.
4. После успешного запуска открой workflow run → **Artifacts** → `NEON-ROYALE-v1.7.4-ANDROID-TESTED-APK`. Скачай ZIP, внутри будет `app-debug.apk`.

APK содержит 44 игры и полностью виртуальные фишки. Debug ID — `com.neon.play.simulator.qa` для установки рядом со старой версией без перезаписи её сохранений. Прогресс старой версии НЕ переносится автоматически. Сценарий обязательно проверяет установку и запуск игры в Android-эмуляторе, а затем публикует APK. Его успешность пока не подтверждена реальным запуском CI.
