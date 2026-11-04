#!/usr/bin/env python3
"""Build exactly one self-contained offline HTML file from existing NEON web assets.
CSP permits the exact hashes of the bundled CSS and JS, not arbitrary scripts.
No game logic, assets or save format is modified.
"""
from pathlib import Path
import re,hashlib,base64,sys

def build(web,output):
    h=(web/"index.html").read_text(encoding="utf-8")
    css=(web/"app.css").read_text(encoding="utf-8")
    js=(web/"app.js").read_text(encoding="utf-8")
    if re.search(r'</script',js,re.I):
        raise SystemExit("Unsupported closing script sequence")
    css_hash=base64.b64encode(hashlib.sha256(("\n"+css+"\n").encode()).digest()).decode()
    js_hash=base64.b64encode(hashlib.sha256(("\n"+js+"\n").encode()).digest()).decode()
    policy=(f"default-src 'none'; script-src 'sha256-{js_hash}'; "
            f"style-src 'sha256-{css_hash}' 'unsafe-inline'; img-src data:; "
            "connect-src 'none'; font-src data:; manifest-src 'none'; "
            "object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'")
    old=re.search(r'<meta http-equiv="Content-Security-Policy" content="[^"]+">',h)
    if not old:raise SystemExit("Original CSP missing")
    h=h[:old.start()]+f'<meta http-equiv="Content-Security-Policy" content="{policy}">'+h[old.end():]
    for name,mime in (("icon.svg","image/svg+xml"),("icon-192.png","image/png")):
        url="data:"+mime+";base64,"+base64.b64encode((web/name).read_bytes()).decode()
        h=h.replace('href="'+name+'"','href="'+url+'"')
    h=h.replace('  <link rel="manifest" href="manifest.webmanifest">\n','')
    old_css='<link rel="stylesheet" href="app.css">'
    old_js='<script src="app.js" defer></script>'
    if h.count(old_css)!=1 or h.count(old_js)!=1:raise SystemExit("Unexpected resource layout")
    h=h.replace(old_css,'<style>\n'+css+'\n</style>')
    h=h.replace(old_js,'<script>\n'+js+'\n</script>')
    if 'script-src \'sha256-' not in h:raise SystemExit("Content policy failed to update")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(h,encoding="utf-8")
    print("PASS: generated single HTML using 8-asset NEON original v1.8.9 source, size",output.stat().st_size)

if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: build-standalone-offline.py SOURCE_WEB_DIR OUTPUT_HTML")
    build(Path(sys.argv[1]),Path(sys.argv[2]))
