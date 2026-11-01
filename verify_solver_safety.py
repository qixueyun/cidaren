import json
from pathlib import Path
from local_solver import LocalSolver
root=Path(__file__).resolve().parent
solver=LocalSolver(root,json.loads((root/'config.json').read_text(encoding='utf-8')))
solver.config['fast_mode']=False
choices=['v. 承诺，保证','v. 把…写下来；把…记住','v. 全心全意投入','v. 花（钱或时间）']
sentence='< 返回 The University committed substantial funds to assisting mature students.\n目标单词：committed'
assert solver.answer(sentence,choices)==3
assert solver.answer(sentence,list(reversed(choices)))==0
assert solver.last_decision['source']=='reviewed_correction'
outputs=iter([{'choice':1,'confidence':.99},{'choice':1,'confidence':.99}])
solver.infer=lambda prompt:next(outputs)
assert solver.answer('A different unreviewed sentence.',choices)==0
assert solver.last_decision['source']=='disagreement_trial'
assert solver.last_decision['agreement'] is False
# After actual wrong feedback, the caller passes only remaining meanings.
remaining=choices[1:]
outputs=iter([{'choice':1,'confidence':.99},{'choice':3,'confidence':.99}])
solver.infer=lambda prompt:next(outputs)
assert solver.answer('A different unreviewed sentence.',remaining)==0
assert remaining[0]!=choices[0]
print('PASS: reviewed meaning follows shuffled options; disagreement returns first candidate; second decision uses remaining choices')
solver.config['fast_mode']=True
calls=[]
def fast_infer(prompt):
    calls.append(prompt)
    return {'choice':2}
solver.infer=fast_infer
assert solver.answer('New unreviewed question.',choices)==1
assert len(calls)==1 and solver.last_decision['source']=='fast_single_pass'
print('PASS: fast mode uses exactly one model request, no confidence or reasoning required')
