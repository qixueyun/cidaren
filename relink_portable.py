"""Deduplicate a freshly built release after verifying identical file contents."""
import hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent

if __name__=='__main__':
    output=Path(json.loads((ROOT/'runs/portable-output.json').read_text(encoding='utf-8'))['folder']).resolve()
    if not output.is_relative_to(ROOT/'dist'):raise RuntimeError('Release outside dist')
    saved=0;count=0
    for folder in ('models','.deps','runtime','assets','licenses'):
        for destination in (output/folder).rglob('*'):
            if not destination.is_file():continue
            source=(ROOT/destination.relative_to(output)).resolve()
            if not source.is_relative_to(ROOT) or not destination.resolve().is_relative_to(output):raise RuntimeError('Unsafe path')
            if not source.is_file() or os.path.samefile(source,destination):continue
            if source.stat().st_size!=destination.stat().st_size:continue
            with source.open('rb') as a,destination.open('rb') as b:
                if hashlib.file_digest(a,'sha256').digest()!=hashlib.file_digest(b,'sha256').digest():continue
            temporary=destination.with_name(destination.name+'.hardlink-pending')
            os.link(source,temporary)
            os.replace(temporary,destination)
            saved+=source.stat().st_size;count+=1
    print(json.dumps({'deduplicated_bytes':saved,'hardlinked_files':count}),flush=True)
