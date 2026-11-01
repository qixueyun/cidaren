"""Standard-library manual control panel; no extra installation required."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
from portable_env import configure
configure()
import tkinter as tk
from tkinter import ttk,messagebox
from tkinter.scrolledtext import ScrolledText
from runtime_control import active
from process_job import ProcessJob

ROOT=Path(__file__).resolve().parent

class Launcher:
    def __init__(self,window):
        self.window=window;self.process=None;self.job=None;self.messages=queue.Queue();self.closing=False
        self.runner_args=['--run','--uia'];self.stop_deadline=None
        window.title('词达人学习控制台');window.geometry('720x480')
        ttk.Label(window,text='先在微信打开要练习的单元，再点击“开始学习”。',padding=12).pack(anchor='w')
        ttk.Label(window,text='快速模式 · UI Automation直接调用 · 可能激活微信窗口',padding=(12,0,12,8)).pack(anchor='w')
        self.status=tk.StringVar(value='等待启动')
        ttk.Label(window,textvariable=self.status,padding=12).pack(anchor='w')
        buttons=ttk.Frame(window,padding=(12,0));buttons.pack(fill='x')
        for label,command in [('开始学习',self.start),('暂停',self.pause),('继续',self.resume),('停止',self.stop),('打开日志',self.logs)]:
            ttk.Button(buttons,text=label,command=command).pack(side='left',padx=(0,8))
        self.output=ScrolledText(window,height=16,state='disabled',font=('Microsoft YaHei UI',10))
        self.output.pack(fill='both',expand=True,padx=12,pady=12)
        self.append('停止会先保存并退出；超过5秒仍未退出，会结束本次脚本及其模型进程。')
        config=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
        if config.get('model_device'):
            self.append('模型推理设备：'+config['model_device']+'；GPU层数：'+str(config.get('gpu_layers','自动')))
        window.protocol('WM_DELETE_WINDOW',self.close)
        window.after(200,self.poll)

    def append(self,text):
        self.output.configure(state='normal');self.output.insert('end',text+'\n')
        self.output.see('end');self.output.configure(state='disabled')

    def clear_flag(self,name):
        path=ROOT/name
        if path.is_file():path.unlink()

    def start(self):
        if self.process is not None and self.process.poll() is None:
            self.status.set('脚本已启动或正在启动，请勿重复点击');return
        if active(ROOT):
            self.status.set('已有脚本运行，可使用暂停、继续或停止按钮');return
        self.clear_flag('STOP');self.clear_flag('PAUSE')
        self.stop_deadline=None
        env=os.environ.copy();env['PYTHONUTF8']='1';env['PYTHONUNBUFFERED']='1'
        try:
            self.process=subprocess.Popen([sys.executable,str(ROOT/'offline_runner.py'),*self.runner_args],cwd=ROOT,
                env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW)
            self.job=ProcessJob(self.process)
        except OSError as error:
            if self.process is not None and self.process.poll() is None:
                self.process.terminate();self.process.wait(timeout=5)
            self.process=None
            messagebox.showerror('启动失败',str(error));return
        process=self.process
        def read_output():
            for line in process.stdout:self.messages.put(line.rstrip())
            process.wait()
        threading.Thread(target=read_output,daemon=True).start()
        self.status.set('启动中，正在载入本地模型…');self.append('已启动学习脚本。')

    def pause(self):
        if not self.running():self.status.set('当前没有运行中的学习脚本');return
        (ROOT/'PAUSE').write_text('manual pause',encoding='utf-8')
        self.status.set('已请求暂停，等待当前操作完成')

    def resume(self):
        if (ROOT/'STOP').exists():self.status.set('已请求停止，请等待退出后重新开始');return
        self.clear_flag('PAUSE')
        self.status.set('运行中' if self.running() else '脚本未运行，请点击开始学习')

    def stop(self):
        if not self.running():self.status.set('当前没有运行中的学习脚本');return
        (ROOT/'STOP').write_text('manual stop',encoding='utf-8')
        if self.process is not None and self.stop_deadline is None:self.stop_deadline=time.monotonic()+5
        self.status.set('已请求停止，等待保存记录并退出')

    def running(self):
        return (self.process is not None and self.process.poll() is None) or active(ROOT)

    def logs(self):
        try:
            (ROOT/'runs').mkdir(exist_ok=True);os.startfile(ROOT/'runs')
        except OSError as error:
            self.append('无法自动打开日志目录：'+str(error)+'；目录：'+str(ROOT/'runs'))

    def poll(self):
        while not self.messages.empty():
            line=self.messages.get()
            try:
                row=json.loads(line);event=row.get('event','')
                labels={'page':'页面','heard_word':'识别单词','answer':'提交答案','verified_feedback':'答案反馈',
                        'wrong_option_excluded':'排除错误选项','complete':'单元完成','paused':'运行异常','stopped':'已停止','model_ready':'模型已就绪',
                        'open_failure_card_settings':'打开错题卡片设置','disable_wrong_card_popups':'关闭错题弹出',
                        'wrong_card_popups_disabled':'已确认错题弹出关闭','close_disabled_failure_card':'关闭错题卡片',
                        'waiting_for_loading':'等待页面加载','waiting_for_unit_ready':'等待单元数据和选词按钮',
                        'waiting_for_familiar_ready':'等待单词卡片继续按钮','retry_observation':'正在自动重新识别','model_device':'推理设备'}
                details=row.get('description') or row.get('reason') or row.get('word') or row.get('kind') or ''
                if event=='answer':details='第'+str(row.get('choice'))+'项'
                if event=='verified_feedback':details='正确选项：第'+str(row.get('correct_choice'))+'项'
                self.append(row.get('time','')+' '+labels.get(event,event)+' '+str(details))
                if event=='page' and not (ROOT/'PAUSE').exists() and not (ROOT/'STOP').exists():self.status.set('运行中')
                if event=='model_ready':self.status.set('模型已就绪（启动停止测试）')
            except (ValueError,TypeError):self.append(line)
        if self.process is not None and self.process.poll() is None and self.stop_deadline is not None and time.monotonic()>=self.stop_deadline:
            if self.job:
                self.job.terminate();self.append('已结束本次学习脚本及其模型进程。')
            self.stop_deadline=None
        if self.process is not None and self.process.poll() is not None:
            code=self.process.returncode;self.process=None
            if self.job:self.job.close();self.job=None
            self.stop_deadline=None
            self.status.set('已停止，可重新开始' if (ROOT/'STOP').exists() else '已结束，请查看下方日志（退出码 '+str(code)+'）')
        if self.closing and not self.running():self.window.destroy();return
        self.window.after(200,self.poll)

    def close(self):
        if self.running():
            if not messagebox.askyesno('关闭控制台','关闭时将停止学习并保存记录，是否关闭？'):return
            self.closing=True;self.stop();self.status.set('正在停止，完成后自动关闭…')
        else:self.window.destroy()

if __name__=='__main__':
    window=tk.Tk();Launcher(window);window.mainloop()
