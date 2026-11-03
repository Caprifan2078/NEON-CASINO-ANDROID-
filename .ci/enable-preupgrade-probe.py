from pathlib import Path
f=Path("s5src/tests/android_smoke.sh")
s=f.read_text()
before="run_test stagePersistentWalletCheckpoint\n"
after=before+"run_test verifyCheckpointBeforeUpgrade\n"
if s.count(before)!=1: raise SystemExit("unexpected smoke script")
f.write_text(s.replace(before,after))
print("Pre-upgrade checkpoint test inserted")
