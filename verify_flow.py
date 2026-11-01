"""Offline regression checks for pages that actually interrupted the live run."""
import json
from pathlib import Path
from offline_runner import Runner, ROOT
from offline_core import page_kind
from PIL import Image
from types import SimpleNamespace

runner = Runner(json.loads((ROOT / 'config.json').read_text(encoding='utf-8')))
runner.last_submission=None
runner.memory.data={'questions':{},'active':None}
runner.solver=SimpleNamespace(learn_feedback=lambda *args:None)
familiar = ROOT / 'runs/20261031-224459/last-screen.png'
if familiar.exists():
    im = Image.open(familiar).convert('RGB')
    items = runner.read(im)
    assert page_kind(items) == 'familiar'
    assert runner.find(items, '继续') is not None
feedback = ROOT / 'runs/20261031-225120/last-screen.png'
if feedback.exists():
    im = Image.open(feedback).convert('RGB')
    items = runner.read(im)
    calls = []
    runner.click = calls.append
    # Feedback may learn locally, but must not request model inference.
    assert runner.handle(im, items) is False
    assert not calls or all(t.text == '继续' for t in calls)
print('PASS: white-on-green Continue recognition and feedback page precedence')
