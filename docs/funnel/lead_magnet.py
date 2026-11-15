# Builds the free lead magnet: "3 late-payment emails" (a sample of the Get-Paid Kit).
# Output: site/free/late-payment-emails.pdf  (uploaded to Gumroad as a $0 product by the owner)
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os, textwrap

INTER = "/usr/share/fonts/truetype/inter/"
def font(name, file):
    for d in (INTER, "/usr/share/fonts/opentype/inter/"):
        p = d + file
        if os.path.exists(p) and p.endswith(".ttf"):
            pdfmetrics.registerFont(TTFont(name, p)); return name
    return {"B": "Helvetica-Bold", "R": "Helvetica"}[name]
B, R = font("B", "Inter-Bold.ttf"), font("R", "Inter-Regular.ttf")
INK, ACC, MUT = Color(28/255, 30/255, 38/255), Color(232/255, 93/255, 58/255), Color(95/255, 98/255, 110/255)
KIT = "https://pixelcoshop.gumroad.com/l/freelancer-get-paid-kit"

EMAILS = [
 ("1. The day after it's due", "Send 1–3 days after the due date.",
  "Subject: Invoice [#] for [amount] — due [date]",
  ["Hi [name],",
   "A quick note that invoice [#] for [amount] was due on [date]. I've attached it again in case the first one went astray.",
   "Could you let me know when I can expect payment, or who I should follow up with?",
   "Thanks, [your name]"]),
 ("2. One week overdue", "Offer to fix whatever is blocking payment.",
  "Subject: Following up: invoice [#] ([amount]), now 7 days overdue",
  ["Hi [name],",
   "I'm following up on invoice [#] for [amount], which was due on [date]. It's attached again here.",
   "If there's an issue with the invoice, or it needs a PO or approval on your side, just tell me what you need and I'll sort it out today.",
   "Thanks, [your name]"]),
 ("3. Thirty days overdue", "Ask for a specific payment date.",
  "Subject: Invoice [#] is 30 days overdue — please confirm a payment date",
  ["Hi [name],",
   "Invoice [#] for [amount] is now 30 days past its due date of [date].",
   "Please reply with a date by which payment will be made. If cash flow is the issue, I'm happy to agree a short payment plan.",
   "Per our agreement, [late fee terms, if any] applies from [date].",
   "Regards, [your name]"]),
]

def wrap(c, text, x, y, f, size, width, color, lead=None):
    c.setFont(f, size); c.setFillColor(color); lead = lead or size * 1.45
    for line in textwrap.wrap(text, width):
        c.drawString(x, y, line); y -= lead
    return y

def build(out="site/free/late-payment-emails.pdf"):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    c = canvas.Canvas(out, pagesize=letter); W, H = letter; X = 60
    c.setFillColor(ACC); c.rect(0, H - 8, W, 8, fill=1, stroke=0)
    y = wrap(c, "FREE SAMPLE FROM THE FREELANCER GET-PAID KIT", X, H - 60, B, 10, 90, ACC)
    y = wrap(c, "3 late-payment emails", X, y - 14, B, 30, 40, INK)
    y = wrap(c, "Copy, fill in the [brackets], send. Always attach the invoice again: the most common reason "
                "for non-payment is that the first email got lost.", X, y - 4, R, 11, 95, MUT)
    for title, when, subj, body in EMAILS:
        y -= 14
        y = wrap(c, title, X, y, B, 14, 70, INK)
        y = wrap(c, when, X, y, R, 10, 95, MUT)
        y = wrap(c, subj, X, y - 4, B, 10.5, 92, INK)
        for p in body:
            y = wrap(c, p, X, y - 3, R, 10.5, 95, INK)
    c.setStrokeColor(Color(0.89, 0.88, 0.85)); c.line(X, 118, W - X, 118)
    wrap(c, "Want the rest? The full Get-Paid Kit adds the final-notice email, copy-paste payment terms "
            "(deposits, late fees, kill fees), an invoice checklist and an invoice tracker spreadsheet.", X, 98, R, 10.5, 95, INK)
    c.setFont(B, 11); c.setFillColor(ACC); c.drawString(X, 58, "Get the full kit ($7): " + KIT)
    c.linkURL(KIT, (X, 52, W - X, 70))
    c.setFont(R, 8); c.setFillColor(MUT); c.drawString(X, 34, "PixelCo · PixelCo.shop@proton.me · Free to use in your own business.")
    c.save()

if __name__ == "__main__":
    build()
