"""Offline task-row and completed-word recognition."""
import re
from pathlib import Path
import cv2
import numpy as np
from offline_core import compact

def task_rows(items):
    titles=sorted([t for t in items if re.search(r'List\s*\d+',t.text,re.I)],key=lambda t:t.center[1])
    rows=[]
    for i,title in enumerate(titles):
        previous=titles[i-1].center[1] if i else title.center[1]-180
        low=(previous+title.center[1])/2
        scores=[]
        for t in items:
            match=re.search(r'(?<!单元)得分[:：]?(\d+(?:\.\d+)?)',compact(t.text))
            if match and low<t.center[1]<=title.center[1]+20:
                scores.append(float(match[1]))
        if len(scores)==1:rows.append((title,scores[0]))
    return rows

def all_badges_ten(image,words,total):
    if len(words)!=total:return False
    template=cv2.imread(str(Path(__file__).parent/'assets/badge-ten.png'),0)
    if template is None:return False
    gray=cv2.cvtColor(np.asarray(image.convert('RGB')),cv2.COLOR_RGB2GRAY)
    for word in words:
        left=min(p[0] for p in word.box);right=max(p[0] for p in word.box)
        top=min(p[1] for p in word.box)
        crop=gray[max(0,int(top-55)):int(top+14),max(0,int(right-35)):min(image.width,int(right+70))]
        matched=False
        for size in range(21,44,2):
            if min(crop.shape)<size:continue
            result=cv2.matchTemplate(crop,cv2.resize(template,(size,size)),cv2.TM_CCOEFF_NORMED)
            if cv2.minMaxLoc(result)[1]>=.77:
                matched=True;break
        if not matched:return False
    return True
