"""Device order, low-VRAM selection and dependency-free audio downsampling."""
import sys,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent/'.deps'))
import numpy as np
from gpu_devices import parse_devices,select_device
from audio_resample import downsample_48k

listing=b'Vulkan0: AMD Radeon(TM) 780M (16000 MiB, 15000 MiB free)\nVulkan2: NVIDIA GeForce RTX 3060 (6000 MiB, 4100 MiB free)'
with patch('gpu_devices.subprocess.run',return_value=subprocess.CompletedProcess([],0,listing,b'')):
    device,layers,_=select_device('engine.exe')
assert (device,layers)==('Vulkan2',24)
with patch('gpu_devices.subprocess.run',side_effect=OSError('no driver')):
    assert select_device('engine.exe')[:2]==('none',0)
with patch('gpu_devices.subprocess.run',return_value=subprocess.CompletedProcess([],0,b'Vulkan0: AMD Radeon RX 6600 (8000 MiB, 7000 MiB free)',b'')):
    assert select_device('engine.exe')[:2]==('Vulkan0',99)
t=np.arange(48000)/48000
speech=downsample_48k(np.sin(2*np.pi*1000*t))
alias=downsample_48k(np.sin(2*np.pi*20000*t))
assert len(speech)==16000 and speech.dtype==np.float32
assert .69<np.sqrt(np.mean(speech[100:-100]**2))<.72
assert np.sqrt(np.mean(alias[100:-100]**2))<.01
print('PASS: reordered GPUs, integrated-GPU exclusion, 6GB partial offload, AMD selection, missing-driver CPU fallback, 48k/16k FIR resampling')
