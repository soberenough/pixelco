"""Storefront layout: hero, shelves of product cards grouped by the job they do,
free tools and guides as cards, and richer product pages.

Pure presentation. Reads item data and the optional, human-reviewed copy file
copy/products.json; never touches checkouts, prices or money.
"""
import html as H
import json
import re
from pathlib import Path


def _ads_on():
    from .lanes import ads_head  # late import: lanes imports this module
    return bool(ads_head())

COPY_FILE = Path("copy") / "products.json"

# Shelves, in display order. First matching shelf wins; keywords match the title.
SHELVES = [
    ("get-paid", "Get paid on time",
     "Invoices, deposits, reminders and rates, so money arrives when it should.",
     ["get-paid", "deposit", "milestone", "invoice", "bookkeeping", "irregular income",
      "rate increase", "retainer"]),
    ("win-clients", "Win the right clients",
     "From first call to signed proposal, plus the pages and proof that bring work in.",
     ["discovery", "proposal", "pipeline", "services page", "case study", "referral",
      "testimonial", "onboarding"]),
    ("run-projects", "Run projects smoothly",
     "Scope, changes, difficult moments and clean hand-offs.",
     ["change request", "difficult client", "wrap-up", "subcontract", "time tracking"]),
    ("plan-grow", "Plan and grow",
     "Capacity, time off and the yearly review that keeps the business healthy.",
     ["capacity", "time off", "year-end", "review"]),
]
OTHER = ("more", "More from the shop", "Other planners and kits.")

FILE_HINTS = [  # (pattern in file name, friendly label)
    (r"readme|start-here", "Start-here guide: what's in the kit and how to use it"),
    (r"\.csv$", "Spreadsheet template (opens in Excel, Google Sheets or Numbers)"),
    (r"email|reminder|script|message", "Ready-to-send wording you can copy and adapt"),
    (r"checklist", "Step-by-step checklist"),
    (r"terms|contract|clause|agreement|policy", "Clause wording to adapt (general information, not legal advice)"),
    (r"\.md$|\.txt$", "Guide or template you can copy into any doc app"),
]


def load_copy():
    try:
        return json.loads(COPY_FILE.read_text())
    except (OSError, ValueError):
        return {}


def slug_of(item):
    return item.get("url", "").strip("/").split("/")[-1] or item.get("id", "")


def shelf_of(item):
    t = item.get("title", "").lower()
    for key, *_rest, kws in SHELVES:
        if any(k in t for k in kws):
            return key
    return OTHER[0]


def short(text, n=170):
    text = " ".join((text or "").split())
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0].rstrip(",.;:")
    return cut + "…"


def meta_description(site, url):
    """Description of an already-built page (tools and guides keep theirs in <meta>)."""
    try:
        s = (Path(site) / url / "index.html").read_text(errors="ignore")[:6000]
    except OSError:
        return ""
    m = re.search(r'<meta name="description" content="([^"]*)"', s)
    return H.unescape(m.group(1)) if m else ""


def file_label(name, notes):
    if name in notes:
        return notes[name]
    low = name.lower()
    for pat, label in FILE_HINTS:
        if re.search(pat, low):
            return label
    return "Template file"


def initials(title):
    words = [w for w in re.findall(r"[A-Za-z]+", title) if w.lower() not in ("freelance", "freelancer", "kit", "and", "the", "a")]
    return ("".join(w[0] for w in words[:2]) or title[:2]).upper()


def card(item, copy, depth=0):
    c = copy.get(slug_of(item), {})
    title = H.escape(item["title"])
    tagline = H.escape(c.get("tagline") or short(item.get("description", "")))
    n = len(item.get("files") or [])
    price = f'${float(item["price"]):.0f}' if item.get("price") else ""
    meta = " · ".join(x for x in (f"{n} ready-to-use files" if n else "", price) if x)
    return (f'<a class=card href="{"../" * depth}{item["url"]}">'
            f'<span class=badge aria-hidden=true>{H.escape(initials(item["title"]))}</span>'
            f'<span class=ct>{title}</span><span class=cd>{tagline}</span>'
            f'<span class=cm>{meta}</span></a>')


