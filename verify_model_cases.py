"""Real model regression checks, explicitly bypassing reviewed answer lookup."""
import json
from pathlib import Path
from local_solver import LocalSolver
root=Path(__file__).resolve().parent
solver=LocalSolver(root,json.loads((root/'config.json').read_text(encoding='utf-8')))
solver.corrections=[]
solver.bank=[]
cases=[
    ('The University committed substantial funds to assisting mature students.\n目标单词：committed',
     ['v. 承诺，保证','v. 把…写下来；把…记住','v. 全心全意投入','v. 花（钱或时间）'],3),
    ('There is an overlap of several days in which both treatments are given.\n目标单词：overlap',
     ['n. 交叠；重叠','v. 重叠；交叠','n. （电子）文档','n. 解释；评论；评注'],0),
]
try:
    solver.start()
    for sentence,choices,expected in cases:
        actual=solver.answer(sentence,choices)
        assert actual==expected,(actual,expected,solver.last_decision)
        print('PASS:',sentence.split('\n')[0],flush=True)
finally:
    solver.close()
