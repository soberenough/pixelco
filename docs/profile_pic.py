# PixelCo profile picture (agreed by Claude + ChatGPT, 2026-11-15): mark only, dark field, orange pixel P.
from PIL import Image, ImageDraw
INK=(28,30,38); ACC=(232,93,58)
P=["1110","1001","1001","1110","1000","1000"]   # closed-bowl pixel P
S=1080; s=112; g=10; r=24
w=4*s+3*g; h=6*s+5*g; x0=(S-w)//2+s//6; y0=(S-h)//2   # nudge right: optical centre of a P sits left
im=Image.new("RGB",(S,S),INK); d=ImageDraw.Draw(im)
for ri,row in enumerate(P):
    for ci,ch in enumerate(row):
        if ch=="1":
            x=x0+ci*(s+g); y=y0+ri*(s+g); d.rounded_rectangle([x,y,x+s,y+s],radius=r,fill=ACC)
im.save("site/brand/pixelco-profile-1080.png")
for n in (320,110,40): im.resize((n,n),Image.LANCZOS).save(f"/tmp/pp{n}.png")
