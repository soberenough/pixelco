"""Builds the 'Comment PAID' prompt-screenshot post (1080x1350). Run: python make_image.py"""
from PIL import Image, ImageDraw, ImageFont
import re
F = "/usr/share/fonts/opentype/inter/"
B = lambda s: ImageFont.truetype(F + "InterDisplay-ExtraBold.otf", s)
M = lambda s: ImageFont.truetype(F + "Inter-SemiBold.otf", s)
MONO = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 23)
INK, CARD, CREAM, ACC, DIM, TAG, FILL = (28, 30, 38), (38, 41, 52), (250, 246, 238), (232, 93, 58), (150, 152, 160), (120, 170, 230), (240, 190, 90)

src = open("late-payment-reminder-prompt.md").read().split("```")[1].strip("\n").splitlines()

def make(cta, out):
    W, H = 1080, 1350
    im = Image.new("RGB", (W, H), INK); d = ImageDraw.Draw(im)
    d.text((70, 70), "STOP WRITING", font=B(92), fill=CREAM)
    d.text((70, 168), "“JUST CHECKING IN.”", font=B(92), fill=CREAM)
    d.text((70, 270), "MAKE AI WRITE YOUR", font=B(70), fill=ACC)
    d.text((70, 346), "PAYMENT REMINDERS.", font=B(70), fill=ACC)
    # prompt "screenshot" card
    x0, y0, x1, y1 = 60, 460, 1020, 1130
    d.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=CARD)
    for i, c in enumerate([(224, 86, 86), (240, 190, 90), (76, 175, 120)]):
        d.ellipse([x0 + 26 + i * 30, y0 + 22, x0 + 44 + i * 30, y0 + 40], fill=c)
    d.text((x0 + 130, y0 + 18), "late-payment-reminder.prompt", font=M(22), fill=DIM)
    y = y0 + 70
    for line in src:
        if y > y1 - 110: break
        x = x0 + 30
        for part in re.split(r"(\[[^\]]*\]?|<[^>]*>)", line[:62]):
            if not part: continue
            col = FILL if part.startswith("[") else TAG if part.startswith("<") else CREAM
            d.text((x, y), part, font=MONO, fill=col); x += d.textlength(part, font=MONO)
        y += 31
    # fade the bottom of the card so it reads as "cut off"
    FH = 240
    fade = Image.new("RGBA", (x1 - x0, FH), (0, 0, 0, 0)); fd = ImageDraw.Draw(fade)
    for i in range(FH):
        fd.line([(0, i), (x1 - x0, i)], fill=CARD + (min(255, int(255 * (i / (FH - 90)) ** 1.3)),))
    im.paste(fade, (x0, y1 - FH - 10), fade)
    ImageDraw.Draw(im).rounded_rectangle([x0, y1 - 100, x1, y1], radius=24, fill=CARD)
    d = ImageDraw.Draw(im)
    d.text((x0 + 30, y1 - 64), "… 4 stages · fill-in blanks · works in Claude, ChatGPT or any AI", font=M(25), fill=DIM)
    # CTA
    d.rounded_rectangle([60, 1160, 1020, 1250], radius=20, fill=ACC)
    tw = d.textlength(cta, font=B(46)); d.text(((W - tw) / 2, 1180), cta, font=B(46), fill=INK)
    P = ["1110", "1001", "1001", "1110", "1000", "1000"]
    for r, row in enumerate(P):
        for c, ch in enumerate(row):
            if ch == "1": d.rounded_rectangle([70 + c * 15, 1270 + r * 11, 82 + c * 15, 1279 + r * 11], radius=3, fill=ACC)
    d.text((140, 1278), "PixelCo", font=M(34), fill=CREAM)
    d.text((620, 1284), "Save this · @pixelco.shop", font=M(28), fill=DIM)
    im.save(out)

make("Comment PAID for the full prompt", "post-comment-PAID-1080x1350.png")
make("Full prompt free · link in bio", "post-link-in-bio-1080x1350.png")
