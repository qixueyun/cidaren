"""Produce a clean Windows package; immutable large files use NTFS hardlinks locally."""
import argparse,hashlib,json,os,shutil,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CODE=['launcher.py','offline_runner.py','offline_core.py','local_solver.py','question_memory.py',
      'runtime_control.py','process_job.py','background_window.py','uia_window.py','feedback_vision.py',
      'audio_capture.py','audio_resample.py','card_controls.py','unit_navigation.py','gpu_devices.py',
      'portable_env.py','portable_check.py','启动学习.cmd','检查环境.cmd','分享版说明.txt']
COPIED_FALLBACK_BYTES=0

def put(source,target,link=False):
    global COPIED_FALLBACK_BYTES
    target.parent.mkdir(parents=True,exist_ok=True)
    if link:
        try:os.link(source,target);return
        except OSError:COPIED_FALLBACK_BYTES+=source.stat().st_size
    shutil.copy2(source,target)

def tree(source,target,link=False):
    for path in source.rglob('*'):
        if not path.is_file() or any(part in ('__pycache__','.cache') for part in path.relative_to(source).parts):continue
        if path.suffix in ('.pyc','.pdb','.part'):continue
        put(path,target/path.relative_to(source),link)

def build():
    parser=argparse.ArgumentParser();parser.add_argument('--zip',action='store_true');args=parser.parse_args()
    output=ROOT/'dist'/('词达人便携版-'+time.strftime('%Y%m%d-%H%M%S'))
    output.mkdir(parents=True,exist_ok=False)
    for name in CODE:put(ROOT/name,output/name)
    config=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    config.update(model_device='auto',gpu_layers=99,engine_dir='models/llama-vulkan',model_port='auto',
                  window_titles=['微信','WeChat','词达人'],window_processes=['WeChatAppEx.exe','WeixinAppEx.exe'])
    (output/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    for name in ('.deps','runtime','assets','licenses'):tree(ROOT/name,output/name,True)
    # Only configured models. Personal progress, vocabulary, answers and logs are omitted.
    for path in (ROOT/'models').glob('qwen2.5-7b-instruct-q4_k_m-*.gguf'):put(path,output/'models'/path.name,True)
    for name in ('llama','llama-vulkan','whisper-tiny-en'):tree(ROOT/'models'/name,output/'models'/name,True)
    (output/'runs').mkdir()
    manifest=[]
    for path in output.rglob('*'):
        if path.is_file():manifest.append({'path':path.relative_to(output).as_posix(),'bytes':path.stat().st_size})
    (output/'manifest.json').write_text(json.dumps({'platform':'Windows x64','files':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
    if args.zip:
        with zipfile.ZipFile(output.with_suffix('.zip'),'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3,allowZip64=True) as archive:
            for path in output.rglob('*'):
                if path.is_file():archive.write(path,output.name+'/'+path.relative_to(output).as_posix(),
                    compress_type=zipfile.ZIP_STORED if path.suffix in ('.gguf','.bin') else zipfile.ZIP_DEFLATED)
    print(json.dumps({'folder':str(output),'logical_bytes':sum(row['bytes'] for row in manifest),
                      'hardlink_fallback_copied_bytes':COPIED_FALLBACK_BYTES,
                      'note':'Large immutable files use local hardlinks; copying or zipping produces ordinary independent files.'},ensure_ascii=False),flush=True)
    (ROOT/'runs/portable-output.json').write_text(json.dumps({'folder':str(output)},ensure_ascii=False),encoding='utf-8')

if __name__=='__main__':build()
