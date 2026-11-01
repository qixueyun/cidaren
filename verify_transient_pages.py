"""Replay captured loading failures without desktop actions or model calls."""
from pathlib import Path
from unittest.mock import patch
import subprocess
from PIL import Image
from offline_runner import Runner, ROOT
from offline_core import loading_overlay
from uia_window import UIAWindow, UIATargetUnavailable
from offline_core import Text
from types import SimpleNamespace

loading = Image.open(ROOT/'runs/20261101-122105/last-screen.png')
assert loading_overlay(loading), 'Missed actual loading spinner'
assert not loading_overlay(Image.new('RGB',loading.size,'white'))
normal=Image.open(ROOT/'runs/20261101-010707/last-screen.png')
assert not loading_overlay(normal), 'Normal question mistaken for loading'

runner=object.__new__(Runner)
runner.loading_since=None
events=[]
runner.record=lambda *a,**kw: events.append((a,kw))
runner.click=lambda *a,**kw: (_ for _ in ()).throw(AssertionError('Clicked loading page'))
with patch('offline_runner.time.sleep'):
    assert runner.handle(loading,[]) is False
assert events[0][0]==('waiting_for_loading',)
runner.loading_since=0
try:
    runner.handle(loading,[])
except RuntimeError as error:
    assert '120秒' in str(error)
else:
    raise AssertionError('Unbounded loading wait')

window=object.__new__(UIAWindow)
window.guard=lambda:None
window.helper=Path('unused.exe');window.hwnd=1
with patch('uia_window.subprocess.run',return_value=subprocess.CompletedProcess([],1,b'',b'No invokable element at observed point')):
    try:window.invoke('point',1,1)
    except UIATargetUnavailable:pass
    else:raise AssertionError('Missing target was not classified')
runner=object.__new__(Runner)
runner.guard=lambda:None
runner.uia=True;runner.background=True
runner.window=SimpleNamespace(width=674,height=1518)
calls=[]
def missing(*args):raise UIATargetUnavailable('No invokable element at observed point')
runner.bg=SimpleNamespace(click=missing,invoke=lambda name:calls.append(name))
runner.click(Text('construction',1,[[50,330],[210,330],[210,380],[50,380]]),settle=False)
assert calls==['construction']
runner.bg.click=lambda *args:(_ for _ in ()).throw(RuntimeError('ambiguous invocation failure'))
try:runner.click(Text('construction',1,[[50,330],[210,330],[210,380],[50,380]]),settle=False)
except RuntimeError:pass
else:raise AssertionError('Uncertain invocation was retried')
assert calls==['construction']
print('PASS: spinner wait/timeout, normal page, no-action UIA text fallback, uncertain actions never retried')
