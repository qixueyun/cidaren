"""Actual GUI callbacks, runner, model and stop; never touches WeChat."""
import time
import tkinter as tk
from launcher import Launcher
from runtime_control import active
from pathlib import Path
root=Path(__file__).resolve().parent
assert not active(root),'An existing learning process must finish first'
window=tk.Tk();window.withdraw();ui=Launcher(window);ui.runner_args=['--startup-check']
def wait_until(condition,timeout):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        window.update()
        if condition():return
        time.sleep(.05)
    raise AssertionError(ui.status.get()+'\n'+ui.output.get('1.0','end'))
try:
    ui.start();time.sleep(.15)
    ui.pause();assert (root/'PAUSE').exists()
    start=time.monotonic();ui.stop()
    wait_until(lambda:ui.process is None,15)
    assert not active(root)
    print('PASS startup cancellation:',round(time.monotonic()-start,2),'seconds',flush=True)
    ui.start()
    wait_until(lambda:'模型已就绪' in ui.status.get(),60)
    ui.pause();assert (root/'PAUSE').exists()
    ui.resume();assert not (root/'PAUSE').exists()
    start=time.monotonic();ui.stop()
    wait_until(lambda:ui.process is None,15)
    assert not active(root)
    print('PASS real model start/pause/resume/stop:',round(time.monotonic()-start,2),'seconds',flush=True)
finally:
    if ui.process is not None and ui.process.poll() is None:
        ui.job.terminate();ui.process.wait(timeout=5)
    if ui.job:ui.job.close()
    window.destroy()
