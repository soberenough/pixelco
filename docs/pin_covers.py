from PIL import Image, ImageDraw, ImageFont
import textwrap, sys
F="/usr/share/fonts/opentype/inter/"
def f(n,s): return ImageFont.truetype(F+n,s)
KITS=[
("freelance-proposal-kit","Freelance Proposal Kit","Turn \"send me a quote\" into a yes",9,
 ["Proposal template + completed example","3-option pricing with worked maths","7 follow-up emails with timing","5-minute pre-send checklist","Proposal tracker spreadsheet"]),
("freelancer-get-paid-kit","Freelancer Get-Paid Kit","Get paid on time without awkward chasing",7,
 ["Invoice tracker spreadsheet","Pre-send invoice checklist","4 payment reminder emails","Copy-paste payment terms","Deposits, late fees, kill fees"]),
("freelance-client-onboarding-kit","Client Onboarding Kit","Start every project clearly",9,
 ["Client intake questionnaire","Scope of work + example","5 onboarding emails","30-minute kickoff agenda","Change request log"]),
("freelance-rate-increase-kit","Rate Increase Kit","Raise your rates without awkward talks",9,
 ["Rate review worksheet","Client-by-client tracker","90-day timeline","10 notice & follow-up emails","Scripts for 8 client replies"]),
("freelance-change-request-kit","Change Request Kit","Stop scope creep without arguing",9,
 ["Revision policy, 3 strictness levels","\"Revision or change?\" test","Change request form + example","2-minute pricing for extra work","10 ready-to-send emails"]),
]
BG=(250,246,238); INK=(28,30,38); ACC=(232,93,58); MUTED=(95,98,110); CARD=(255,255,255)
for slug,title,tag,price,items in KITS:
    W,Hh=1000,1500; im=Image.new("RGB",(W,Hh),BG); d=ImageDraw.Draw(im)
    d.rectangle([0,0,W,18],fill=ACC)
    d.text((70,80),"FREELANCER TEMPLATE KIT",font=f("Inter-SemiBold.otf",30),fill=ACC)
    y=135
    for line in textwrap.wrap(title,16,break_on_hyphens=False):
        d.text((70,y),line,font=f("InterDisplay-ExtraBold.otf",104),fill=INK); y+=118
    y+=15
    for line in textwrap.wrap(tag,30):
        d.text((70,y),line,font=f("Inter-Medium.otf",46),fill=MUTED); y+=60
    y+=45
    top=y; d.rounded_rectangle([60,top,W-60,top+120+len(items)*92],radius=28,fill=CARD,outline=(230,224,212),width=3)
    d.text((105,top+35),"What's inside",font=f("Inter-Bold.otf",40),fill=INK); yy=top+105
    for it in items:
        d.ellipse([105,yy+14,129,yy+38],fill=ACC)
        d.text((150,yy),it,font=f("Inter-Regular.otf",37),fill=INK); yy+=92
    y=Hh-300
    d.rounded_rectangle([60,y,W-60,y+130],radius=65,fill=INK)
    d.text((W//2,y+65),f"Instant download  ·  ${price}",font=f("Inter-Bold.otf",48),fill=(255,255,255),anchor="mm")
    d.text((W//2,Hh-120),"Word  ·  PDF  ·  Excel   —   nothing to install",font=f("Inter-Medium.otf",36),fill=MUTED,anchor="mm")
    d.text((W//2,Hh-60),"PixelCo",font=f("Inter-Bold.otf",34),fill=ACC,anchor="mm")
    im.save(f"/home/claude/pixelco/site/pins/{slug}.png",optimize=True)
print("ok")
