#!/usr/bin/env python3
"""Harden imported JSON text fields against objects with poisoned toString.

Incoming files are untrusted. String({toString:null}) throws and previously
interrupted safeActivity/safeJournal processing during import.
Preserve string/number/boolean legacy metadata while discarding nested objects.
"""
from pathlib import Path
import sys

INSERT="""const safeText=(v,max)=>{
 if(v===null||v===undefined||v===false||v===0)return '';
 return ['string','number','boolean'].includes(typeof v)?String(v).slice(0,max):'';
};
"""
MODS={
 "String(x.game||'').slice(0,35)":"safeText(x.game,35)",
 "String(x.detail||'').slice(0,100)":"safeText(x.detail,100)",
 "String(x.at||'').slice(0,12)":"safeText(x.at,12)",
 "String(x.game||'').slice(0,50)":"safeText(x.game,50)",
 "String(b.value||'').length>110":"((typeof b.value!=='string'&&typeof b.value!=='number')||String(b.value||'').length>110)"
}
MARK="const safeActivity=items=>"

def patch(root):
    count=0
    for p in root.rglob("app.js"):
        if "node_modules" in p.parts:continue
        s=p.read_text(encoding="utf-8")
        if INSERT in s:
            print("Already patched:",p)
            continue
        if MARK not in s:raise RuntimeError(f"Expected sanitizer absent: {p}")
        for old,new in MODS.items():
            occur=s.count(old)
            if old=="String(x.detail||'').slice(0,100)":
                assert occur==2,(p,old,occur)
            else:
                assert occur==1,(p,old,occur)
            s=s.replace(old,new)
        s=s.replace(MARK,INSERT+MARK,1)
        p.write_text(s,encoding="utf-8")
        count+=1
        print("PASS: importer string coercion guarded:",p)
    if count<1:raise RuntimeError("No app.js extracted")
if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("usage: patch-p0-import-text.py EXTRACTED_PROJECT_ROOT")
    patch(Path(sys.argv[1]))
