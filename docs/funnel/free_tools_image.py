# "GET PAID FOR FREE" 1080x1350 image (idea 24). Every URL verified 200 on 2026-11-17 from GitHub's servers.
from PIL import Image, ImageDraw, ImageFont
W, H = 1080, 1350
INK = (14, 15, 19); WHITE = (245, 245, 240); DIM = (150, 152, 160); ACC = (232, 93, 58)
F = "/usr/share/fonts/opentype/inter/"
B = lambda s: ImageFont.truetype(F + "InterDisplay-ExtraBold.otf", s)
R = lambda s: ImageFont.truetype(F + "Inter-Regular.otf", s)
M = lambda s: ImageFont.truetype(F + "Inter-SemiBold.otf", s)
ITEMS = [
    ("Free invoicing", "Wave", "waveapps.com/invoicing"),
    ("Free invoicing", "Zoho Invoice", "zoho.com/us/invoice"),
    ("Quick one-off invoice", "Invoice Generator", "invoice-generator.com"),
    ("Contracts & freelancer rights", "Freelancers Union", "freelancersunion.org"),
    ("Self-employed taxes", "IRS tax center", "irs.gov → self-employed tax center"),
    ("Quarterly tax payments", "IRS estimated taxes", "irs.gov → estimated taxes"),
    ("Free small-business help", "SBA", "sba.gov"),
    ("Late-payment emails (free)", "PixelCo templates", "link in bio"),
]
im = Image.new("RGB", (W, H), INK); d = ImageDraw.Draw(im)
d.text((72, 96), "GET PAID", font=B(118), fill=WHITE)
d.text((72, 214), "FOR FREE", font=B(118), fill=ACC)
d.text((72, 350), "Stop buying invoicing courses.", font=M(40), fill=WHITE)
d.text((72, 402), "These are free.", font=R(40), fill=DIM)
y = 500
for what, name, url in ITEMS:
    d.text((72, y), what.upper(), font=M(22), fill=DIM)
    d.text((72, y + 30), name, font=B(40), fill=WHITE)
    tw = d.textlength(name, font=B(40))
    d.text((72 + tw + 18, y + 42), url, font=R(28), fill=ACC if name == "PixelCo templates" else DIM)
    y += 92
d.text((72, H - 72), "Save this.  ·  @pixelco.shop", font=M(30), fill=WHITE)
im.save("site/social/get-paid-for-free-1080x1350.png")
