"""Play and transcribe current listening question, without submitting an answer."""
import json
from offline_runner import ROOT,Runner
from local_solver import LocalSolver
config=json.loads((ROOT/'config.json').read_text(encoding='utf-8'));config['input_backend']='uia'
r=Runner(config);r.select_window();image=r.capture();items=r.read(image)
play=r.find(items,'播放')
if play is None:raise RuntimeError('未识别到播放按钮')
r.solver=LocalSolver(ROOT,config)
heard=r.listen(play)
print('HEARD:',heard,flush=True)
(r.run_dir/'heard.txt').write_text(heard,encoding='utf-8')
print('AUDIO:',r.run_dir/'last-audio.npy',flush=True)
