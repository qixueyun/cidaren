"""Reversible menu test for the integrated UIA coordinate-to-control adapter."""
import json
from offline_runner import ROOT,Runner
config=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
config['input_backend']='uia'
runner=Runner(config);runner.select_window()
image=runner.capture();items=runner.read(image)
if any('查看单词用法' in t.text for t in items):
    runner.bg.invoke('dismiss-overlay')
    image=runner.capture();items=runner.read(image)
    assert not any('查看单词用法' in t.text for t in items),'Existing menu did not close'
assert 675<=image.width<=690 and 1340<=image.height<=1360,image.size
runner.click((image.width-55,110))
opened=runner.capture();opened_items=runner.read(opened)
opened.save(runner.run_dir/'uia-menu-open.png')
assert any('查看单词用法' in t.text for t in opened_items),'UIA menu did not open'
runner.bg.invoke('dismiss-overlay')
closed=runner.capture();closed_items=runner.read(closed)
closed.save(runner.run_dir/'uia-menu-closed.png')
assert not any('查看单词用法' in t.text for t in closed_items),'Menu did not close'
print('PASS: UIA point-to-control Invoke opened menu and restored original page, no answers submitted')
