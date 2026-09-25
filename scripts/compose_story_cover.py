"""Render fixed cover typography with real Hebrew shaping, never AI-drawn text."""
import json, re, sys, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, features
from fontTools.ttLib import TTFont

if not features.check_feature("raqm"):
    raise RuntimeError("Pillow requires RAQM for correct Hebrew rendering")
m=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
im=ImageOps.fit(Image.open(sys.argv[2]).convert("RGB"),(1080,1920)).convert("RGBA")
shade=Image.new("RGBA",im.size)
d=ImageDraw.Draw(shade)
for y in range(1920):
    a=int(110+95*abs(y-980)/980)
    d.line((0,y,1080,y),fill=(0,0,0,min(a,220)))
im=Image.alpha_composite(im,shade)
d=ImageDraw.Draw(im)
root=Path("/usr/share/fonts/truetype")
he=next(root.rglob("DejaVuSans-Bold.ttf"))
latin=next(root.rglob("DejaVuSans-Bold.ttf"))
def clean(s):
    return re.sub(r"[^\w\s\u0590-\u05ff.,!?׳’'־:—-]","",str(s)).strip()
glyphs=set(TTFont(str(he)).getBestCmap())
def text(s,box,size=50,color="white",hebrew=True):
    missing=sorted({ord(ch) for ch in s if not ch.isspace() and ord(ch) not in glyphs})
    if missing:
        raise ValueError("Unsupported cover characters: "+", ".join(f"U+{cp:04X}" for cp in missing))
    x,y,w,h=box
    path=he if hebrew else latin
    direction="rtl" if hebrew else "ltr"
    for z in range(size,17,-1):
        f=ImageFont.truetype(str(path),z)
        lines=[]
        for para in s.split("\n"):
            line=""
            for word in para.split():
                test=(line+" "+word).strip()
                if d.textlength(test,font=f,direction=direction)>w and line:
                    lines.append(line); line=word
                else: line=test
            lines.append(line)
        step=int(z*1.45)
        if len(lines)*step<=h and all(d.textlength(t,font=f,direction=direction)<=w for t in lines): break
    else: raise ValueError("Text cannot fit its fixed area")
    for i,t in enumerate(lines):
        d.text((x+w/2,y+i*step),t,font=f,fill=color,anchor="mt",direction=direction,stroke_width=1,stroke_fill=(0,0,0,150))
logo=Image.open(sys.argv[3]).convert("RGBA")
logo.thumbnail((180,180),Image.Resampling.LANCZOS)
im.alpha_composite(logo,(65,100))
text("GET NEXT",(270,125,325,65),48,hebrew=False)
text("EPISODE",(605,125,360,65),48,"#ff1838",False)
text("READ • LISTEN • CHAT STORIES",(265,200,700,55),28,hebrew=False)
title=clean(m.get("title",""))
genre=clean(m.get("genre") or m.get("category") or "סיפור מקורי")
text(genre,(85,365,910,80),46,"#ff1838")
text(title,(65,465,950,230),140)
text("סיפורים שנקראים כמו צ׳אט.\nנשמעים כמו סדרה.",(80,725,920,170),52)
d.rounded_rectangle((80,935,1000,1095),radius=48,fill=(22,26,32,230),outline=(130,130,130,200),width=2)
d.ellipse((115,965,215,1065),fill="#ed132d")
d.polygon([(153,990),(153,1040),(190,1015)],fill="white")
for i in range(58):
    x=250+i*11
    height=18+58*abs(math.sin(i*1.71))*math.sin(math.pi*(i+1)/60)
    d.line((x,1015-height/2,x,1015+height/2),fill="#ff344d" if i<22 else "white",width=5)
teaser=clean(m.get("tagline") or m.get("teaser") or "")
d.rounded_rectangle((125,1140,980,1390),radius=40,fill=(22,26,32,235),outline=(110,110,110,190),width=2)
text(teaser,(165,1170,775,200),44)
text("קריאה • האזנה • סיפורים בצ׳אט",(90,1435,900,75),40)
d.rounded_rectangle((85,1580,995,1725),radius=38,fill="#d70923",outline="#ff4558",width=3)
text("לקרוא או להאזין לפרק הראשון",(115,1620,850,90),48)
text("@GetNextEpisodeBot",(90,1775,900,85),48,"#ff1838",False)
im.convert("RGB").save(sys.argv[4])
