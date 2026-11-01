"""Background-only message experiments against the observed blank menu overlay."""
import sys,json,time,ctypes as C
from ctypes import wintypes as W
from offline_runner import Runner,ROOT
from background_window import u
cfg=json.loads((ROOT/'config.json').read_text(encoding='utf-8'));cfg['background']=True
r=Runner(cfg);r.select_window();before=r.capture()
assert 675<=before.width<=690 and 1340<=before.height<=1360,before.size
# Fresh image must show the overlay before touching this blank area.
items=r.read(before)
assert any('查看单词用法' in t.text for t in items),'Menu overlay is not present'
mode=sys.argv[1]
hwnd=r.window._hWnd
rect=W.RECT();u.GetWindowRect(hwnd,C.byref(rect))
point=W.POINT(rect.left+350,rect.top+850);u.ScreenToClient(hwnd,C.byref(point))
if mode=='child-sync':
 child=u.ChildWindowFromPointEx(hwnd,point,7)
 if child and child!=hwnd:u.MapWindowPoints(hwnd,child,C.byref(point),1);hwnd=child
u.SendMessageTimeoutW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM,W.UINT,W.UINT,C.POINTER(C.c_size_t)]
u.SendMessageTimeoutW.restype=C.c_size_t
def send(msg,wp,lp):
 result=C.c_size_t()
 if not u.SendMessageTimeoutW(hwnd,msg,wp,lp,2,1500,C.byref(result)):raise RuntimeError('Message timeout')
foreground=u.GetForegroundWindow();cursor=W.POINT();u.GetCursorPos(C.byref(cursor))
packed=(point.x&0xffff)|((point.y&0xffff)<<16)
try:
 if mode=='activation-sync':
  send(0x86,1,0);send(0x6,1,0);send(0x7,0,0)
 send(0x200,0,packed);send(0x201,1,packed);time.sleep(.08);send(0x202,0,packed)
finally:
 if mode=='activation-sync':
  send(0x8,0,0);send(0x6,0,0);send(0x86,0,0)
time.sleep(.3)
after=r.capture();after.save(r.run_dir/('message-'+mode+'.png'))
now=W.POINT();u.GetCursorPos(C.byref(now))
print(json.dumps({'mode':mode,'foreground_unchanged':foreground==u.GetForegroundWindow(),
 'cursor_unchanged':(cursor.x,cursor.y)==(now.x,now.y),'image':str(r.run_dir/('message-'+mode+'.png'))}))
