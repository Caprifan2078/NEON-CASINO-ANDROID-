#!/usr/bin/env python3
"""Supply required iOS bundle metadata missing from the S5 archived Info.plist."""
from pathlib import Path
import plistlib

p = Path("s5platform/ios/NEONROYALE/Info.plist")
assert p.is_file(), "S5 iOS Info.plist not found"
data = plistlib.loads(p.read_bytes())
assert data["CFBundleShortVersionString"] == "1.8.9"
assert str(data["CFBundleVersion"]) == "190"
required = {
    "CFBundleIdentifier": "com.neon.royale.ios",
    "CFBundleExecutable": "NEONROYALE",
    "CFBundlePackageType": "APPL",
    "CFBundleName": "NEONROYALE",
}
for key, value in required.items():
    if key in data and data[key] != value:
        raise SystemExit(f"Conflicting {key}: {data[key]}")
    data[key] = value
p.write_bytes(plistlib.dumps(data, sort_keys=False))
for key, expected in required.items():
    assert plistlib.loads(p.read_bytes())[key] == expected
print("PASS: iOS bundle identifier, executable, package type, name present")
