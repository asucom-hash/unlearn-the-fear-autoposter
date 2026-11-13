"""Create deterministic, code-generated cinematic gold and dark landscape JPEGs."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SIZE=1080
GOLD=(234,189,100)
WHITE=(249,246,235)

def font(size,bold=False):
    name='/usr/share/fonts/truetype/dejavu/DejaVuSans-'+('Bold' if bold else '')+'.ttf'
    name=name.replace('Sans-.','Sans.')
    return ImageFont.truetype(name,size)

def landscape(index):
    rng=np.random.default_rng(3319+index*97)
    y=np.linspace(0,1,SIZE,dtype=np.float32)[:,None,None]
    x=np.linspace(-1,1,SIZE,dtype=np.float32)[None,:,None]
    sun_y=0.71 if index%3 else 0.58
    glow=np.exp(-((x/.56)**2+((y-sun_y)/.25)**2)*2.4)
    rgb=np.array([8,11,24],dtype=np.float32)*(1-y)+np.array([52,42,39],dtype=np.float32)*y
    rgb=rgb+glow*np.array([125,82,26],dtype=np.float32)
    rgb=rgb+rng.normal(0,2,(SIZE,SIZE,1)).astype(np.float32)
    im=Image.fromarray(np.uint8(np.clip(rgb,0,255)),'RGB')
    d=ImageDraw.Draw(im,'RGBA')
    for _ in range(90):
        xx,yy=int(rng.integers(0,SIZE)),int(rng.integers(30,610))
        rr=int(rng.choice([1,1,1,2]))
        d.ellipse((xx-rr,yy-rr,xx+rr,yy+rr),fill=(255,229,175,int(rng.integers(25,95))))
    def ridge(base,amp,color,points):
        coords=[(0,base)]+[(int(k*SIZE/points),int(base-rng.integers(-amp//2,amp))) for k in range(1,points)]+[(SIZE,base)]
        d.polygon(coords+[(SIZE,SIZE),(0,SIZE)],fill=color)
    if index%4==0:
        ridge(725,145,(24,28,34,245),8);ridge(840,175,(13,18,23,245),9)
    elif index%4==1:
        ridge(750,95,(40,35,30,255),10);ridge(860,95,(18,23,28,255),7)
    elif index%4==2:
        ridge(700,165,(38,34,35,255),6);ridge(880,160,(9,16,20,255),9)
        d.polygon([(516,715),(553,715),(740,1080),(315,1080)],fill=(157,112,53,60))
    else:
        d.rectangle((0,760,SIZE,SIZE),fill=(13,20,28,255))
        for k in range(6):
            yy=770+k*45
            d.arc((-70,yy-90,1160,yy+25),0,180,fill=(195,143,67,max(10,65-k*8)),width=2)
    for yy in range(195,825):
        opacity=int(98*(1-abs(yy-510)/315))
        d.line([(0,yy),(SIZE,yy)],fill=(0,0,0,max(0,opacity)))
    return im

def wrapped(text,draw,f,maxwidth=858):
    lines=[];current=''
    for word in text.split():
        trial=(current+' '+word).strip()
        if current and draw.textbbox((0,0),trial,font=f)[2]>maxwidth:
            lines.append(current);current=word
        else:current=trial
    if current:lines.append(current)
    return lines

def render_quote(quote,index,path):
    im=landscape(index)
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((421,126,659,132),radius=3,fill=GOLD)
    strap='LET GO OF FEAR  •  DISCOVER YOUR STRENGTH'
    f=font(21)
    w=d.textbbox((0,0),strap,font=f)[2]
    d.text(((SIZE-w)/2,170),strap,font=f,fill=(200,180,143))
    for size in range(71,40,-2):
        big=font(size,True);lines=wrapped(quote,d,big);step=int(size*1.34)
        if len(lines)<=6 and len(lines)*step<=420:break
    top=500-(len(lines)*step)//2
    for i,line in enumerate(lines):
        ww=d.textbbox((0,0),line,font=big)[2]
        xx=(SIZE-ww)/2;yy=top+i*step
        d.text((xx,yy),line,font=big,fill=GOLD if i==len(lines)-1 else WHITE,stroke_width=1,stroke_fill=(0,0,0))
    d.rounded_rectangle((468,818,612,824),radius=3,fill=GOLD)
    f=font(23,True);brand='UNLEARN THE FEAR'
    ww=d.textbbox((0,0),brand,font=f)[2]
    d.text(((SIZE-ww)/2,863),brand,font=f,fill=WHITE)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    im.save(path,'JPEG',quality=90,optimize=True,progressive=True)
