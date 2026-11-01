import io
from pathlib import Path
import tempfile
import tkinter as tk
from unittest.mock import patch
import launcher
from runtime_control import RunLock,check_controls

workspace_runs=(launcher.ROOT/'runs').resolve()
with tempfile.TemporaryDirectory(dir=workspace_runs) as directory:
    target=Path(directory).resolve();assert target.is_relative_to(workspace_runs)
    with RunLock(target/'runner.lock'):
        try:
            with RunLock(target/'runner.lock'):raise AssertionError('Duplicate lock accepted')
        except RuntimeError:pass
    window=tk.Tk();window.withdraw()
    try:
        ui=launcher.Launcher(window)
        with patch.object(launcher,'ROOT',target),patch.object(launcher,'active',return_value=True):
            ui.pause();assert (target/'PAUSE').is_file()
            ui.resume();assert not (target/'PAUSE').exists()
            ui.stop();assert (target/'STOP').is_file()
            try:check_controls(target)
            except KeyboardInterrupt:pass
            else:raise AssertionError('Stop signal ignored')
        class FakeProcess:
            stdout=io.StringIO('');returncode=0
            def wait(self):return 0
            def poll(self):return 0
        with patch.object(launcher,'ROOT',target),patch.object(launcher,'active',return_value=False),patch.object(launcher,'ProcessJob'),patch.object(launcher.subprocess,'Popen',return_value=FakeProcess()) as launch:
            ui.start()
            assert not (target/'STOP').exists()
            args=launch.call_args[0][0]
            assert args[-2:]==['--run','--uia']
    finally:window.destroy()
print('PASS: GUI construction, start command, pause/resume/stop signals, and duplicate-runner protection; no learning process launched')