def bundle_of(items):
    b = [i for i in items if i.get("lane") == "products" and i.get("includes")]
    return b[-1] if b else None


def index_body(items, site):
    copy = load_copy()
    prods = [i for i in items if i["lane"] == "products" and not i.get("includes")][::-1]
    tools = [i for i in items if i["lane"] == "tools"][::-1]
    guides = [i for i in items if i["lane"] == "content"][::-1]
    bundle = bundle_of(items)

    out = ['<section class=hero><h1>Ready-made business kits for freelancers</h1>'
           '<p>Templates, scripts and spreadsheets for the jobs every freelancer has to do: '
           'pricing, proposals, getting paid, handling changes and planning the year. '
           'Open them in the tools you already use.</p>'
           '<p class=cta><a class=btn href="#shop">Browse the kits</a> '
           '<a class=btn2 href="#tools">Try a free tool</a></p>'
           '<ul class=trust><li>Instant download</li><li>Works in Excel, Google Sheets, Word or Notion</li>'
           '<li>Full refund within 14 days if a file is broken or not as described</li>'
           + ('<li>No accounts needed</li>' if _ads_on() else '<li>No accounts, no tracking</li>')
           + '</ul></section>']

    if bundle:
        n = len(bundle.get("includes") or [])
        out.append(f'<section class=bundle><h2>Get every kit at once</h2>'
                   f'<p>{H.escape(short(bundle.get("description", ""), 260))}</p>'
                   f'<p><a class=btn href="{bundle["url"]}">See the bundle · '
                   f'{n} kits for ${float(bundle.get("price") or 0):.0f}</a></p></section>')

    out.append('<h2 id=shop>Shop</h2><p class=small>Each kit is a set of finished templates '
               'with instructions. Pick the job you need done.</p>')
    for key, label, blurb, _ in SHELVES + [(*OTHER, [])]:
        row = [p for p in prods if shelf_of(p) == key]
        if not row:
            continue
        out.append(f'<h3 id="{key}">{H.escape(label)}</h3><p class=small>{H.escape(blurb)}</p>'
                   f'<div class=grid>{"".join(card(p, copy) for p in row)}</div>')

    if tools:
        cards = "".join(
            f'<a class="card tool" href="{t["url"]}"><span class=ct>{H.escape(t["title"])}</span>'
            f'<span class=cd>{H.escape(short(t.get("description") or meta_description(site, t["url"]), 140))}</span>'
            f'<span class=cm>Free · runs in your browser</span></a>' for t in tools)
        out.append('<h2 id=tools>Free tools</h2><p class=small>Calculators and builders that run '
                   f'entirely in your browser. Nothing you type is sent anywhere.</p><div class=grid>{cards}</div>')
    if guides:
        lis = "".join(
            f'<li><a href="{g["url"]}">{H.escape(g["title"])}</a>'
            f'<span class=small>{H.escape(short(g.get("description") or meta_description(site, g["url"]), 150))}</span></li>'
            for g in guides)
        out.append(f'<h2 id=guides>Guides</h2><p class=small>Plain answers to common freelance questions.</p>'
                   f'<ul class=guides>{lis}</ul>')
    return "".join(out)


def related_tools(item, items, site):
    words = {w for w in re.findall(r"[a-z]+", item["title"].lower()) if len(w) > 3} - {"freelance", "freelancer"}
    hits = []
    for t in items:
        if t["lane"] != "tools":
            continue
        tw = set(re.findall(r"[a-z]+", t["title"].lower()))
        if words & tw:
            hits.append(t)
    return hits[:3]


