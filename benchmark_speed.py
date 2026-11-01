"""Local inference timing only; never interacts with the desktop."""
import json,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.deps'))
import numpy as np
from local_solver import LocalSolver
cfg=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
s=LocalSolver(ROOT,cfg)
try:
    s.start()
    s.bank=[];s.corrections=[]
    start=time.perf_counter()
    answer=s.answer('播放','功能 半球 爆发'.split(),'function')
    print('FAST_LLM_SECONDS',round(time.perf_counter()-start,3),'CHOICE',answer+1,flush=True)
    words=json.loads((ROOT/'unit_vocabulary.json').read_text(encoding='utf-8'))
    audio=np.load(ROOT/'runs/20261101-003711/last-audio.npy')
    for n in range(2):
        start=time.perf_counter();heard=s.hear(audio,words)
        print('FAST_ASR_SECONDS',round(time.perf_counter()-start,3),'HEARD',heard,flush=True)
finally:s.close()
