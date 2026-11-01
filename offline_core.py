"""Pure perception/planning functions. No desktop actions or network access."""
import re
from dataclasses import dataclass


@dataclass
class Text:
    text: str
    score: float
    box: list
    role: str = ''

    @property
    def center(self):
        return tuple(sum(p[i] for p in self.box) / len(self.box) for i in (0, 1))


def compact(s):
    return re.sub(r"\s+", "", s)


def loading_overlay(image):
    """Recognize the central blue spinner, which has no OCR loading label."""
    import numpy as np
    import cv2
    rgb = np.asarray(image.convert('RGB')).astype(float)
    h, w = rgb.shape[:2]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mask = ((b > 200) & (b > r * 1.35) & (g > 90) & (g < 220)).astype('uint8')
    count, _, stats, centers = cv2.connectedComponentsWithStats(mask)
    for i in range(1, count):
        x, y, sw, sh, area = stats[i]
        cx, cy = centers[i]
        if (.35*w < cx < .65*w and .3*h < cy < .7*h and
                25 < sw < w*.2 and 25 < sh < h*.15 and
                .35 < sw/sh < 2.8 and 80 < area < sw*sh*.65):
            return True
    return False


def numbers(text):
    result = {}
    for key, pattern in {
        "total": r"单词总数[:：]?(\d+)",
        "selected": r"已选[:：]?(\d+)",
        "score": r"单元得分[:：]?(\d+(?:\.\d+)?)",
    }.items():
        m = re.search(pattern, compact(text))
        if m:
            result[key] = float(m[1]) if key == "score" else int(m[1])
    return result


def page_kind(items):
    text = "".join(compact(t.text) for t in items)
    if '打卡成功' in text and ('我知道了' in text or '打卡奖励' in text):
        return 'checkin_notice'
    if '加载中' in text:
        return 'loading'
    if '用法' in text and '例句' in text and '下一题' in text:
        return 'failure_card'
    if "选择单词" in text and ("开始练习" in text or "已选" in text):
        return "select"
    if re.search(r'List\d+',text,re.I) and '得分' in text and ('学习任务' in text or '结束时间' in text):
        return 'task_list'
    if "单元得分" in text and "单词总数" in text:
        return "unit"
    if "词义" in text and ("继续" in text or "查看详细释义" in text):
        return "familiar"
    # Four part-of-speech definitions are present in both supplied question types.
    if len(options(items)) == 4:
        top = options(items)[0].center[1]
        english = ' '.join(t.text for t in items if t.center[1] < top)
        return "sentence" if len(re.findall(r'\b[A-Za-z]{2,}\b', english)) >= 4 else "listening"
    return "unknown"


def options(items):
    return sorted([t for t in items if t.role == 'option' or re.match(
        r"^(?:adj|adv|prep|pron|conj|num|int|aux|art|phr|vt|vi|ad|n|v|a)\s*(?:[.．。]|(?=[\u4e00-\u9fff（(]))", t.text.strip(), re.I
    )], key=lambda t: t.center[1])


def word_items(items, height):
    return [t for t in items if re.fullmatch(r"[A-Za-z]+(?:[-'][A-Za-z]+)*", t.text.strip())
            and height * .12 < t.center[1] < height * .94]


def selected_green(rgb, item):
    """Sample inside the text box, where selected capsules have solid green fill."""
    import numpy as np
    points = np.asarray(item.box)
    x0, y0 = np.floor(points.min(axis=0)).astype(int)
    x1, y1 = np.ceil(points.max(axis=0)).astype(int)
    patch = rgb[max(0, y0):y1 + 1, max(0, x0):x1 + 1, :3].astype(float)
    if not patch.size:
        return False
    r, g, b = patch[..., 0], patch[..., 1], patch[..., 2]
    return float(((g > 110) & (g > r * 1.3) & (g > b * 1.12)).mean()) > .25


def checkbox_checked(rgb, label):
    """Checkbox is left of the observed label, not at a fixed screen coordinate."""
    import numpy as np
    p = np.asarray(label.box)
    size = max(12, int(p[:, 1].max() - p[:, 1].min()))
    x = int(p[:, 0].min() - size * 1.2)
    y = int(label.center[1])
    patch = rgb[max(0, y-size):y+size, max(0, x-size):x+size, :3].astype(float)
    if not patch.size:
        return False, (x, y)
    blue = (patch[..., 2] > 130) & (patch[..., 0] < 110) & (patch[..., 1] > 75)
    return float(blue.mean()) > .12, (x, y)
