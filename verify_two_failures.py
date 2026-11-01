"""Read the user's actual card and starred-feedback screenshots; no desktop input."""
import json
from pathlib import Path
from offline_runner import ROOT,Runner
from offline_core import page_kind
from feedback_vision import feedback_markers

from PIL import Image
root=Path.home()/'Pictures/Screenshots'
card=Image.open(root/'屏幕截图 2026-10-31 231638.png').convert('RGB')
feedback=Image.open(root/'屏幕截图 2026-10-31 231643.png').convert('RGB')
runner=Runner(json.loads((ROOT/'config.json').read_text(encoding='utf-8')))
card_items=runner.read(card)
assert page_kind(card_items)=='failure_card',[(t.text,t.score) for t in card_items]
clicks=[]
runner.click=clicks.append
runner.handle(card,card_items)
assert len(clicks)==1 and isinstance(clicks[0],tuple)
assert clicks[0][0]>card.width*.7 and clicks[0][1]<card.height*.15
markers=feedback_markers(feedback)
assert markers is not None
assert markers['correct']==[0],markers
assert markers['wrong']==[3],markers
class Recorder:
    def __init__(self):self.answers=[]
    def learn_feedback(self,sentence,meaning):self.answers.append((sentence,meaning))
runner.solver=Recorder()
runner.last_submission=None
runner.memory.data={'active':None,'questions':{}}
items=runner.read(feedback)
runner.learn_feedback(feedback,items)
assert len(runner.solver.answers)==1
sentence,meaning=runner.solver.answers[0]
assert 'overlap' in sentence and 'n.' in meaning and '叠' in meaning,(sentence,meaning)
assert len(clicks)==1 # Feedback harvesting must not click another answer.
print('PASS: failed-twice card -> settings gear; green star=option 1; red wrong=option 4; correct noun sense recorded without desktop clicks')
