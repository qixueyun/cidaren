"""Download the pinned official portable Vulkan engine; no system installation."""
import hashlib
import json
import zipfile
from prepare_models import ROOT, MODELS, download

TAG='b11998'
URL=f'https://github.com/ggml-org/llama.cpp/releases/download/{TAG}/llama-{TAG}-bin-win-vulkan-x64.zip'

if __name__=='__main__':
    archive=download(URL,MODELS/'llama-vulkan.zip')
    output=(MODELS/'llama-vulkan').resolve()
    output.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            if not (output/member.filename).resolve().is_relative_to(output):
                raise RuntimeError('Unsafe archive path')
        bundle.extractall(output)
    (output/'source.json').write_text(json.dumps({'url':URL,'release':TAG,
        'download_sha256':hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()},indent=2),encoding='utf-8')
    print('Portable Vulkan engine ready:',output,flush=True)
