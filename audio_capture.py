"""Continuously drain WASAPI loopback while UIA playback is invoked."""
import ctypes
import queue
import threading
import time
import numpy as np

def record_playback(play,seconds=4):
    import soundcard as sc
    ready=threading.Event();stop=threading.Event();result=queue.Queue()
    def worker():
        status=ctypes.windll.ole32.CoInitializeEx(None,0)
        try:
            speaker=sc.default_speaker()
            mic=sc.get_microphone(speaker.id,include_loopback=True)
            chunks=[]
            with mic.recorder(samplerate=48000,channels=2,blocksize=4800) as recorder:
                recorder.record(numframes=4800)
                ready.set()
                deadline=time.monotonic()+15
                while not stop.is_set() and time.monotonic()<deadline:
                    chunks.append(recorder.record(numframes=4800))
            if not chunks:raise RuntimeError('没有取得录音帧')
            result.put(np.concatenate(chunks,axis=0).mean(axis=1).astype(np.float32))
        except Exception as error:
            result.put(error);ready.set()
        finally:
            if status in (0,1):ctypes.windll.ole32.CoUninitialize()
    threading.Thread(target=worker,daemon=True).start()
    if not ready.wait(8):raise RuntimeError('录音设备初始化超时')
    if not result.empty():raise result.get()
    try:
        play()
        time.sleep(seconds)
    finally:
        stop.set()
    try:audio=result.get(timeout=5)
    except queue.Empty:raise RuntimeError('录音结束超时')
    if isinstance(audio,Exception):raise audio
    return audio
