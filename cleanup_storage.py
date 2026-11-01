"""Remove only named, unused artifacts within this project; preview by default."""
import argparse,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def candidates():
    config=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    protected=[(ROOT/config[key]).resolve() for key in ('answer_model','whisper_model','engine_dir') if key in config]
    names=['models/answer.gguf','models/whisper','models/llama.zip','models/llama-vulkan.zip']
    names += [str(p.relative_to(ROOT)) for p in (ROOT/'models').glob('*.part') if p.with_suffix('').is_file()]
    result=[]
    for name in names:
        target=(ROOT/name).resolve()
        if not target.is_relative_to((ROOT/'models').resolve()):raise RuntimeError('Cleanup target outside models')
        if any(target==p or target.is_relative_to(p) or p.is_relative_to(target) for p in protected):continue
        if target.exists():result.append(target)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    total=0;rows=[]
    for path in candidates():
        size=sum(p.stat().st_size for p in path.rglob('*') if p.is_file()) if path.is_dir() else path.stat().st_size
        rows.append({'path':str(path.relative_to(ROOT)),'bytes':size});total+=size
        if args.apply:
            if path.is_dir():shutil.rmtree(path)
            else:path.unlink()
    report={'applied':args.apply,'freed_bytes':total,'files':rows}
    (ROOT/'runs/storage-cleanup.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
