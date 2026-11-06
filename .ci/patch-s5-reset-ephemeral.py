#!/usr/bin/env python3
"""Reset ALL transient table states when changing wallets, without touching saved data.

Bug: the existing resetRuntime() cleared early games but not 26 later additions.
After cancelling a wager and changing mode, a stale rt.letitride/threecard/etc.
remained active despite state.reserved=0 and could block play or throw on payout.
Patch only the extracted, already verified 1.8.9 source. No change to save schema.
"""
from pathlib import Path
import sys

OLD = (
    "function resetRuntime(){lastRouletteBets=[];roundEpoch++;"
    "if(rt.crash?.interval)clearInterval(rt.crash.interval);"
    "if(rt.plinko?.timer)clearInterval(rt.plinko.timer);"
    "Object.assign(rt,{"
)
NEW = OLD.replace(
    "Object.assign(rt,{",
    # Preserve existing abort epoch and explicit timer cleanup, then drop every
    # transient table key (including games added in future versions).
    "for(const key of Object.keys(rt))delete rt[key];Object.assign(rt,{"
)

def apply(folder):
    root=Path(folder)
    patched=[]
    for path in sorted(root.rglob("app.js")):
        source=path.read_text(encoding="utf-8")
        if "function resetRuntime()" not in source:
            continue
        if NEW in source:
            print("ALREADY PATCHED",path)
            continue
        if source.count(OLD) != 1:
            raise RuntimeError(f"resetRuntime source differs from known baseline: {path}")
        path.write_text(source.replace(OLD,NEW),encoding="utf-8")
        patched.append(path)
        print("PATCHED",path)
    if not patched:
        raise RuntimeError("No unpatched NEON 1.8.9 app.js found in extracted snapshot")
    print("PASS: patched",len(patched),"transient runtime reset implementations")

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("Usage: patch-s5-reset-ephemeral.py EXTRACTED_PROJECT_ROOT")
    apply(sys.argv[1])
