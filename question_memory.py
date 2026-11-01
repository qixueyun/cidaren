"""Durable wrong-option exclusion and a two-attempt limit per encounter."""
import hashlib
import json
from pathlib import Path
import re
import time


def meaning_key(text):
    return re.sub(r'[\W_]+', '', text.lower())


def question_key(sentence, heard='', choices=None):
    if heard:
        data = 'listening:' + ' '.join(re.findall(r'[a-z]+', heard.lower()))
        if choices:
            data += ':' + '|'.join(sorted(meaning_key(t) for t in choices))
    else:
        # Includes target word after the sentence, so two highlighted words in
        # the same sentence are distinct. Chinese UI labels are ignored.
        data = 'sentence:' + ' '.join(re.findall(r'[a-z]+', sentence.lower()))
    return hashlib.sha256(data.encode()).hexdigest()


class QuestionMemory:
    def __init__(self, path):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {'active': None, 'questions': {}}

    def save(self):
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(self.path)

    def available(self, key, sentence, choices):
        row = self.data['questions'].setdefault(key, {
            'sentence': sentence, 'wrong': [], 'history': [], 'consecutive': 0,
            'pending': None, 'solved': False})
        if row['solved']:
            raise RuntimeError('已做对题目再次出现，可能识别冲突，已暂停')
        if self.data['active'] != key:
            row['consecutive'] = 0
            self.data['active'] = key
        if row['pending'] is not None:
            raise RuntimeError('上一提交结果尚未确认，不重复点击或消耗第二次机会')
        if row['consecutive'] >= 2:
            raise RuntimeError('同题已连续尝试2次，已暂停，禁止第三次提交')
        self.save()
        available = [i for i, text in enumerate(choices) if meaning_key(text) not in row['wrong']]
        if not available:
            raise RuntimeError('没有可用选项，已暂停')
        return available

    def reserve(self, key, meaning, submission=None):
        row = self.data['questions'][key]
        if row['pending'] is not None or row['consecutive'] >= 2:
            raise RuntimeError('禁止重复提交或第三次尝试')
        if meaning_key(meaning) in row['wrong']:
            raise RuntimeError('禁止提交已确认错误的选项')
        row['consecutive'] += 1
        row['pending'] = meaning
        row['submission'] = submission
        row['history'].append({'time': time.time(), 'meaning': meaning, 'status': 'pending'})
        self.save()

    def pending_submission(self):
        key=self.data.get('active')
        row=self.data['questions'].get(key,{})
        return row.get('submission') if row.get('pending') is not None else None

    def feedback(self, key, correct):
        row = self.data['questions'][key]
        if row['pending'] is None:
            return
        meaning = row['pending']
        if correct:
            row['solved'] = True
        elif meaning_key(meaning) not in row['wrong']:
            row['wrong'].append(meaning_key(meaning))
        row['history'][-1]['status'] = 'correct' if correct else 'wrong'
        row['pending'] = None
        self.save()

    def exhausted(self, key):
        row = self.data['questions'][key]
        return row['consecutive'] >= 2 and not row['solved']

    def no_feedback(self,key):
        row=self.data['questions'][key]
        if row['pending'] is None:
            return
        self.feedback(key,False)
        row['history'][-1]['source']='assumed_wrong_no_feedback_user_rule'
        self.save()

    def begin_round(self):
        self.data['active']=None
        self.save()

    def observe_failed_review(self,key,wrong_meanings):
        row=self.data['questions'].get(key)
        if row is None:
            return
        for meaning in wrong_meanings:
            normalized=meaning_key(meaning)
            if normalized not in row['wrong']:
                row['wrong'].append(normalized)
        if row['pending'] is not None:
            row['history'][-1]['status']='wrong_after_two_failure_card'
        row['pending']=None
        row['consecutive']=2
        self.save()
