"""Experimental window-only capture/input. Never activates or moves the cursor."""
import ctypes as C
from ctypes import wintypes as W
import queue
import threading
from PIL import Image

u=C.WinDLL('user32',use_last_error=True)
g=C.WinDLL('gdi32',use_last_error=True)
for dll,name,args,result in [
    (u,'GetWindowDC',[W.HWND],W.HDC),
    (u,'ReleaseDC',[W.HWND,W.HDC],C.c_int),
    (u,'PrintWindow',[W.HWND,W.HDC,W.UINT],W.BOOL),
    (g,'CreateCompatibleDC',[W.HDC],W.HDC),
    (g,'CreateCompatibleBitmap',[W.HDC,C.c_int,C.c_int],W.HBITMAP),
    (g,'SelectObject',[W.HDC,W.HANDLE],W.HANDLE),
    (g,'DeleteObject',[W.HANDLE],W.BOOL),
    (g,'DeleteDC',[W.HDC],W.BOOL),
    (u,'ChildWindowFromPointEx',[W.HWND,W.POINT,W.UINT],W.HWND),
    (u,'PostMessageW',[W.HWND,W.UINT,W.WPARAM,W.LPARAM],W.BOOL),
    (u,'GetWindowRect',[W.HWND,C.POINTER(W.RECT)],W.BOOL),
    (u,'ScreenToClient',[W.HWND,C.POINTER(W.POINT)],W.BOOL),
    (u,'MapWindowPoints',[W.HWND,W.HWND,C.POINTER(W.POINT),W.UINT],C.c_int),
    (u,'IsWindow',[W.HWND],W.BOOL),
    (u,'IsIconic',[W.HWND],W.BOOL),
    (u,'GetForegroundWindow',[],W.HWND),
    (u,'GetCursorPos',[C.POINTER(W.POINT)],W.BOOL),
]:
    fn=getattr(dll,name);fn.argtypes=args;fn.restype=result

class Header(C.Structure):
    _fields_=[('size',W.DWORD),('width',W.LONG),('height',W.LONG),
              ('planes',W.WORD),('bits',W.WORD),('compression',W.DWORD),
              ('image_size',W.DWORD),('xppm',W.LONG),('yppm',W.LONG),
              ('used',W.DWORD),('important',W.DWORD)]
g.GetDIBits.argtypes=[W.HDC,W.HBITMAP,W.UINT,W.UINT,C.c_void_p,C.c_void_p,W.UINT]
g.GetDIBits.restype=C.c_int

class BackgroundWindow:
    def __init__(self,hwnd):self.hwnd=hwnd;self.size=None

    def guard(self):
        if not u.IsWindow(self.hwnd):raise RuntimeError('小程序窗口已关闭')
        if u.IsIconic(self.hwnd):raise RuntimeError('后台模式请勿最小化小程序，可被其他窗口遮挡')

    def _capture(self):
        self.guard()
        rect=W.RECT();u.GetWindowRect(self.hwnd,C.byref(rect))
        w,h=rect.right-rect.left,rect.bottom-rect.top
        dc=u.GetWindowDC(self.hwnd);mem=g.CreateCompatibleDC(dc)
        bitmap=g.CreateCompatibleBitmap(dc,w,h);old=g.SelectObject(mem,bitmap)
        try:
            if not u.PrintWindow(self.hwnd,mem,2):raise RuntimeError('后台窗口截图失败')
            g.SelectObject(mem,old)
            header=Header();header.size=C.sizeof(Header);header.width=w;header.height=-h
            header.planes=1;header.bits=32
            data=C.create_string_buffer(w*h*4)
            if g.GetDIBits(mem,bitmap,0,h,data,C.byref(header),0)!=h:
                raise RuntimeError('后台截图像素读取失败')
            im=Image.frombytes('RGB',(w,h),data.raw,'raw','BGRX')
            import numpy as np
            pixels=np.asarray(im)
            if float(pixels.std())<3:raise RuntimeError('后台截图为空白；不会回退到前台抢占鼠标')
            self.size=(w,h)
            return im
        finally:
            g.SelectObject(mem,old);g.DeleteObject(bitmap);g.DeleteDC(mem);u.ReleaseDC(self.hwnd,dc)

    def capture(self):
        result=queue.Queue()
        def work():
            try:result.put(self._capture())
            except Exception as error:result.put(error)
        threading.Thread(target=work,daemon=True).start()
        try:value=result.get(timeout=5)
        except queue.Empty:raise RuntimeError('后台截图超时，停止操作')
        if isinstance(value,Exception):raise value
        return value

    def click(self,x,y):
        self.guard()
        rect=W.RECT();u.GetWindowRect(self.hwnd,C.byref(rect))
        if self.size!=(rect.right-rect.left,rect.bottom-rect.top):
            raise RuntimeError('窗口大小变化，请重新截图')
        point=W.POINT(rect.left+round(x),rect.top+round(y))
        u.ScreenToClient(self.hwnd,C.byref(point))
        hwnd=self.hwnd
        # WeChat exposes an "Intermediate D3D Window" used only for drawing.
        # Its top-level host, rather than that rendering surface, receives input.
        packed=(point.x&0xffff)|((point.y&0xffff)<<16)
        for message,buttons in [(0x200,0),(0x201,1),(0x202,0)]:
            if not u.PostMessageW(hwnd,message,buttons,packed):
                raise RuntimeError('后台点击消息发送失败；未回退到前台点击')
