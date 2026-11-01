from offline_runner import Runner
r=Runner.__new__(Runner)
r.background=True
r.uia=False
r.cfg={}
try:
    r.run()
except RuntimeError as error:
    assert '禁止答题' in str(error)
else:
    raise AssertionError('Unverified background input was allowed')
print('PASS: unverified background mode cannot start model or submit answers')
