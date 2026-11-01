import json
from pathlib import Path
from local_solver import LocalSolver
root=Path(__file__).resolve().parent
solver=LocalSolver(root,json.loads((root/'config.json').read_text(encoding='utf-8')))
solver.bank=[{'heard':'Hierarchical','meaning':'a. 按等级划分的；等级制度的'}]
choices=['a. 同时发生的；同步的','a. 故意的；有意的','a. 按等级划分的；等级制度的','a. 有意识的']
assert solver.answer('播放\n听到单词：hierarchical',choices,'hierarchical')==2
assert solver.last_decision['source']=='verified_listening_answer'
assert solver.answer('播放',list(reversed(choices)),'Hierarchical')==1
print('PASS: verified listening answer uses heard word and meaning, survives option shuffle without model inference')
