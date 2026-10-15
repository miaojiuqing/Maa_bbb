"""战后蓝色传送锚点的补充检测；只用于靠近展开，不据此认定门的体系。"""
import numpy as np
from PIL import Image, ImageFilter


def dormant_anchors(frame):
    b, g, r = (frame[:, :, i].astype(np.int16) for i in range(3))
    mask = (b>175)&(g>115)&(r<180)&(b-r>65)&(g-r>25)
    mask[:160]=False;mask[470:]=False;mask[:,:80]=False;mask[:,1100:]=False
    mask=np.array(Image.fromarray(mask.astype(np.uint8)*255).filter(ImageFilter.MaxFilter(5)))>0
    components=[]
    for y,x in np.argwhere(mask):
        if not mask[y,x]:continue
        stack=[(int(y),int(x))];mask[y,x]=False
        left=right=int(x);top=bottom=int(y);area=0
        while stack:
            yy,xx=stack.pop();area+=1
            left=min(left,xx);right=max(right,xx);top=min(top,yy);bottom=max(bottom,yy)
            for ny,nx in ((yy-1,xx),(yy+1,xx),(yy,xx-1),(yy,xx+1)):
                if 0<=ny<720 and 0<=nx<1280 and mask[ny,nx]:
                    mask[ny,nx]=False;stack.append((ny,nx))
        w,h=right-left+1,bottom-top+1
        if 25<=w<=190 and 5<=h<=55 and w/h>=1.7 and area>=70:
            components.append({"box":[left,top,w,h],"area":area})
    groups=[]
    for item in components:
        x,y,w,h=item["box"]
        group=[i for i in components if abs(i["box"][1]+i["box"][3]/2-y-h/2)<=42]
        if 3<=len(group)<=4:
            group.sort(key=lambda i:i["box"][0])
            if all(45<=group[j+1]["box"][0]-group[j]["box"][0]<=400 for j in range(len(group)-1)):
                groups.append(group)
    return max(groups,key=lambda g:sum(i["area"] for i in g)) if groups else []


def red_portals(frame):
    """新版红紫色强敌门：颜色只引导靠近，交互前仍须游戏文字确认。"""
    b,g,r=(frame[:,:,i].astype(np.int16) for i in range(3))
    masks=[(r>65)&(b>40)&(r-g>45)&(b-g>25), (b>65)&(b>g*2)&(b>r*2)]
    found=[]
    for mask in masks:
        for portal in _portal_components(frame,mask):
            x,y,w,h=portal['box']
            if not any(abs(x+w/2-a['box'][0]-a['box'][2]/2)<20 for a in found):found.append(portal)
    return found


def _portal_components(frame,mask):
    mask[:100]=False;mask[400:]=False;mask[:,:100]=False;mask[:,1080:]=False
    mask=np.array(Image.fromarray(mask.astype(np.uint8)*255).filter(ImageFilter.MaxFilter(7)))>0
    found=[]
    for y,x in np.argwhere(mask):
        if not mask[y,x]:continue
        stack=[(int(y),int(x))];mask[y,x]=False
        left=right=int(x);top=bottom=int(y);area=0
        while stack:
            yy,xx=stack.pop();area+=1
            left=min(left,xx);right=max(right,xx);top=min(top,yy);bottom=max(bottom,yy)
            for ny,nx in ((yy-1,xx),(yy+1,xx),(yy,xx-1),(yy,xx+1)):
                if 0<=ny<720 and 0<=nx<1280 and mask[ny,nx]:
                    mask[ny,nx]=False;stack.append((ny,nx))
        w,h=right-left+1,bottom-top+1
        if 15<=w<=150 and 60<=h<=290 and h/w>=1.8 and area>=300:
            glyph=frame[top+int(h*.2):top+int(h*.85),left:right+1,:]
            # 门中央有白色刻印图标；紫色地图裂纹没有，不能仅凭颜色走向墙。
            if int(np.count_nonzero(np.min(glyph,axis=2)>220))>=25:
                found.append({"box":[left,top,w,h],"area":area})
    return found
