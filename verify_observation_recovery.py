"""Regression for misclassified loading vocabulary card and safe observation retry."""
import json
import itertools
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
from offline_runner import ROOT,Runner,RetryObservation
from offline_core import page_kind,Text

config=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
runner=Runner(config)
im=Image.open(ROOT/'runs/20261101-130330/last-screen.png')
items=runner.read(im)
assert page_kind(items) in ('loading','familiar'),[(t.text,t.score) for t in items]
clicks=[];events=[]
runner.click=clicks.append
runner.record=lambda event,**kw:events.append(event)
with patch('offline_runner.time.sleep'):
    assert runner.handle(im,items) is False
assert not clicks
# Even when OCR misses loading text, four definitions must stay a vocabulary card.
without_loading=[t for t in items if '加载' not in t.text and '继续' not in t.text]
assert page_kind(without_loading)=='familiar'
assert runner.handle(im,without_loading) is False and not clicks
continue_button=Text('继续',1,[[400,1200],[550,1200],[550,1250],[400,1250]])
runner.handle(im,without_loading+[continue_button])
assert clicks==[continue_button]
# Model and capture are stubbed: retry never starts inference or submits answers.
runner.select_window=lambda:None
runner.capture=lambda:Image.new('RGB',(674,1332),'white')
runner.read=lambda image:[]
count=[]
def handle(image,items):
    count.append(1)
    if len(count)==1:raise RetryObservation('模拟一次临时识别失败')
    return True
runner.handle=handle
model=SimpleNamespace(start=lambda:None,close=lambda:None)
with patch('local_solver.LocalSolver',return_value=model),patch('offline_runner.time.sleep'):
    runner.run()
assert len(count)==2 and 'retry_observation' in events
assert clicks==[continue_button]
runner.handle=lambda *args:(_ for _ in ()).throw(RetryObservation('持续模拟识别失败'))
with patch('local_solver.LocalSolver',return_value=model),patch('offline_runner.time.sleep'),patch('offline_runner.time.monotonic',side_effect=itertools.count(0,46)):
    try:runner.run()
    except RuntimeError as error:assert '45秒' in str(error)
    else:raise AssertionError('Recovery retries must remain bounded')
print('PASS: actual loading vocabulary card never answered; missing loading text waits for Continue; transient observation retries without submission')
