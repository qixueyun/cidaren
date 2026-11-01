"""Locate card-only icons using the user's observed gear and red close circle."""
from pathlib import Path
import cv2
import numpy as np

def gear_point(image):
    template=cv2.imread(str(Path(__file__).parent/'assets/card-gear.png'),cv2.IMREAD_GRAYSCALE)
    if template is None:raise RuntimeError('缺少单词卡片齿轮模板')
    gray=cv2.cvtColor(np.asarray(image.convert('RGB')),cv2.COLOR_RGB2GRAY)
    height,width=gray.shape
    left=int(width*.65);bottom=min(max(int(height*.22),100),220)
    region=gray[:bottom,left:]
    best=(-1,None)
    for size in range(25,76,2):
        if min(region.shape)<size:continue
        resized=cv2.resize(template,(size,size))
        _,score,_,point=cv2.minMaxLoc(cv2.matchTemplate(region,resized,cv2.TM_CCOEFF_NORMED))
        if score>best[0]:best=(score,(left+point[0]+size/2,point[1]+size/2))
    if best[0]<.7:raise RuntimeError('未可靠定位单词卡片右上角齿轮')
    return best[1]

def close_point(image):
    rgb=np.asarray(image.convert('RGB')).astype(float)
    h,w=rgb.shape[:2]
    r,g,b=rgb[...,0],rgb[...,1],rgb[...,2]
    mask=((r>170)&(r>g*1.6)&(r>b*1.6)).astype('uint8')
    mask[min(max(int(h*.22),100),220):]=0;mask[:,:int(w*.85)]=0
    count,_,stats,_=cv2.connectedComponentsWithStats(mask)
    candidates=[]
    for x,y,sw,sh,area in stats[1:]:
        if 18<sw<85 and 18<sh<85 and .7<sw/sh<1.4:
            candidates.append((x+sw/2,y+sh/2))
    if len(candidates)!=1:raise RuntimeError('未可靠定位单词卡片右上角关闭按钮')
    return candidates[0]
