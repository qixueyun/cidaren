"""Check GPU/CPU command selection without starting either model."""
import json
from pathlib import Path
from local_solver import LocalSolver
from unittest.mock import patch

root=Path(__file__).resolve().parent
config=json.loads((root/'config.json').read_text(encoding='utf-8'))
solver=LocalSolver(root,config)
with patch('gpu_devices.select_device',return_value=('Vulkan2',99,'test discrete GPU')):
    command=solver.engine_command()
assert 'llama-vulkan' in command[0]
assert command[command.index('--device')+1]=='Vulkan2'
assert command[command.index('--gpu-layers')+1]=='99'
assert command[command.index('--port')+1]=='18765'
cpu=LocalSolver(root,dict(config,engine_dir='models/llama',model_device='none',gpu_layers=0,model_port=18766))
command=cpu.engine_command()
assert 'llama-vulkan' not in command[0]
assert command[command.index('--gpu-layers')+1]=='0'
assert cpu.base_url.endswith(':18766')
print('PASS: GPU uses explicit discrete device and full offload; CPU and isolated benchmark port retained')
