"""Audit generated release contents and refresh the final file manifest."""
import json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
output=Path(json.loads((ROOT/'runs/portable-output.json').read_text(encoding='utf-8'))['folder']).resolve()
assert output.is_relative_to(ROOT/'dist')
for name in ('question_memory.json','verified_answers.json','corrections.json','unit_vocabulary.json','STOP','PAUSE'):
    assert not (output/name).exists(),name
assert not list((output/'runs').iterdir()),'Release contains runtime logs'
config=json.loads((output/'config.json').read_text(encoding='utf-8'))
assert config['model_device']=='auto' and config['model_port']=='auto'
assert len(list((output/'models').glob('*.gguf')))==2
assert os.path.samefile(ROOT/config['answer_model'],output/config['answer_model'])
files=[p for p in output.rglob('*') if p.is_file() and p.name!='manifest.json']
manifest={'platform':'Windows x64','files':[{'path':p.relative_to(output).as_posix(),'bytes':p.stat().st_size} for p in files]}
(output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
report={'release':str(output),'GiB':round(sum(p.stat().st_size for p in files)/1024**3,3),
        'files':len(files),'privacy_check':'passed','model_hardlink_check':'passed'}
(ROOT/'runs/release-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False),flush=True)
