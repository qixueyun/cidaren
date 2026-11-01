"""Windows local runner. --analyze reads files; --run controls the chosen miniapp."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.deps'))
import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR
from offline_core import (Text, checkbox_checked, compact, numbers, options,
                          page_kind, selected_green, word_items, loading_overlay)
from uia_window import UIATargetUnavailable,UIABatchPartial
from unit_navigation import task_rows,all_badges_ten
from question_memory import QuestionMemory, question_key
from feedback_vision import feedback_markers
from runtime_control import RunLock,check_controls


class LayoutChanged(RuntimeError):
    pass

class RetryObservation(RuntimeError):
    """Uncertain observation before input: retry without submitting anything."""
    pass


class Runner:
    def __init__(self, config):
        self.cfg = config
        self.ocr = RapidOCR(use_angle_cls=config.get('ocr_angle_cls',False))
        self.ocr_frame_key=None
        self.ocr_frame_items=None
        self.last_image = None
        self.words = set()
        vocabulary=ROOT/'unit_vocabulary.json'
        if vocabulary.exists():
            self.words.update(json.loads(vocabulary.read_text(encoding='utf-8')))
        self.total = None
        self.rounds = 0
        self.stagnant = 0
        self.last_score = None
        self.last_question = None
        self.last_question_time = 0
        self.last_submission = None
        self.unknown_since = None
        self.notice_attempts = 0
        self.loading_since = None
        self.feedback_since = None
        self.run_dir = ROOT / 'runs' / time.strftime('%Y%m%d-%H%M%S')
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.solver = None
        self.checkpoint = ROOT / 'runs/checkpoint.json'
        self.memory = QuestionMemory(ROOT / 'question_memory.json')
        self.last_submission = self.memory.pending_submission()
        self.after_failure_card = False
        self.card_setting_attempts=0
        self.card_popups_disabled=False
        self.leaving_completed_unit=False
        self.task_scroll_signature=None
        self.unit_ready_since=None
        self.familiar_wait_since=None
        self.word_ocr=None
        self.audio_encounter=None
        active=self.memory.data['questions'].get(self.memory.data.get('active'),{})
        submission=active.get('submission') or {}
        if not active.get('solved') and '\n听到单词：' in submission.get('sentence',''):
            from question_memory import meaning_key
            self.audio_encounter={'options':sorted(meaning_key(t) for t in submission['choices']),
                                  'key':submission['key']}
        self.uia = config.get('input_backend')=='uia'
        self.background = bool(config.get('background',False)) or self.uia

    def read(self, im):
        self.last_image = im
        # Exact pixels only: changing options, feedback, or window dimensions
        # must invalidate the cache, even for a one-pixel change.
        frame_key=(im.size,hashlib.sha256(im.convert('RGB').tobytes()).digest())
        if frame_key==self.ocr_frame_key:
            return list(self.ocr_frame_items)
        if loading_overlay(im):
            return []
        result, _ = self.ocr(np.asarray(im.convert('RGB')))
        items = [Text(str(t), float(s), b) for b, t, s in (result or []) if float(s) >= .65]
        if any('用法' in t.text for t in items) and any('例句' in t.text for t in items) and not self.find(items,'返回'):
            import cv2
            rgb=np.asarray(im.convert('RGB')).astype(float)
            r,g,b=rgb[...,0],rgb[...,1],rgb[...,2]
            ink=((r>150)&(r>g*1.5)&(r>b*1.5)).astype('uint8')
            ink[:int(im.height*.8)]=0
            count,labels,stats,_=cv2.connectedComponentsWithStats(ink)
            for label in range(1,count):
                if stats[label,cv2.CC_STAT_WIDTH]>im.width*.25:
                    ink[labels==label]=0
            start=int(im.height*.8)
            clean=np.full((im.height-start,im.width,3),255,np.uint8)
            clean[ink[start:]>0]=0
            extra,_=self.ocr(clean)
            for box,text,score in extra or []:
                if compact(text)=='返回' and float(score)>=.6:
                    items.append(Text('返回',float(score),[[float(p[0]),float(p[1])+start] for p in box]))
        if im.height > 500 and len(options(items)) in (2, 3) and not any('词义' in t.text for t in items):
            # Recover missed short options and multiline definitions by reading
            # each of the four observed rounded rectangles independently.
            import cv2
            rgb0 = np.asarray(im.convert('RGB'))
            edges = cv2.Canny(rgb0, 40, 100)
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            boxes = []
            for c in contours:
                x,y,w,h = cv2.boundingRect(c)
                if not (w > im.width*.5 and 35 < h < im.height*.16 and
                        y > im.height*.15 and y+h < im.height*.9):
                    continue
                if any(abs(y-yy)<8 for xx,yy,ww,hh in boxes):
                    continue
                boxes.append((x,y,w,h))
            boxes.sort(key=lambda b:b[1])
            if len(boxes)==4:
                recovered=[]
                for x,y,w,h in boxes:
                    crop=im.crop((x+3,y+3,x+w-3,y+h-3)).resize((2*(w-6),2*(h-6)))
                    raw,_=self.ocr(np.asarray(crop))
                    lines=sorted(raw or [],key=lambda a:(a[0][0][1],a[0][0][0]))
                    text=' '.join(str(t) for box,t,s in lines if float(s)>=.5)
                    if not text:
                        break
                    recovered.append(Text(text,min(float(s) for box,t,s in lines),
                                          [[x,y],[x+w,y],[x+w,y+h],[x,y+h]],'option'))
                if len(recovered)==4:
                    items=[t for t in items if not any(x<=t.center[0]<=x+w and y<=t.center[1]<=y+h
                                                       for x,y,w,h in boxes)]+recovered
        if im.height > 500 and not self.find(items, '继续'):
            # Some OCR detectors miss white lettering on the green action button.
            # Locate its actual colored region and OCR its text as black on white.
            import cv2
            rgb = np.asarray(im.convert('RGB')).astype(float)
            r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
            green = ((g > 120) & (g > r * 1.5) & (g > b * 1.2)).astype('uint8') * 255
            green[:int(im.height * .75)] = 0
            contours, _ = cv2.findContours(green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w < im.width * .2 or h < 25:
                    continue
                inside = np.zeros(green.shape, np.uint8)
                cv2.drawContours(inside, [contour], -1, 255, -1)
                inside = cv2.erode(inside, np.ones((7, 7), np.uint8))
                white_text = (rgb.min(axis=2) > 210) & (inside > 0)
                clean = np.full((h + 24, w + 24, 3), 255, dtype=np.uint8)
                clean[12:h+12,12:w+12][white_text[y:y+h,x:x+w]] = 0
                extra, _ = self.ocr(clean)
                for box, text, score in extra or []:
                    if '加载' in compact(text) and float(score)>=.5:
                        items.append(Text('加载中',float(score),[[x,y],[x+w,y],[x+w,y+h],[x,y+h]]))
                    if compact(text) in ('继续','开始选词','重新选词','开始练习','继续练习') and float(score) >= .65:
                        mapped = [[float(p[0])+x-12, float(p[1])+y-12] for p in box]
                        items.append(Text(compact(text), float(score), mapped))
        self.ocr_frame_key=frame_key
        self.ocr_frame_items=list(items)
        return items

    def record(self, event, **data):
        row = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'event': event, **data}
        print(json.dumps(row, ensure_ascii=False), flush=True)
        with (self.run_dir / 'events.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')

    def find(self, items, label):
        return next((t for t in items if
                     (compact(t.text).lstrip('<〈《‹＜←﹤') if label=='返回' else compact(t.text)) == label), None)

    def wait_unit_ready(self,reason):
        if self.unit_ready_since is None:
            self.unit_ready_since=time.monotonic()
            self.record('waiting_for_unit_ready',reason=reason)
        if time.monotonic()-self.unit_ready_since>45:
            raise RuntimeError('单元详情等待45秒仍未就绪：'+reason)
        return False

    def select_window(self):
        import pyautogui as pg
        import pygetwindow as gw
        self.pg = pg
        pg.FAILSAFE = True
        pg.PAUSE = .15
        user = ctypes.windll.user32
        kernel = ctypes.windll.kernel32
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                      wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        candidates = []
        titles=set(self.cfg.get('window_titles',[self.cfg['window_title']]))
        processes={name.lower() for name in self.cfg.get('window_processes',[self.cfg['window_process']])}
        for window in gw.getAllWindows():
            if window.title not in titles:
                continue
            pid = wintypes.DWORD()
            user.GetWindowThreadProcessId(window._hWnd, ctypes.byref(pid))
            handle = kernel.OpenProcess(0x1000, False, pid.value)
            if not handle:
                continue
            try:
                buffer = ctypes.create_unicode_buffer(32768)
                size = wintypes.DWORD(len(buffer))
                if kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                    if Path(buffer.value).name.lower() in processes:
                        candidates.append(window)
            finally:
                kernel.CloseHandle(handle)
        if len(candidates) != 1:
            raise RuntimeError(f'需要唯一微信小程序窗口，当前找到{len(candidates)}个')
        self.window = candidates[0]
        if self.background:
            if self.uia:
                from uia_window import UIAWindow
                self.bg=UIAWindow(self.window._hWnd)
                self.record('uia_mode',notice='UIA调用可能激活微信；不会模拟鼠标点击')
                from background_window import u
                if u.IsIconic(self.window._hWnd):
                    u.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
                    u.ShowWindow(self.window._hWnd,4)
                    time.sleep(.3)
            else:
                from background_window import BackgroundWindow
                self.bg=BackgroundWindow(self.window._hWnd)
            self.bg.guard()
            return
        try:
            self.window.activate()
        except Exception:
            # Windows can report activation failure even when focus was set.
            if user.GetForegroundWindow() != self.window._hWnd:
                raise RuntimeError('Windows未允许激活小程序；请将词达人窗口切到前台后重新运行')
        time.sleep(1)

    def guard(self):
        check_controls(ROOT)
        if self.background:
            self.bg.guard()
            return
        if ctypes.windll.user32.GetAsyncKeyState(0x1B) & 0x8000:
            raise KeyboardInterrupt('Escape')
        if ctypes.windll.user32.GetForegroundWindow() != self.window._hWnd:
            raise RuntimeError('小程序失去焦点，已暂停')
        if self.window.width < 250 or self.window.height < 400:
            raise RuntimeError('小程序窗口过小或已最小化')

    def capture(self):
        self.guard()
        self.origin = (self.window.left, self.window.top)
        if self.background:
            return self.bg.capture()
        return self.pg.screenshot(region=(*self.origin, self.window.width, self.window.height))

    def click(self, point, settle=True):
        self.guard()
        if not self.uia and (self.window.left, self.window.top) != self.origin:
            raise LayoutChanged('窗口移动，重新截图识别')
        x, y = point.center if isinstance(point, Text) else point
        if not 0 <= x < self.window.width or not 0 <= y < self.window.height:
            raise RuntimeError('点击坐标越界')
        if self.background:
            try:
                self.bg.click(x,y)
            except UIATargetUnavailable:
                if not self.uia or not isinstance(point,Text):
                    raise
                # Point lookup issued no action; resolve the same unique text.
                self.bg.invoke(point.text.strip())
        else:self.pg.click(self.origin[0] + x, self.origin[1] + y)
        if settle:
            time.sleep(self.cfg['settle_seconds'])

    def listen(self, play):
        from audio_capture import record_playback
        from audio_resample import downsample_48k
        def start_playback():
            self.guard()
            if self.uia:
                self.bg.invoke('播放')
            else:
                self.click(play,settle=False)
        mono=record_playback(start_playback,self.cfg['audio_seconds'])
        if float(np.sqrt(np.mean(mono ** 2))) < .001:
            raise RetryObservation('没有录到播放声音，重新播放识别')
        audio = downsample_48k(mono)
        np.save(self.run_dir / 'last-audio.npy', audio)
        try:
            return self.solver.hear(audio, sorted(self.words))
        except RuntimeError as error:
            if '听力识别不可靠' in str(error) or '听力转写不在' in str(error):
                raise RetryObservation(str(error)) from error
            raise

    def green_region(self, im, top, left_only=False):
        import cv2
        rgb = np.asarray(im).astype(float)
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        mask = ((g > 115) & (g > r * 1.5) & (g > b * 1.3)).astype('uint8') * 255
        mask[int(top):] = 0
        if left_only:
            mask[:, int(im.width * .3):] = 0
        mask = cv2.dilate(mask, np.ones((3, 7), np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        regions = [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) > 60]
        if not regions:
            return None
        x, y, w, h = max(regions, key=lambda r: r[2] * r[3])
        return x, y, w, h

    def learn_feedback(self, im, items=None):
        markers=feedback_markers(im)
        if markers is None:
            # During a short incorrect-answer animation, neighboring option
            # outlines may not all be visible. A large red selected rectangle
            # is still explicit error feedback, even without four contours.
            if self.last_submission is not None:
                import cv2
                rgb=np.asarray(im.convert('RGB')).astype(float)
                r,g,b=rgb[...,0],rgb[...,1],rgb[...,2]
                red=((r>160)&(r>g*1.5)&(r>b*1.2)).astype('uint8')*255
                red[:int(im.height*.2)]=0
                contours,_=cv2.findContours(red,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
                if any(w>im.width*.5 and h>25 for x,y,w,h in (cv2.boundingRect(c) for c in contours)):
                    self.memory.feedback(self.last_submission['key'],False)
                    self.last_question=None
                    self.record('wrong_option_excluded',source='red_feedback_animation')
            return
        row=self.last_submission
        if row is not None and row['chosen'] in markers['wrong']:
            self.memory.feedback(row['key'],False)
            self.last_question=None
            self.record('wrong_option_excluded',choice=row['chosen']+1)
        if len(markers['correct'])!=1:
            return
        index=markers['correct'][0]
        failed_review=self.after_failure_card or bool(markers['starred'] and markers['wrong'])
        if row is None and items is not None:
            top=markers['boxes'][0][1]
            sentence=' '.join(t.text for t in items if t.center[1]<top and
                              re.search(r'[A-Za-z]{3,}',t.text))
            if not sentence:
                return
            choices=[]
            for x,y,w,h in markers['boxes']:
                parts=sorted([t for t in items if x<=t.center[0]<=x+w and y<=t.center[1]<=y+h],
                             key=lambda t:(t.center[1],t.center[0]))
                choices.append(' '.join(t.text for t in parts))
            if not all(choices):
                return
            active=self.memory.data.get('active')
            known=self.memory.data['questions'].get(active,{})
            english=lambda text:re.findall(r'[a-z]+',text.split('\n目标单词：')[0].lower())
            key=active if english(known.get('sentence',''))==english(sentence) else None
            row={'sentence':known.get('sentence',sentence) if key else sentence,
                 'choices':choices,'key':key,'chosen':None}
        if row is None:
            return
        if row['key'] is not None:
            if failed_review:
                self.memory.observe_failed_review(row['key'],[row['choices'][i] for i in markers['wrong']])
            elif row['chosen'] is not None:
                self.memory.feedback(row['key'],index==row['chosen'])
        self.solver.learn_feedback(row['sentence'],row['choices'][index])
        self.record('verified_feedback',correct_choice=index+1,chosen=None if row['chosen'] is None else row['chosen']+1,
                    source='green_star_or_fill',after_two_failures=failed_review)
        self.last_submission=None
        self.after_failure_card=False

    def handle(self, im, items):
        if loading_overlay(im):
            if self.loading_since is None:
                self.loading_since=time.monotonic()
                self.record('waiting_for_loading',source='visual_spinner')
            if time.monotonic()-self.loading_since > 120:
                raise RuntimeError('页面加载超过120秒，已保存现场并暂停')
            time.sleep(.3)
            return False
        close_popup=next((t for t in items if compact(t.text)=='关闭错题弹出'),None)
        open_popup=next((t for t in items if compact(t.text)=='打开错题弹出'),None)
        if page_kind(items)=='failure_card' or close_popup or open_popup:
            from card_controls import gear_point,close_point
            self.after_failure_card=True
            self.card_setting_attempts+=1
            if self.card_setting_attempts>10:
                raise RuntimeError('关闭错题弹出设置未能确认或卡片未关闭，已保存现场')
            if close_popup:
                self.card_popups_disabled=False
                self.record('disable_wrong_card_popups')
                self.click(close_popup)
            elif open_popup:
                # This is an action label: "open" means popups are currently OFF.
                self.card_popups_disabled=True
                self.record('wrong_card_popups_disabled',confirmed_label='打开错题弹出')
                self.click(close_point(im))
            elif self.card_popups_disabled:
                self.record('close_disabled_failure_card')
                self.click(close_point(im))
            else:
                self.record('open_failure_card_settings')
                self.click(gear_point(im))
            return False
        self.card_setting_attempts=0
        self.card_popups_disabled=False
        # Dismiss observed informational overlays before considering background page.
        if page_kind(items) == 'checkin_notice':
            notice = self.find(items, '我知道了')
            if notice is None:
                raise RuntimeError('识别到打卡弹窗，但未找到关闭按钮，已暂停')
            if self.notice_attempts >= 3:
                raise RuntimeError('打卡弹窗关闭3次后仍存在，已暂停')
            self.notice_attempts += 1
            self.record('dismiss_checkin_notice')
            self.click(notice)
            # The next loop captures a new screen; background learning actions
            # are allowed only once the overlay is no longer observed.
            return False
        self.notice_attempts = 0
        # A question with a Continue button is showing its answer/translation.
        # Handle feedback before question classification; never answer it again.
        continuation = self.find(items, '继续')
        question_options = options(items)
        if question_options and not any(compact(t.text) == '词义' for t in items):
            import cv2
            rgb = np.asarray(im.convert('RGB')).astype(float)
            r, g, b = rgb[...,0], rgb[...,1], rgb[...,2]
            colored = (((g > 120) & (g > r*1.5) & (g > b*1.2)) |
                       ((r > 160) & (r > g*1.5) & (r > b*1.2))).astype('uint8')*255
            colored[:int(im.height*.2)] = 0
            colored[int(im.height*.85):] = 0
            contours, _ = cv2.findContours(colored,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            feedback = any(w > im.width*.45 and h > 25
                           for x,y,w,h in (cv2.boundingRect(c) for c in contours))
            markers=feedback_markers(im)
            marked=markers is not None and (markers['correct'] or markers['wrong'])
            if continuation or feedback or marked:
                self.learn_feedback(im,items)
                if self.feedback_since is None:
                    self.feedback_since = time.monotonic()
                if continuation:
                    self.record('continue_after_feedback')
                    self.click(continuation)
                    self.last_question = None
                    self.audio_encounter=None
                elif time.monotonic()-self.feedback_since > 120:
                    raise RuntimeError('答案反馈已出现，但继续按钮等待超过120秒')
                else:
                    time.sleep(1)
                return False
        self.feedback_since = None
        text = '\n'.join(t.text for t in items)
        kind = page_kind(items)
        if kind == 'loading':
            if self.loading_since is None:
                self.loading_since = time.monotonic()
                self.record('waiting_for_loading')
            if time.monotonic() - self.loading_since > 120:
                raise RuntimeError('页面加载超过120秒，已保存现场并暂停')
            time.sleep(1)
            return False
        self.loading_since = None
        if kind != 'unknown':
            self.unknown_since = None
        values = numbers(text)
        self.record('page', kind=kind, values=values)
        if kind == 'task_list':
            rows=task_rows(items)
            unfinished=[(title,score) for title,score in rows if score<100]
            if not unfinished:
                signature=tuple((t.text,score) for t,score in rows)
                if not rows:raise RetryObservation('任务列表单元及得分暂未可靠识别')
                if self.uia and hasattr(self.bg,'invoke'):
                    if signature==self.task_scroll_signature:
                        raise RuntimeError('任务列表滚动后内容未变化，已暂停以避免遗漏单元')
                    self.task_scroll_signature=signature
                    result=self.bg.invoke('scroll-down')
                    self.record('task_list_scroll',result=result)
                    if result!='SCROLL_END':return False
                self.record('task_list_no_visible_unfinished',recognized=len(rows))
                return True
            title,score=unfinished[0]
            self.total=None;self.rounds=0;self.stagnant=0;self.last_score=None
            self.words.clear();self.last_question=None;self.audio_encounter=None
            self.leaving_completed_unit=False
            self.task_scroll_signature=None
            self.record('open_unfinished_unit',title=title.text,score=score)
            self.click(title)
        elif kind == 'unit':
            if 'score' not in values or values.get('total',0)<=0:
                return self.wait_unit_ready('单词总数或得分尚未加载完成')
            button = self.find(items, '重新选词') or self.find(items, '开始选词')
            if values['score']<100 and not self.leaving_completed_unit and button is None:
                return self.wait_unit_ready('等待开始选词或重新选词按钮出现')
            self.unit_ready_since=None
            self.total = values['total']
            score = values['score']
            if not 0 <= score <= 100:
                raise RuntimeError('单元得分超出范围')
            self.checkpoint.write_text(json.dumps({'score': score, 'total': self.total,
                                                   'rounds': self.rounds}, indent=2), encoding='utf-8')
            if score == 100 or self.leaving_completed_unit:
                self.record('complete', score=score)
                back=self.find(items,'返回')
                if back is None:raise RuntimeError('已完成单元未找到返回任务列表按钮')
                self.click(back)
                return False
            if self.last_score is not None:
                self.stagnant = self.stagnant + 1 if score <= self.last_score else 0
            if self.stagnant >= self.cfg['max_stagnant_rounds']:
                raise RuntimeError('多轮得分未提升，已停止重试')
            if self.rounds >= self.cfg['max_rounds']:
                raise RuntimeError('达到本次重练轮次上限')
            self.last_score = score
            self.words.clear()
            self.click(button)
        elif kind == 'select':
            self.total = self.total or self.cfg.get('expected_words')
            if not self.total:
                raise RuntimeError('请从单元详情页开始，以读取实际单词总数')
            selected = values.get('selected')
            if selected is None or selected > self.total:
                raise RetryObservation('选词数量暂未可靠识别')
            labels = word_items(items, im.height)
            if all_badges_ten(im,labels,self.total):
                self.record('complete_by_word_badges',count=len(labels))
                self.leaving_completed_unit=True
                back=self.find(items,'返回')
                if back is None:raise RuntimeError('所有单词得分10，未找到选词页返回按钮')
                self.click(back)
                return False
            if len(labels)==self.total:
                self.words={t.text.strip() for t in labels}
            else:
                self.words.update(t.text.strip() for t in labels)
            rgb = np.asarray(im)
            unselected = [t for t in labels if not selected_green(rgb, t)]
            if unselected:
                if self.uia and hasattr(self.bg,'click_many'):
                    # Only word toggles are batched. Recheck their actual fill
                    # between chunks; never reuse this path for answers.
                    for start in range(0,len(unselected),5):
                        self.guard()
                        chunk=unselected[start:start+5]
                        current=self.capture()
                        if current.size!=im.size:raise LayoutChanged('选词期间窗口大小变化')
                        remaining=[t for t in chunk if not selected_green(np.asarray(current),t)]
                        if remaining:
                            self.bg.click_many([t.center for t in remaining])
                    self.record('words_selected_batch',count=len(unselected))
                else:
                    self.click(unselected[0])
                return False
            if selected != self.total:
                raise RuntimeError(f'当前已选{selected}/{self.total}，可能需要滚动；已暂停以避免漏选')
            label = next((t for t in items if '只做错题' in t.text), None)
            if label is None:
                raise RetryObservation('暂未定位只做错题选项')
            checked, point = checkbox_checked(rgb, label)
            if not checked:
                self.click(point)
                return False
            self.record('selection_ready', count=selected, only_wrong=True)
            (ROOT/'unit_vocabulary.json').write_text(json.dumps(sorted(self.words),ensure_ascii=False),encoding='utf-8')
            self.click(self.find(items, '开始练习'))
            self.memory.begin_round()
            self.rounds += 1
            self.last_question = None
        elif kind == 'familiar':
            continuation=self.find(items,'继续')
            if continuation is None:
                if self.familiar_wait_since is None:
                    self.familiar_wait_since=time.monotonic()
                    self.record('waiting_for_familiar_ready')
                if time.monotonic()-self.familiar_wait_since>120:
                    raise RuntimeError('单词释义卡片等待继续按钮超过120秒')
                return False
            self.familiar_wait_since=None
            self.words.update(t.text for t in items if
                              re.fullmatch(r'[A-Za-z]+(?:[-\x27][A-Za-z]+)*', t.text.strip())
                              and t.center[1] < im.height * .3)
            (self.run_dir / 'vocabulary.json').write_text(json.dumps(sorted(self.words), ensure_ascii=False), encoding='utf-8')
            self.click(continuation)
        elif kind in ('sentence', 'listening'):
            opts = options(items)
            top = min(t.center[1] for t in opts)
            sentence = ' '.join(t.text for t in items if t.center[1] < top and
                                t.text not in ('返回', '播放'))
            # Include the highlighted word's pixels: repeated word senses can otherwise
            # have identical OCR text and options, yet ask about a different target.
            pixels = im.crop((0, 0, im.width, int(top))).resize((160, 80)).tobytes()
            signature = hashlib.sha256((sentence + json.dumps([t.text for t in opts])).encode() + pixels).hexdigest()
            if signature == self.last_question:
                if time.monotonic()-self.last_question_time < self.cfg.get('no_feedback_seconds',20):
                    return False
            heard = ''
            if kind == 'listening':
                play = self.find(items, '播放')
                if play is None:
                    region = self.green_region(im, top - 15, left_only=True)
                    if region is None:
                        raise RetryObservation('暂未定位听力播放按钮')
                    x, y, w, h = region
                    play = Text('播放', 1, [[x,y],[x+w,y],[x+w,y+h],[x,y+h]])
                heard = self.listen(play)
                sentence += '\n听到单词：'+heard
                self.record('heard_word',word=heard)
                # Playback can auto-advance. Reobserve before clicking an answer.
                fresh = self.capture()
                fresh_items = self.read(fresh)
                fresh_opts = options(fresh_items)
                from difflib import SequenceMatcher
                from question_memory import meaning_key
                same_options=len(fresh_opts)==len(opts)==4 and all(
                    SequenceMatcher(None,meaning_key(a.text),meaning_key(b.text)).ratio()>=.75
                    for a,b in zip(opts,fresh_opts))
                if not same_options:
                    self.record('listening_options_changed',before=[t.text for t in opts],after=[t.text for t in fresh_opts])
                    raise RetryObservation('录音后选项尚未稳定，重新观察题目')
                opts = fresh_opts
            else:
                region = self.green_region(im, top - 15)
                if region is None:
                    raise RetryObservation('暂未识别到句意题标绿单词')
                x, y, w, h = region
                patch = np.asarray(im.convert('RGB'))[y:y+h,x:x+w].astype(float)
                r, g, b = patch[...,0], patch[...,1], patch[...,2]
                ink = (g > 110) & (g > r * 1.5) & (g > b * 1.3)
                # The link-like underline must not be joined to the letters.
                ink[ink.mean(axis=1) > .65] = False
                clean = np.full((h+32,w+32,3),255,dtype=np.uint8)
                clean[16:h+16,16:w+16][ink] = 0
                target_result, _ = self.ocr(clean)
                if not target_result:
                    # Retry the observed word crop at larger scale before stopping.
                    target_result, _ = self.ocr(np.asarray(Image.fromarray(clean).resize((clean.shape[1]*3,clean.shape[0]*3))))
                target = [Text(str(t),float(s),box) for box,t,s in target_result or [] if float(s)>=.65]
                if not target:
                    # A single cropped word does not need text-box detection;
                    # tiny/thin glyphs can otherwise be missed by the detector.
                    if self.word_ocr is None:
                        self.word_ocr=RapidOCR(use_text_det=False,use_angle_cls=False)
                    raw,_=self.word_ocr(clean)
                    target=[Text(str(t),float(s),box) for box,t,s in raw or []
                            if float(s)>=.5 and re.fullmatch(r"[A-Za-z]+(?:[-'][A-Za-z]+)*",str(t).strip())]
                if not target:
                    raise RetryObservation('标绿单词暂未可靠识别')
                sentence += '\n目标单词：' + ' '.join(t.text for t in target)
                self.last_image = im
            all_choices=[t.text for t in opts]
            key=question_key(sentence,heard,all_choices)
            if kind=='listening':
                from question_memory import meaning_key
                option_set=sorted(meaning_key(t) for t in all_choices)
                if self.audio_encounter and self.audio_encounter['options']==option_set:
                    key=self.audio_encounter['key']
                else:
                    self.audio_encounter={'options':option_set,'key':key}
            saved=self.memory.data['questions'].get(key)
            if saved and saved['pending'] is not None:
                age=time.time()-saved['history'][-1]['time']
                if age < self.cfg.get('no_feedback_seconds',20):
                    return False
                self.memory.no_feedback(key)
                self.record('wrong_option_excluded',source='no_feedback_timeout',question=key)
                self.last_question=None
                if self.memory.exhausted(key):
                    raise RuntimeError('两次提交后仍无反馈，已记录错误；禁止第三次提交，请检查单词卡片或页面')
            available=self.memory.available(key,sentence,all_choices)
            reduced=[all_choices[i] for i in available]
            chosen=available[self.solver.answer(sentence,reduced,heard)]
            self.record('answer', sentence=sentence, heard=heard, choices=[t.text for t in opts], choice=chosen + 1,
                        decision=self.solver.last_decision)
            self.last_question = signature
            self.last_question_time = time.monotonic()
            # Check coordinates before reserving; save before input so a crash
            # cannot silently reset the maximum number of submissions.
            self.guard()
            if not self.uia and (self.window.left,self.window.top)!=self.origin:
                raise LayoutChanged('窗口移动，重新识别')
            self.last_submission={'sentence':sentence,'choices':all_choices,'chosen':chosen,'key':key}
            self.memory.reserve(key,all_choices[chosen],self.last_submission)
            self.click(opts[chosen],settle=False)
            # Incorrect choices can flash red and reset before a normal OCR
            # cycle finishes. Inspect pixels immediately, without running OCR.
            feedback_deadline=time.monotonic()+self.cfg.get('feedback_poll_seconds',1.0)
            while time.monotonic()<feedback_deadline:
                feedback_image=self.capture()
                self.last_image=feedback_image
                previous=self.memory.data['questions'][key]['pending']
                self.learn_feedback(feedback_image)
                if self.memory.data['questions'][key]['pending'] is None and previous is not None:
                    if not self.memory.data['questions'][key]['solved']:
                        self.last_question=None
                    break
                time.sleep(.02)
        else:
            for label in ('下一题', '完成练习', '查看成绩', '返回单元', '继续'):
                button = self.find(items, label)
                if button:
                    self.click(button)
                    return False
            if self.unknown_since is None:
                self.unknown_since = time.monotonic()
            if time.monotonic() - self.unknown_since < 20:
                return False
            raise RetryObservation('页面暂未识别，重新截图识别')
        return False

    def run(self):
        if self.background and not self.uia and not self.cfg.get('background_input_verified',False):
            raise RuntimeError('后台截图成功，但当前微信未通过后台点击测试；已禁止答题，避免将无效点击记为答错。可用 --probe-background 单独检查截图。')
        from local_solver import LocalSolver
        self.solver = LocalSolver(ROOT, self.cfg)
        try:
            self.solver.start()
            # Validate speech model now, before starting any task.
            if not (ROOT / self.cfg['whisper_model'] / 'model.bin').exists():
                raise RuntimeError('缺少本地听力模型')
            self.select_window()
            deadline = time.monotonic() + 4 * 3600
            moved = 0
            missing_target = 0
            recovery_since=None
            recovery_attempts=0
            while time.monotonic() < deadline:
                try:
                    im = self.capture()
                    try:
                        items = self.read(im)
                    except (ValueError,RuntimeError) as error:
                        raise RetryObservation('OCR暂时失败：'+str(error)) from error
                    if self.handle(im, items):
                        return
                    moved = 0
                    missing_target = 0
                    recovery_since=None
                    recovery_attempts=0
                except RetryObservation as error:
                    if recovery_since is None:recovery_since=time.monotonic()
                    recovery_attempts+=1
                    self.record('retry_observation',reason=str(error),attempt=recovery_attempts)
                    self.ocr_frame_key=None
                    if time.monotonic()-recovery_since>45:
                        raise RuntimeError('自动重新识别45秒仍未恢复：'+str(error)) from error
                    time.sleep(min(.15*recovery_attempts,.8))
                except UIABatchPartial:
                    if page_kind(items)!='select':raise
                    missing_target+=1
                    self.record('reobserve_partial_word_batch',attempt=missing_target)
                    if missing_target>=3:raise
                except UIATargetUnavailable:
                    # Only retry navigation/selection: never repeat an answer submission.
                    if page_kind(items) not in ('select','familiar','failure_card','unit'):
                        raise
                    missing_target += 1
                    self.record('reobserve_missing_uia_target',attempt=missing_target)
                    if missing_target >= 3:
                        raise
                except LayoutChanged as error:
                    moved += 1
                    self.record('reobserve_after_move')
                    self.last_question = None
                    if moved >= 3:
                        raise RuntimeError('窗口连续移动3次，请固定窗口后重新运行') from error
                time.sleep(self.cfg.get('loop_seconds',.1))
            raise RuntimeError('达到本次运行时间上限')
        finally:
            if self.last_image is not None:
                self.last_image.save(self.run_dir / 'last-screen.png')
            self.solver.close()


def main():
    parser = argparse.ArgumentParser(description='词达人本地离线脚本')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--analyze', type=Path, help='识别截图或文件夹，不操作桌面')
    group.add_argument('--run', action='store_true', help='处理当前单元，得分100后停止')
    group.add_argument('--probe-background',action='store_true',help='只测试后台截图，不提交答案')
    group.add_argument('--startup-check',action='store_true',help='仅验证模型启动和停止，不操作微信')
    parser.add_argument('--background',action='store_true',help='实验性后台窗口操作，不激活窗口或移动鼠标')
    parser.add_argument('--uia',action='store_true',help='UI Automation直接调用，可能激活微信但不移动鼠标')
    args = parser.parse_args()
    cfg = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    if args.background or args.probe_background:cfg['background']=True
    if args.uia:cfg['input_backend']='uia'
    if args.startup_check:
        from local_solver import LocalSolver
        solver=LocalSolver(ROOT,cfg)
        try:
            with RunLock(ROOT/'runs/runner.lock'):
                solver.start()
                print(json.dumps({'event':'model_ready'}),flush=True)
                while True:check_controls(ROOT);time.sleep(.1)
        except KeyboardInterrupt:return 0
        finally:solver.close()
    runner = Runner(cfg)
    if args.probe_background:
        runner.select_window()
        image=runner.capture()
        image.save(runner.run_dir/'background-probe.png')
        items=runner.read(image)
        print('Background capture:',page_kind(items),'Output:',runner.run_dir/'background-probe.png')
        return 0
    if args.analyze:
        files = sorted(args.analyze.glob('*.png')) if args.analyze.is_dir() else [args.analyze]
        reports = []
        for path in files:
            im = Image.open(path).convert('RGB')
            items = runner.read(im)
            words = word_items(items, im.height)
            row = {'file': path.name, 'kind': page_kind(items),
                   'numbers': numbers('\n'.join(t.text for t in items)),
                   'options': [t.text for t in options(items)],
                   'words': [{'text': t.text, 'selected': selected_green(np.asarray(im), t)} for t in words],
                   'ocr': [{'text': t.text, 'score': t.score, 'box': t.box} for t in items]}
            reports.append(row)
            print(path.name, row['kind'], row['numbers'], 'options=', len(row['options']),
                  'words=', len(words), 'selected=', sum(t['selected'] for t in row['words']))
        output = ROOT / 'runs/analysis.json'
        output.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        try:
            with RunLock(ROOT/'runs/runner.lock'):
                runner.run()
        except KeyboardInterrupt:
            runner.record('stopped',reason='手动停止')
            return 0
        except Exception as error:
            runner.record('paused', reason=str(error))
            print('暂停，现场目录:', runner.run_dir)
            return 1
    return 0


if __name__ == '__main__':
    if sys.platform == 'win32':
        ctypes.windll.user32.SetProcessDPIAware()
    raise SystemExit(main())
