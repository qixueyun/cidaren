"""Manual controls and a Windows single-runner lock."""
import time
from pathlib import Path

class RunLock:
    def __init__(self,path):self.path=Path(path);self.file=None
    def __enter__(self):
        import msvcrt
        self.path.parent.mkdir(exist_ok=True)
        self.file=self.path.open('a+b')
        if self.path.stat().st_size==0:self.file.write(b'0');self.file.flush()
        self.file.seek(0)
        try:msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            self.file.close();self.file=None
            raise RuntimeError('已有学习脚本正在运行，请勿重复启动')
        return self
    def __exit__(self,*args):
        import msvcrt
        if self.file:
            self.file.seek(0);msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
            self.file.close();self.file=None

def active(root):
    try:
        with RunLock(Path(root)/'runs/runner.lock'):return False
    except RuntimeError:return True

def check_controls(root):
    root=Path(root)
    while True:
        if (root/'STOP').exists():raise KeyboardInterrupt('手动停止')
        if not (root/'PAUSE').exists():return
        time.sleep(.2)
