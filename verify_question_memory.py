from pathlib import Path
import tempfile
from question_memory import QuestionMemory, question_key

workspace_runs=(Path(__file__).resolve().parent/'runs').resolve()
with tempfile.TemporaryDirectory(dir=workspace_runs) as directory:
    assert Path(directory).resolve().is_relative_to(workspace_runs)
    path=Path(directory)/'memory.json'
    memory=QuestionMemory(path)
    choices=['v. 承诺，保证','v. 花（钱或时间）','v. 记住','v. 全心全意投入']
    key=question_key('The University committed funds.\n目标单词：committed')
    assert memory.available(key,'example',choices)==[0,1,2,3]
    memory.reserve(key,choices[0])
    memory.no_feedback(key)
    assert memory.data['questions'][key]['history'][-1]['source']=='assumed_wrong_no_feedback_user_rule'
    # Restart and shuffle: the wrong meaning stays excluded.
    memory=QuestionMemory(path)
    shuffled=list(reversed(choices))
    assert memory.available(key,'example',shuffled)==[0,1,2]
    memory.reserve(key,shuffled[0])
    memory.feedback(key,False)
    memory=QuestionMemory(path)
    try:
        memory.available(key,'example',choices)
    except RuntimeError as error:
        assert '2次' in str(error)
    else:
        raise AssertionError('Third attempt was allowed')
    other=question_key('A different question.\n目标单词：question')
    memory.available(other,'other',choices)
    memory.reserve(other,choices[1])
    memory.feedback(other,True)
    assert memory.data['questions'][other]['solved']
print('PASS: wrong answers excluded by meaning, survives restart and shuffle, third attempt blocked, success recorded')
