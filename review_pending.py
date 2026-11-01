"""Apply a specific reviewed grammatical correction to the pending example only."""
from pathlib import Path
from question_memory import QuestionMemory, meaning_key
root=Path(__file__).resolve().parent
memory=QuestionMemory(root/'question_memory.json')
key=memory.data.get('active')
row=memory.data['questions'].get(key,{})
sentence=row.get('sentence','')
if 'There is an overlap of several days in which both treatments are given.' in sentence:
    pending=row.get('pending')
    if pending and meaning_key(pending).startswith('v'):
        memory.feedback(key,False)
        row['history'][-1]['review_reason']='an overlap为名词短语，动词选项经语法复核确认错误；不是UI反馈'
        memory.save()
        print('Reviewed pending verb sense as wrong; second attempt remains available')
else:
    print('No matching pending example; no change')
