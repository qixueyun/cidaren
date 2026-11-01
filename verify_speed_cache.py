"""Check exact-frame OCR caching and benchmark repeated screenshots offline."""
import json,time
from unittest.mock import patch
from PIL import Image
from offline_runner import Runner,ROOT

runner=Runner(json.loads((ROOT/'config.json').read_text(encoding='utf-8')))
image=Image.open(ROOT/'runs/20261101-010707/last-screen.png').convert('RGB')
original=runner.ocr
calls=[]
def counted(pixels):
    calls.append(1)
    return original(pixels)
runner.ocr=counted
start=time.perf_counter();first=runner.read(image);initial=time.perf_counter()-start
count=len(calls)
assert count>0
start=time.perf_counter();again=runner.read(image.copy());cached=time.perf_counter()-start
assert len(calls)==count
assert [(t.text,t.box) for t in first]==[(t.text,t.box) for t in again]
again.clear()
assert runner.read(image), 'Caller modified stored cache'
changed=image.copy()
pixel=changed.getpixel((0,0));changed.putpixel((0,0),((pixel[0]+1)%256,pixel[1],pixel[2]))
runner.read(changed)
assert len(calls)>count,'Even a one-pixel change must re-run OCR'
count=len(calls)
loading=Image.open(ROOT/'runs/20261101-122105/last-screen.png')
assert runner.read(loading)==[] and len(calls)==count
report={'first_read_seconds':round(initial,4),'cached_read_seconds':round(cached,4)}
(ROOT/'runs/ocr-cache-benchmark.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PASS: exact-frame cache, pixel-change invalidation, independent item list, loading skips OCR',report)
