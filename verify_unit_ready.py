"""Replay actual unit-loading failure and delayed-button states, without UI actions."""
import json,time
from unittest.mock import patch
from PIL import Image
from offline_runner import ROOT,Runner
from offline_core import loading_overlay,Text

im=Image.open(ROOT/'runs/20261101-130141/last-screen.png')
assert loading_overlay(im),'Actual narrow loading arc was missed'
runner=Runner(json.loads((ROOT/'config.json').read_text(encoding='utf-8')))
runner.checkpoint=ROOT/'runs/unit-ready-test-checkpoint.json'
calls=[];events=[]
runner.click=calls.append
runner.record=lambda event,**kw:events.append(event)
with patch('offline_runner.time.sleep'):
    assert runner.handle(im,[]) is False
assert not calls and events==['waiting_for_loading']
blank=Image.new('RGB',(674,1518),'white')
def text(value):return Text(value,1,[[10,10],[150,10],[150,30],[10,30]])
zero=[text('单词总数：0'),text('单元得分：0')]
assert runner.handle(blank,zero) is False
assert runner.total is None and not calls
ready=[text('单词总数：30'),text('单元得分：0')]
assert runner.handle(blank,ready) is False
assert runner.last_score is None and runner.stagnant==0
runner.handle(blank,ready+[text('重新选词')])
assert calls[-1].text=='重新选词' and runner.total==30 and runner.unit_ready_since is None
runner.handle(blank,ready+[text('开始选词')])
assert calls[-1].text=='开始选词'
runner.unit_ready_since=time.monotonic()-46
try:runner.handle(blank,ready)
except RuntimeError as error:assert '45秒' in str(error)
else:raise AssertionError('Unit-ready wait must be bounded')
print('PASS: actual loading arc; zero total and delayed button wait without clicks; both entry buttons; 45-second bound')
