"""Regression test using the user's screenshot. Never operates the desktop."""
import json
from pathlib import Path
import sys
from offline_runner import ROOT, Runner
from offline_core import page_kind
from PIL import Image

path = Path(sys.argv[1])
runner = Runner(json.loads((ROOT / 'config.json').read_text(encoding='utf-8')))
im = Image.open(path).convert('RGB')
items = runner.read(im)
assert page_kind(items) == 'checkin_notice'
clicks = []
runner.click = clicks.append
assert runner.handle(im, items) is False
assert len(clicks) == 1 and clicks[0].text == '我知道了'
assert clicks[0].center[1] > im.height * .5
runner.handle(im, items)
runner.handle(im, items)
try:
    runner.handle(im, items)
except RuntimeError as error:
    assert '3次' in str(error)
else:
    raise AssertionError('Retry limit was not enforced')
assert len(clicks) == 3
print('PASS: check-in overlay takes precedence, correct button, bounded retry; no desktop clicks')
