import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.deps'))
from offline_core import numbers
from local_solver import LocalSolver

assert numbers('单元进度100% 单词总数：30 单元得分：11.6')['score'] == 11.6
rows = json.loads((ROOT / 'runs/analysis.json').read_text(encoding='utf-8'))
sentence = next(r for r in rows if r['file'] == '句意选词题型.png')
assert sentence['kind'] == 'sentence'
assert next(r for r in rows if r['file'] == '听力选词题型.png')['kind'] == 'listening'
for row in rows:
    if row['kind'] == 'select':
        assert len(row['words']) == 30
        assert sum(w['selected'] for w in row['words']) == 10
solver = LocalSolver(ROOT, json.loads((ROOT / 'config.json').read_text(encoding='utf-8')))
try:
    solver.start()
    answer = solver.answer('While there is some overlap, the activities each participant engages in are different. 目标单词：overlap', sentence['options'])
    assert answer == 2, answer
    print('PASS: screenshots, counts, score semantics, local model noun/verb disambiguation', flush=True)
finally:
    solver.close()
