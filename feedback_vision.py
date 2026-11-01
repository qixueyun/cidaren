"""Read answer markers from observed option rectangles, including green stars."""
def feedback_markers(image):
    import cv2
    import numpy as np
    rgb=np.asarray(image.convert('RGB'))
    height,width=rgb.shape[:2]
    contours,_=cv2.findContours(cv2.Canny(rgb,40,100),cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    boxes=[]
    for contour in contours:
        x,y,w,h=cv2.boundingRect(contour)
        if w>width*.5 and 35<h<height*.2 and y>height*.12 and y+h<height*.96:
            if not any(abs(y-yy)<8 for xx,yy,ww,hh in boxes):
                boxes.append((x,y,w,h))
    boxes.sort(key=lambda box:box[1])
    if len(boxes)!=4:
        return None
    green,red,starred=[],[],[]
    for index,(x,y,w,h) in enumerate(boxes):
        patch=rgb[y+4:y+h-4,x+4:x+w-4].astype(float)
        r,g,b=patch[...,0],patch[...,1],patch[...,2]
        greens=(g>120)&(g>r*1.5)&(g>b*1.2)
        reds=(r>160)&(r>g*1.5)&(r>b*1.2)
        # The correct answer may be indicated only by a small green star
        # at the right edge, with the remainder of the option unfilled.
        right=greens[:,int(greens.shape[1]*.82):]
        if greens.mean()>.5 or int(right.sum())>15:
            green.append(index)
            if greens.mean()<=.5:
                starred.append(index)
        if reds.mean()>.4:
            red.append(index)
    return {'boxes':boxes,'correct':green,'wrong':red,'starred':starred}
