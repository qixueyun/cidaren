"""Offline preflight for a copied package; never operates WeChat."""
import json,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.deps'))
from portable_env import configure
configure()

def main():
    import tkinter as tk
    import numpy as np
    import cv2,onnxruntime,pyautogui,soundcard,ctranslate2,av
    from rapidocr_onnxruntime import RapidOCR
    from faster_whisper import WhisperModel
    root=tk.Tk();root.withdraw();root.update();root.destroy()
    RapidOCR(use_angle_cls=False)
    config=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    WhisperModel(str(ROOT/config['whisper_model']),device='cpu',compute_type='int8',local_files_only=True,cpu_threads=2)
    from local_solver import LocalSolver
    solver=LocalSolver(ROOT,config)
    command=solver.engine_command()
    assert (ROOT/config['answer_model']).is_file()
    assert list((ROOT/'assets').glob('uia_invoke.exe')),'缺少UIA辅助程序'
    if '--model' in sys.argv:
        try:
            solver.start()
            choice=solver.answer('This is a test. 目标单词：test',['n. 测试','v. 离开'])
            print(json.dumps({'model_inference_ok':True,'choice':choice+1}),flush=True)
        finally:solver.close()
    print(json.dumps({'ok':True,'python':sys.executable,'paths':sys.path,'engine_command':command,
                      'numpy':np.__version__},ensure_ascii=False),flush=True)

if __name__=='__main__':
    try:main()
    except Exception:
        import traceback
        traceback.print_exc();raise SystemExit(1)
