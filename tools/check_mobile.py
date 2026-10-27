from pathlib import Path
import hashlib,re,sys
root=Path(__file__).resolve().parents[1]
web=root/'web'; bundled=root/'app/src/main/assets/web'
files=['index.html','app.css','app.js','icon.svg','icon-192.png','icon-512.png','manifest.webmanifest','sw.js']
for name in files:
    assert (web/name).read_bytes()==(bundled/name).read_bytes(),f'Different Android assets: {name}'
manifest=(root/'app/src/main/AndroidManifest.xml').read_text()
assert 'android.permission.INTERNET' not in manifest
assert 'usesCleartextTraffic="false"' in manifest
source=(root/'app/src/main/java/com/neon/play/simulator/MainActivity.java').read_text()
assert 'shouldInterceptRequest' in source
assert 'onRenderProcessGone' in source
assert 'isBundled(Uri uri)' in source
assert 'MAX_BACKUP_CHARS' in source
assert 'backupResult(written)' in source
assert 'onBackPressed()' in source
assert "window.neonNativeBackupComplete" in (web/'app.js').read_text()
assert "window.NEON_INFO.version === '1.7.5'" in source
assert "version:'1.7.5'" in (web/'app.js').read_text()
assert 'android:launchMode="singleTask"' in manifest
assert 'soleNativeActivity' in (web/'app.js').read_text()
assert 'Content-Security-Policy' in (web/'index.html').read_text()
assert "connect-src 'self'" in (web/'index.html').read_text()
assert "frame-src 'none'" in (web/'index.html').read_text()
assert "versionCode 175" in (root/'app/build.gradle').read_text()
print('PASS Android asset integrity, origin isolation, backup callback, error screen, version, no INTERNET permission')
print('JS SHA256:',hashlib.sha256((web/'app.js').read_bytes()).hexdigest())

assert "WEB_READY_v1.7.5_games44" in source
assert "WEB_READY_v1.7.5_games44" in (root/"tests/android_smoke.sh").read_text()