def product_body(item, items, site):
    copy = load_copy().get(slug_of(item), {})
    price = float(item.get("price") or 0)
    desc = item.get("description") or ""
    files = list(item.get("files") or [])
    notes = copy.get("file_notes") or {}
    buy = (f'<a class=btn href="{H.escape(item["buy_url"])}">Buy for ${price:.2f}</a>'
           if item.get("buy_url") else "<i>Checkout opens soon.</i>")
    shelf = next((s for s in SHELVES if s[0] == shelf_of(item)), None)
    crumb = (f'<p class=small><a href="../../#shop">Shop</a> › '
             f'<a href="../../#{shelf[0]}">{H.escape(shelf[1])}</a></p>' if shelf else "")
    parts = [crumb, f"<h1>{H.escape(item['title'])}</h1>",
             f'<p class=lede>{H.escape(copy.get("tagline") or desc)}</p>' if copy.get("tagline") else f"<p class=lede>{H.escape(desc)}</p>",
             f'<p class=buy><span class=price>${price:.2f}</span> {buy}</p>']
    if copy.get("who_for"):
        parts.append(f'<h2>Who it\'s for</h2><p>{H.escape(copy["who_for"])}</p>')
    if copy.get("outcomes"):
        parts.append("<h2>What it helps you do</h2><ul class=ticks>"
                     + "".join(f"<li>{H.escape(o)}</li>" for o in copy["outcomes"][:6]) + "</ul>")
    if copy.get("tagline") and desc:
        parts.append(f"<h2>About this kit</h2><p>{H.escape(desc)}</p>")
    parts.append("<h2>What's inside</h2><ul class=files>"
                 + "".join(f"<li><b>{H.escape(f)}</b><span>{H.escape(file_label(f, notes))}</span></li>" for f in files)
                 + "<li><b>LICENSE.txt</b><span>Use for your own personal and business work</span></li></ul>")
    tools = related_tools(item, items, site)
    if tools:
        parts.append("<h2>Free tools that pair with this kit</h2><ul>"
                     + "".join(f'<li><a href="../../{t["url"]}">{H.escape(t["title"])}</a></li>' for t in tools) + "</ul>")
    parts.append(f'<p class=buy>{buy}</p>'
                 "<p class=small>Instant download after checkout. Payments are processed by Stripe. "
                 'Full refund within 14 days if a file is broken or not as described: see our '
                 '<a href="../../refunds/">refund policy</a>. General information, not legal, tax or '
                 "financial advice.</p>")
    return "".join(parts)


STYLE_EXTRA = """
.wrap{max-width:980px}
.hero{padding:28px 0 8px}.hero h1{font-size:clamp(28px,4.5vw,42px);margin:0 0 10px}
.hero p{max-width:680px;color:var(--dim);font-size:18px}
.cta{margin:18px 0;display:flex;flex-wrap:wrap;gap:10px}.btn2{display:inline-block;padding:.6em 1.3em;border-radius:6px;border:1px solid var(--line);text-decoration:none;font-weight:600;color:var(--fg)}
.trust{display:flex;flex-wrap:wrap;gap:6px 18px;list-style:none;padding:0;margin:10px 0 0;font-size:14px;color:var(--dim)}
.trust li::before{content:"✓ ";color:var(--btn);font-weight:700}
.bundle{margin:24px 0;padding:18px 20px;border:2px solid var(--btn);border-radius:10px}
.bundle h2{margin-top:0}
h3{margin:28px 0 2px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px;margin:12px 0 8px}
.card{display:flex;flex-direction:column;gap:6px;padding:16px;border:1px solid var(--line);border-radius:10px;text-decoration:none;color:var(--fg);background:color-mix(in srgb,var(--bg) 92%,var(--accent));transition:transform .12s,border-color .12s}
.card:hover{transform:translateY(-2px);border-color:var(--accent)}
.badge{width:40px;height:40px;border-radius:9px;display:grid;place-items:center;font-weight:800;font-size:15px;color:#fff;background:var(--accent)}
.ct{font-weight:700;line-height:1.3}.cd{font-size:15px;color:var(--dim);line-height:1.45}.cm{font-size:13px;color:var(--dim);margin-top:auto}
.card.tool .ct::before{content:"⚙ ";color:var(--accent)}
ul.guides{list-style:none;padding:0}ul.guides li{padding:10px 0;border-bottom:1px solid var(--line)}ul.guides .small{display:block}
.lede{font-size:19px}.buy{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
ul.ticks{list-style:none;padding:0}ul.ticks li{padding:4px 0}ul.ticks li::before{content:"✓ ";color:var(--btn);font-weight:700}
ul.files{list-style:none;padding:0}ul.files li{padding:8px 0;border-bottom:1px solid var(--line)}ul.files span{display:block;font-size:14px;color:var(--dim)}
"""
