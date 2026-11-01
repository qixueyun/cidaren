"""Window capture plus UIA Invoke; may activate WeChat, never moves the mouse."""
from pathlib import Path
import subprocess
import time
from background_window import BackgroundWindow

ROOT=Path(__file__).resolve().parent

class UIATargetUnavailable(RuntimeError):
    """The helper found no target and did not invoke any action."""
    pass

class UIABatchPartial(RuntimeError):
    """Some word toggles may have run; only a new screenshot can resolve them."""
    pass

class UIAWindow(BackgroundWindow):
    def __init__(self,hwnd):
        super().__init__(hwnd)
        self.helper=ROOT/'runs/uia_invoke.exe'
        bundled=ROOT/'assets/uia_invoke.exe'
        if bundled.exists():
            self.helper=bundled
            return
        source=ROOT/'uia_invoke.cs'
        if not self.helper.exists() or self.helper.stat().st_mtime<source.stat().st_mtime:
            framework=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319')
            command=[str(framework/'csc.exe'),'/nologo','/out:'+str(self.helper)]
            command+=['/reference:'+str(framework/'WPF'/name) for name in
                      ('UIAutomationClient.dll','UIAutomationTypes.dll','WindowsBase.dll')]
            command.append(str(source))
            subprocess.run(command,check=True,capture_output=True,timeout=30,
                           creationflags=subprocess.CREATE_NO_WINDOW)

    def invoke(self,*arguments):
        self.guard()
        result=subprocess.run([str(self.helper),str(self.hwnd),*map(str,arguments)],
                              capture_output=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            error=result.stderr.decode(errors='replace')
            if 'Batch partially applied' in error:
                raise UIABatchPartial('批量选词部分完成，需要重新检查绿色状态：'+error)
            if error.strip()=='No invokable element at observed point':
                raise UIATargetUnavailable('UIA直接调用失败：'+error)
            raise RuntimeError('UIA直接调用失败：'+error)
        time.sleep(.05)
        return result.stdout.decode(errors='replace').strip()

    def click(self,x,y):
        if self.size is None:raise RuntimeError('UIA调用前必须先截图')
        return self.invoke('point',x,y)

    def click_many(self,points):
        if not 1<=len(points)<=5:raise ValueError('选词批次应为1至5个')
        return self.invoke('points',*(coordinate for point in points for coordinate in point))
