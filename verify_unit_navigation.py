"""Replay user task screenshots without UI actions or changes to answer records."""
import json
from pathlib import Path
from types import SimpleNamespace
from PIL import Image,ImageDraw
from offline_runner import Runner,ROOT
from offline_core import page_kind,word_items,Text
from unit_navigation import all_badges_ten,task_rows

import tempfile
temp=Path(tempfile.gettempdir())
names=['215a2a0b-1000-4479-9004-846a297ea879','79ee1fc1-8e64-46da-9eb7-1b3e62fdb745',
       'f81532fb-c85a-4e3d-9185-e6cc68a13c71','efc9c01f-4370-4eca-bbc9-5c433821062c',
       '83a3a33f-64fe-4f4d-920a-69eb8015b6ca']
images=[Image.open(temp/f'codex-clipboard-{name}.png').convert('RGB') for name in names]
runner=Runner(json.loads((ROOT/'config.json').read_text(encoding='utf-8')))
items=[runner.read(im) for im in images]
assert [page_kind(row) for row in items]==['select','unit','task_list','unit','unit']
labels=word_items(items[0],images[0].height)
assert len(labels)==30,len(labels)
assert all_badges_ten(images[0],labels,30),'Failed completed badges'
incomplete=Image.open(ROOT/'runs/20261101-122046/last-screen.png')
other=runner.read(incomplete)
assert not all_badges_ten(incomplete,word_items(other,incomplete.height),30)
rows=task_rows(items[2])
assert len(rows)>=6,[(t.text,s) for t,s in rows]
assert next(s for t,s in rows if '28' in t.text)==100
clicks=[];events=[]
runner.click=lambda point,*a,**kw:clicks.append(point)
runner.record=lambda event,**kw:events.append(event)
runner.checkpoint=ROOT/'runs/navigation-test-checkpoint.json'
back=Text('返回',1,[[0,0],[30,0],[30,20],[0,20]])
runner.handle(images[0],items[0]+[back])
assert '返回' in clicks[-1].text
runner.handle(images[1],items[1])
assert '返回' in clicks[-1].text
runner.handle(images[2],items[2])
assert '30' in clicks[-1].text and not runner.leaving_completed_unit
runner.handle(images[3],items[3])
assert clicks[-1].text=='开始选词'
runner.handle(images[4],items[4])
assert clicks[-1].text=='重新选词'
# Same observed 30 word labels, six chunks, no per-word OCR.
runner.uia=True;runner.total=30
runner.guard=lambda:None
runner.capture=lambda:incomplete
batches=[]
runner.bg=SimpleNamespace(click_many=lambda points:batches.append(points))
runner.handle(incomplete,other)
assert len(batches)==6 and sum(map(len,batches))==30,[len(b) for b in batches]
painted=incomplete.convert('RGB').copy()
draw=ImageDraw.Draw(painted)
already=word_items(other,incomplete.height)[:5]
for word in already:
    xs=[p[0] for p in word.box];ys=[p[1] for p in word.box]
    draw.rectangle((min(xs),min(ys),max(xs),max(ys)),fill=(0,190,100))
runner.capture=lambda:painted
batches.clear()
runner.handle(painted,other)
assert sum(map(len,batches))==25
assert not any(word.center in batch for word in already for batch in batches)
print('PASS: 30 completed badges -> back twice -> unfinished List30; both entries; six batches; five already-green words skipped')
