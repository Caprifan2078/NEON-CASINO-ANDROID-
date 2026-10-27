from pathlib import Path
import xml.etree.ElementTree as ET
import re, hashlib
root=Path(__file__).resolve().parent.parent
manifest=ET.parse(root/'app/src/main/AndroidManifest.xml').getroot()
main=(root/'app/src/main/java/com/neon/play/simulator/MainActivity.java').read_text()
assert manifest.tag=='manifest'
assert len(manifest.findall('uses-permission'))==0,'Unexpected Android permissions'
assert 'shouldInterceptRequest' in main and 'setDomStorageEnabled(true)' in main
assert (root/'app/src/main/assets/web/index.html').is_file()
js=(root/'app/src/main/assets/web/app.js').read_bytes()
assert len(js)>100000,'Game logic missing'
assert hashlib.sha256(js).digest()==hashlib.sha256((root/'web/app.js').read_bytes()).digest()
assert '.qa' in (root/'app/build.gradle').read_text()
print('PASS: Android source, game assets, offline manifest, distinct QA applicationId')
