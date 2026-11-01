"""Compare local CPU/GPU inference with identical prompts; no WeChat interaction."""
import json
from pathlib import Path
import statistics
import subprocess
import time
from local_solver import LocalSolver
from runtime_control import RunLock

ROOT=Path(__file__).resolve().parent
CASES=[
 ('There is an overlap of several days in which both treatments are given. 目标单词：overlap',['n. 交叠；重叠','v. 重叠；交叠','n. （电子）文档','n. 议论；评论；解释']),
 ('The organization is extending the range of markets into which its services will be delivered. 目标单词：extending',['v. 拓展；扩大影响','v. 适用于；包括','v. 延长；使延期','v. 提供；给予']),
 ('The committee reviewed the evidence carefully before making a decision. 目标单词：reviewed',['v. 审查；复查','v. 重叠','n. 半球','n. 爆发']),
]

if __name__=='__main__':
    cfg=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    report={}
    with RunLock(ROOT/'runs/runner.lock'):
        for name,directory,device,layers in [('cpu','models/llama','none',0),('gpu','models/llama-vulkan','auto',99)]:
            current=dict(cfg,engine_dir=directory,model_device=device,gpu_layers=layers,model_port=18766,
                         model_log=f'runs/benchmark-{name}.log')
            solver=LocalSolver(ROOT,current);solver.bank=[];solver.corrections=[]
            try:
                begin=time.perf_counter();solver.start()
                result={'startup_seconds':round(time.perf_counter()-begin,3),'cases':[]}
                solver.answer('A simple test. 目标单词：test',['n. 测试','v. 离开'])
                result['gpu_memory']=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.used','--format=csv,noheader'],text=True).strip()
                for sentence,choices in CASES:
                    begin=time.perf_counter();answer=solver.answer(sentence,choices)
                    result['cases'].append({'seconds':round(time.perf_counter()-begin,3),'choice':answer+1})
                result['median_seconds']=statistics.median(row['seconds'] for row in result['cases'])
                report[name]=result
                print(name,json.dumps(result,ensure_ascii=False),flush=True)
            finally:solver.close()
    report['speedup']=round(report['cpu']['median_seconds']/report['gpu']['median_seconds'],2)
    (ROOT/'runs/gpu-benchmark.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('SPEEDUP',report['speedup'],flush=True)
