"""One-time online preparation. Runtime never downloads models."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.deps'))
MODELS = ROOT / 'models'
MODELS.mkdir(exist_ok=True)


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'cidaren-local'}), timeout=60) as r:
        return json.load(r)


def download(url, target):
    target = Path(target)
    if target.exists():
        return target
    partial = target.with_suffix(target.suffix + '.part')
    offset = partial.stat().st_size if partial.exists() else 0
    request = urllib.request.Request(url, headers={'User-Agent': 'cidaren-local'})
    if offset:
        request.add_header('Range', f'bytes={offset}-')
    with urllib.request.urlopen(request, timeout=120) as response:
        mode = 'ab' if response.status == 206 else 'wb'
        with partial.open(mode) as f:
            while block := response.read(1024 * 1024):
                f.write(block)
    partial.replace(target)
    return target


def llm():
    repo = 'Qwen/Qwen2.5-7B-Instruct-GGUF'
    filenames = ['qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf',
                 'qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf']
    from huggingface_hub import snapshot_download
    snapshot_download(repo,local_dir=str(MODELS),allow_patterns=filenames,max_workers=2)
    if not all((MODELS/name).is_file() for name in filenames):
        raise RuntimeError('模型分片下载未完成')
    print('Language model ready',flush=True)


def speech():
    from huggingface_hub import snapshot_download
    snapshot_download('Systran/faster-whisper-tiny.en', local_dir=str(MODELS / 'whisper-tiny-en'),
                      allow_patterns=['model.bin', 'config.json', 'tokenizer.json', 'vocabulary.*', 'preprocessor_config.json'])
    print('Speech model ready', flush=True)


def engine():
    release = {'tag_name': 'b11998'}
    asset = {
        'browser_download_url': 'https://github.com/ggml-org/llama.cpp/releases/download/b11998/llama-b11998-bin-win-cpu-x64.zip',
        'digest': 'sha256:2cdb7ff52769dff9bf19c4cf7d6b6e136e7b46249679d5d92ecd92631b8f7fb2'
    }
    dest = download(asset['browser_download_url'], MODELS / 'llama.zip')
    if asset.get('digest', '').startswith('sha256:'):
        digest = hashlib.file_digest(dest.open('rb'), 'sha256').hexdigest()
        if digest != asset['digest'].split(':')[1]:
            raise RuntimeError('llama.cpp SHA256 mismatch')
    output = (MODELS / 'llama').resolve()
    output.mkdir(exist_ok=True)
    with zipfile.ZipFile(dest) as z:
        for member in z.infolist():
            if not (output / member.filename).resolve().is_relative_to(output):
                raise RuntimeError('Unsafe archive path')
        z.extractall(output)
    (MODELS / 'engine-source.json').write_text(json.dumps({
        'release': release['tag_name'], 'url': asset['browser_download_url'],
        'digest': asset.get('digest')}, indent=2), encoding='utf-8')
    print('Inference engine ready', flush=True)


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(f) for f in (llm, speech, engine)]
        for future in concurrent.futures.as_completed(futures):
            future.result()
