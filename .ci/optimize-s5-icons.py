#!/usr/bin/env python3
"""Loss-minimized Android game icon optimization; fail if visual quality decreases."""
from pathlib import Path
from PIL import Image
import sys, math, shutil

def main(root):
    web=root/'web'
    originals={}
    for size in (192,512):
        name=f'icon-{size}.png'
        p=web/name
        assert p.exists(), f'Missing {p}'
        img=Image.open(p).convert('RGB')
        assert img.size==(size,size)
        before=p.stat().st_size
        originals[name]=p.read_bytes()
        temp=p.with_suffix('.optimized.png')
        img.quantize(colors=256,method=Image.Quantize.FASTOCTREE,dither=Image.Dither.NONE).save(temp,optimize=True)
        after=Image.open(temp).convert('RGB')
        a,b=img.tobytes(),after.tobytes()
        total_error=sum((x-y)**2 for x,y in zip(a,b))
        psnr=10*math.log10(255**2/(total_error/len(a))) if total_error else float('inf')
        maximum=max(abs(x-y) for x,y in zip(a,b))
        if psnr<38.5 or maximum>16 or temp.stat().st_size>=before*.45:
            temp.unlink(missing_ok=True)
            raise RuntimeError(f'Icon optimization not safe: {name}, PSNR {psnr:.2f}, worst difference {maximum}')
        temp.replace(p)
        print(f'PASS {name}: {before} -> {p.stat().st_size} bytes, PSNR={psnr:.2f} dB, max diff {maximum}')
    original192=originals['icon-192.png']
    for p in (root/'app/src/main/res').glob('**/neon_icon.png'):
        if p.read_bytes()!=original192:
            raise RuntimeError(f'Unknown launcher icon: {p}; refusing silent replacement')
        shutil.copyfile(web/'icon-192.png',p)
        print('PASS matching launcher drawable:',p)
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: optimize-s5-icons.py SOURCE_ROOT')
    main(Path(sys.argv[1]))
