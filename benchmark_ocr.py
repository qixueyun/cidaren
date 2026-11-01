"""Compare screenshot OCR with and without orientation classification."""
import sys,time,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.deps'))
import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

paths=[ROOT/'runs/20261101-010707/last-screen.png',ROOT/'runs/20261101-122046/last-screen.png']
report={}
for classify in (True,False):
    engine=RapidOCR(use_angle_cls=classify)
    rows=[]
    for path in paths:
        im=np.asarray(Image.open(path).convert('RGB'))
        engine(im)
        samples=[]
        for _ in range(3):
            start=time.perf_counter();result,_=engine(im);samples.append(time.perf_counter()-start)
        rows.append({'file':str(path),'seconds':round(statistics.median(samples),3),'text':[r[1] for r in result or []]})
    report[str(classify)]=rows
    print('ANGLE_CLS',classify,[(r['seconds'],len(r['text'])) for r in rows],flush=True)
report['same_text']=all(a['text']==b['text'] for a,b in zip(report['True'],report['False']))
(ROOT/'runs/ocr-benchmark.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('SAME_TEXT',report['same_text'],flush=True)
