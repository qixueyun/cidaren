"""Replay the three supplied settings screenshots; never invokes desktop controls."""
import json
from pathlib import Path
from PIL import Image
from offline_runner import ROOT,Runner
from card_controls import gear_point,close_point

import tempfile
temp=Path(tempfile.gettempdir())
names=['codex-clipboard-a25139ce-af78-4d00-9402-87c48a9b2ef0.png',
       'codex-clipboard-2f75e793-bfbb-439f-97c8-5db5a084a923.png',
       'codex-clipboard-c48abea2-7f0d-4c31-8479-64fe12eef58a.png']
images=[Image.open(temp/name).convert('RGB') for name in names]
runner=Runner(json.loads((ROOT/'config.json').read_text(encoding='utf-8')))
clicks=[];events=[]
runner.click=clicks.append
runner.record=lambda event,**kw:events.append((event,kw))
for im in images:
    items=runner.read(im)
    assert runner.handle(im,items) is False
assert len(clicks)==3
assert abs(clicks[0][0]-512)<8 and abs(clicks[0][1]-56)<8,clicks[0]
assert clicks[1].text.replace(' ','')=='关闭错题弹出'
assert runner.card_popups_disabled
assert abs(clicks[2][0]-586)<8 and abs(clicks[2][1]-35)<8,clicks[2]
assert events[2][0]=='wrong_card_popups_disabled'
assert all(not hasattr(c,'text') or c.text!='打开错题弹出' for c in clicks)
# A previously disabled popup must not be toggled back on.
runner.card_popups_disabled=False
runner.handle(images[2],runner.read(images[2]))
assert isinstance(clicks[-1],tuple) and runner.card_popups_disabled
# If the toggle closes its menu, re-open the gear to verify its new action label.
runner.card_popups_disabled=False
runner.handle(images[0],runner.read(images[0]))
assert clicks[-1]==gear_point(images[0])
runner.card_setting_attempts=10
try:runner.handle(images[0],runner.read(images[0]))
except RuntimeError as error:assert '设置未能确认' in str(error)
else:raise AssertionError('Missing retry bound')
print('PASS: gear -> disable popups -> confirmed open-action label -> red close; never re-enable; bounded retries')
