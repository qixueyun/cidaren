"""Collect upstream license texts and source attribution for redistribution."""
from pathlib import Path
from prepare_models import download,ROOT

SOURCES={
 'llama.cpp-LICENSE.txt':'https://raw.githubusercontent.com/ggml-org/llama.cpp/b11998/LICENSE',
 'Qwen2.5-LICENSE.txt':'https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/raw/main/LICENSE',
 'Whisper-LICENSE.txt':'https://raw.githubusercontent.com/openai/whisper/main/LICENSE',
 'Tcl-license.txt':'https://raw.githubusercontent.com/tcltk/tcl/core-8-6-branch/license.terms',
 'Tk-license.txt':'https://raw.githubusercontent.com/tcltk/tk/core-8-6-branch/license.terms',
}
if __name__=='__main__':
    directory=ROOT/'licenses';directory.mkdir(exist_ok=True)
    for name,url in SOURCES.items():
        download(url,directory/name)
    (directory/'SOURCES.txt').write_text('\n'.join(f'{name}: {url}' for name,url in SOURCES.items())+
        '\nPython: https://www.python.org/ftp/python/3.13.5/ (license in runtime/LICENSE.txt)\n'+
        'Dependencies: exact versions and licenses are bundled in .deps/*dist-info.\n'+
        'Speech weights: https://huggingface.co/Systran/faster-whisper-tiny.en\n',encoding='utf-8')
    print('License texts collected')
