"""One reversible menu click; never submits an answer or activates the target."""
import json
import time
import ctypes as C
from ctypes import wintypes as W
from offline_runner import Runner,ROOT
from background_window import u
cfg=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
cfg['background']=True
r=Runner(cfg);r.select_window()
before=r.capture()
foreground=u.GetForegroundWindow()
cursor=W.POINT();u.GetCursorPos(C.byref(cursor))
# This exact menu position was observed in the successful background capture.
assert abs(before.width-681)<=2 and abs(before.height-1350)<=2,before.size
r.click((626,110))
time.sleep(.5)
after=r.capture();after.save(r.run_dir/'menu-after.png')
now=W.POINT();u.GetCursorPos(C.byref(now))
print(json.dumps({'foreground_unchanged':foreground==u.GetForegroundWindow(),
                  'cursor_unchanged':(cursor.x,cursor.y)==(now.x,now.y),
                  'image':str(r.run_dir/'menu-after.png')}))
