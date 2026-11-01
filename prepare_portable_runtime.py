"""Build an app-local CPython runtime with Tk; no installer or PATH changes."""
from pathlib import Path
import re,shutil,sys,zipfile
from prepare_models import download,ROOT

if __name__=='__main__':
    runtime=ROOT/'runtime';runtime.mkdir(exist_ok=True)
    archive=download('https://www.python.org/ftp/python/3.13.5/python-3.13.5-embed-amd64.zip',ROOT/'runs/python-embed.zip')
    with zipfile.ZipFile(archive) as bundle:
        for name in bundle.namelist():
            if not (runtime/name).resolve().is_relative_to(runtime.resolve()):raise RuntimeError('Unsafe archive')
        bundle.extractall(runtime)
    base=Path(sys.base_prefix)
    shutil.copytree(base/'Lib/tkinter',runtime/'Lib/tkinter',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','test'))
    shutil.copy2(base/'DLLs/_tkinter.pyd',runtime/'_tkinter.pyd')
    for name in ('tcl8.6','tk8.6','tcl8'):
        shutil.copytree(base/'Library/lib'/name,runtime/'tcl'/name,dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('demos','__pycache__'))
    lookup={p.name.lower():p for folder in (base,base/'Library/bin') for p in folder.glob('*.dll')}
    queue=[base/'Library/bin/tcl86t.dll',base/'Library/bin/tk86t.dll']
    queue += [p for p in base.glob('*.dll') if p.name.lower().startswith(('msvcp','vcruntime','concrt'))]
    copied=set()
    while queue:
        source=queue.pop();key=source.name.lower()
        if key in copied:continue
        copied.add(key)
        if not (runtime/source.name).exists():shutil.copy2(source,runtime/source.name)
        for raw in re.findall(rb'[A-Za-z0-9_.-]+\.dll\x00',source.read_bytes(),re.I):
            name=raw[:-1].decode('ascii').lower()
            if name in lookup and not (runtime/lookup[name].name).exists():queue.append(lookup[name])
    (runtime/'python313._pth').write_text('python313.zip\n.\nLib\n..\n../.deps\nimport site\n',encoding='ascii')
    print('Portable Python + Tk ready',runtime,flush=True)
