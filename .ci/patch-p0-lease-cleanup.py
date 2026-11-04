#!/usr/bin/env python3
"""Fix same-instance stale lock after storage writes fail.

A failed write flips instanceStorageAvailable=false, so old pagehide
guard checking canModify() refuses to clear the stale lease.
Only remove the saved lease if its token equals INSTANCE_TOKEN.
"""
from pathlib import Path
import sys

OLD = """ window.addEventListener('pagehide',()=>{
  if(!canModify())return;
  try{localStorage.removeItem(INSTANCE_KEY)}catch(e){}
 });"""
NEW = """ window.addEventListener('pagehide',()=>{
  // A failed save can mark this page read-only while its own token remains in
  // localStorage. Never clear another tab's lease; compare exact instance tokens.
  try{
   const raw=localStorage.getItem(INSTANCE_KEY);
   if(raw&&JSON.parse(raw)?.token===INSTANCE_TOKEN)localStorage.removeItem(INSTANCE_KEY)
  }catch(e){}
 });"""

def apply(root):
    count=0
    for path in root.rglob('app.js'):
        if path.name!='app.js' or 'node_modules' in path.parts:
            continue
        content=path.read_text(encoding='utf-8')
        if OLD not in content:
            if NEW in content:
                print('Already patched:',path);continue
            raise RuntimeError(f'Expected lease pagehide handler not found: {path}')
        if content.count(OLD)!=1:
            raise RuntimeError(f'Pagehide handler occurrence count unexpected: {path}')
        path.write_text(content.replace(OLD,NEW),encoding='utf-8')
        count+=1
        print('PASS: owner-token-only lease cleanup:',path)
    if count<1:raise RuntimeError('No copies of source JS found under '+str(root))
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: patch-p0-lease-cleanup.py EXTRACTED_ROOT')
    apply(Path(sys.argv[1]))
