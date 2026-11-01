"""Select a Vulkan device by reported memory, not machine-specific index."""
import re
import subprocess

def parse_devices(text):
    devices=[]
    for line in text.splitlines():
        match=re.search(r'(Vulkan\d+):\s*(.*?)\s*\((\d+) MiB,\s*(\d+) MiB free\)',line)
        if match:
            device,name,total,free=match.groups()
            integrated=bool(re.search(r'\b\d{3}M\b|Radeon.*Graphics|Intel.*(?:UHD|Iris)',name,re.I))
            devices.append({'id':device,'name':name,'total':int(total),'free':int(free),'integrated':integrated})
    return devices

def select_device(executable):
    try:
        result=subprocess.run([str(executable),'--list-devices'],capture_output=True,timeout=20,
                              creationflags=subprocess.CREATE_NO_WINDOW)
    except (OSError,subprocess.SubprocessError):return 'none',0,'显卡检测失败，使用CPU'
    devices=parse_devices((result.stdout+result.stderr).decode('utf-8',errors='replace'))
    if result.returncode or not devices:return 'none',0,'未检测到可用Vulkan显卡，使用CPU'
    chosen=max(devices,key=lambda d:(not d['integrated'],d['free']))
    # Leave room for the desktop, KV cache and other applications. Auto fitting
    # can further reduce the selected layers when actual available VRAM is lower.
    layers=99 if chosen['free']>=6000 else 24 if chosen['free']>=4000 else 12 if chosen['free']>=2500 else 0
    if not layers:return 'none',0,'显存余量不足，使用CPU'
    return chosen['id'],layers,chosen['name']+'；可用显存 '+str(chosen['free'])+' MiB'
