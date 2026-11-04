#!/usr/bin/env python3
"""Inject secret-backed Android release signing into the extracted S5 Gradle app.

Does not alter existing QA/debug signing, users' data, or the source ZIP.
The certificate and passwords are NEVER committed to Git.
"""
from pathlib import Path
import sys

BLOCK = '''
// NEON_SIGNED_RELEASE_BLOCK_V1 — release-only credentials from the environment.
if (System.getenv('NEON_SIGNED_RELEASE') == '1') {
    def keyPath = System.getenv('NEON_RELEASE_KEYSTORE_PATH')
    def password = System.getenv('NEON_RELEASE_PASSWORD')
    if (!keyPath || !password || !file(keyPath).isFile()) {
        throw new GradleException('NEON release signing requires a keystore and password')
    }
    def signer = android.signingConfigs.maybeCreate('neonRealRelease')
    signer.storeFile = file(keyPath)
    signer.storePassword = password
    signer.keyAlias = 'neon_release'
    signer.keyPassword = password
    def releaseVariant = android.buildTypes.getByName('release')
    releaseVariant.signingConfig = signer
    releaseVariant.debuggable = false
}
'''

def inject(path: Path):
    if not path.is_file():
        raise SystemExit('Missing app build.gradle')
    original = path.read_text(encoding='utf-8')
    if 'NEON_SIGNED_RELEASE_BLOCK_V1' in original:
        raise SystemExit('Release block already inserted')
    if 'com.android.application' not in original:
        raise SystemExit('Not an Android application Gradle project')
    path.write_text(original + '\n' + BLOCK, encoding='utf-8')
    print('PASS: enabled release-only signing without embedding secrets')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: configure-android-release-signing.py app/build.gradle')
    inject(Path(sys.argv[1]))
