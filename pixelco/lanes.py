"""Turn checked item specs into live pages, downloads and checkouts.

content   - helpful guides on the site; earn by cross-selling the shop
tools     - offline single-file web tools; earn through tips and cross-sells
products  - downloadable kits sold through Stripe checkout links
"""
import html as H
import io
import secrets
import zipfile
from pathlib import Path

from .guard import lock_tool

SITE = Path("site")


def build_content(spec, ledger, cfg, stripe=None):
    slug = spec["slug"]
    body = spec["html"].replace("<a ", '<a rel="nofollow noopener" ')
    out = SITE / "blog" / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(spec["title"], spec["description"],
                        f"<article>{body}</article>" + _crosssell(ledger), depth=2))
    return {"id": f"content-{slug}", "lane": "content", "title": spec["title"],
            "url": f"blog/{slug}/"}


def build_tool(spec, ledger, cfg, stripe=None):
    slug = spec["slug"]
    html = lock_tool(spec["html"])
    back = ('<p style="text-align:center;margin:2em 0;font:14px system-ui">'
            '<a href="../../">More free tools from PixelCo</a></p>')
    html = html.replace("</body>", back + "</body>") if "</body>" in html else html + back
    out = SITE / "tools" / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return {"id": f"tool-{slug}", "lane": "tools", "title": spec["title"],
            "url": f"tools/{slug}/"}


def build_product(spec, ledger, cfg, stripe):
    slug, price = spec["slug"], spec["price"]
    # Delivery: zip at an unguessable path, only revealed after checkout.
    token = secrets.token_urlsafe(18)
    dl = SITE / "dl" / token
    dl.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in spec["files"].items():
            z.writestr(name, body)
        z.writestr("LICENSE.txt",
                   "You may use these files for personal and business work.\n"
                   "Please don't resell or share them as-is.\n")
    (dl / f"{slug}.zip").write_bytes(buf.getvalue())
    (dl / "index.html").write_text(page(
        "Thank you", "Your download",
        f"<h1>Thanks for your order</h1><p>Your download is ready: "
        f'<a class=btn href="{slug}.zip">Download {H.escape(spec["title"])}</a></p>'
        "<p>Bookmark this page in case you need the file again. Problems? "
        'See the <a href="../../contact/">contact page</a>.</p>', depth=2, index=False))

    item = {"id": f"product-{slug}", "lane": "products", "title": spec["title"],
            "price": price, "description": spec["description"], "url": f"shop/{slug}/",
            "dl": token, "files": list(spec["files"])}
    attach_checkout(item, cfg, stripe)
    return item


def attach_checkout(item, cfg, stripe):
    """Create the Stripe checkout for a product (retried each run until it works)."""
    if stripe.enabled and not item.get("buy_url"):
        base = cfg.get("site_url", "").rstrip("/")
        buy = stripe.create_payment_link(item, item["price"], f"{base}/dl/{item['dl']}/")
        if buy:
            item["stripe_link"] = buy["id"]
            item["buy_url"] = buy["url"]
    write_product_page(item, item.get("files", []))


def write_product_page(item, files):
    buy = (f'<p><a class=btn href="{H.escape(item["buy_url"])}">Buy for ${item["price"]:.2f}</a></p>'
           if item.get("buy_url") else "<p><i>Checkout opens soon.</i></p>")
    body = (f"<h1>{H.escape(item['title'])}</h1><p>{H.escape(item['description'])}</p>"
            f"<p class=price>${item['price']:.2f}</p>{buy}"
            "<h2>What's inside</h2><ul>"
            + "".join(f"<li>{H.escape(n)}</li>" for n in files)
            + "<li>LICENSE.txt</li></ul>"
            "<p class=small>Instant download after checkout. Payments are processed by Stripe. "
            'See our <a href="../../refunds/">refund policy</a>.</p>')
    out = SITE / item["url"] / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(item["title"], item["description"], body, depth=2))


def _crosssell(ledger):
    prods = [i for i in ledger.state["items"] if i["lane"] == "products"][-3:]
    if not prods:
        return ""
    links = "".join(f'<li><a href="../../{p["url"]}">{H.escape(p["title"])}</a></li>' for p in prods)
    return f"<aside><h2>From the PixelCo shop</h2><ul>{links}</ul></aside>"


STYLE = """
:root{--bg:#fbfaf7;--fg:#22212b;--dim:#6b6878;--line:#e4e1d8;--accent:#3b6fd4;--btn:#2f8a4c}
@media (prefers-color-scheme:dark){:root{--bg:#17161f;--fg:#ebe8df;--dim:#a19db0;--line:#2e2c3a;--accent:#8fb0ff;--btn:#3fa862}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.65 system-ui,-apple-system,Segoe UI,sans-serif}
.wrap{max-width:720px;margin:0 auto;padding:20px max(16px,env(safe-area-inset-left,0px)) 40px}
nav,footer{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:14px;color:var(--dim)}
nav{padding-bottom:12px;border-bottom:1px solid var(--line);margin-bottom:24px}
nav b a{color:var(--fg);text-decoration:none;font-size:17px}
footer{margin-top:48px;padding-top:12px;border-top:1px solid var(--line)}
a{color:var(--accent)}h1{line-height:1.2;text-wrap:balance}
.btn{display:inline-block;background:var(--btn);color:#fff;padding:.6em 1.3em;border-radius:6px;text-decoration:none;font-weight:600}
.price{font-size:24px;font-weight:700}.small{font-size:14px;color:var(--dim)}
ul.items{list-style:none;padding:0}ul.items li{padding:8px 0;border-bottom:1px solid var(--line)}
aside{margin-top:40px;padding-top:12px;border-top:1px solid var(--line)}
"""


def page(title, description, body, depth=0, index=True):
    up = "../" * depth
    robots = "" if index else '<meta name="robots" content="noindex">'
    return (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{H.escape(title)} · PixelCo</title>"
        f'<meta name="description" content="{H.escape(description)}">{robots}'
        f"<style>{STYLE}</style></head><body><div class=wrap>"
        f'<nav><b><a href="{up}./">PixelCo</a></b><a href="{up}./#shop">Shop</a>'
        f'<a href="{up}./#tools">Free tools</a><a href="{up}./#guides">Guides</a></nav>'
        f"{body}"
        f'<footer><a href="{up}contact/">Contact</a><a href="{up}refunds/">Refunds</a>'
        f'<a href="{up}terms/">Terms</a><a href="{up}privacy/">Privacy</a></footer>'
        "</div></body></html>"
    )


BUILD = {"content": build_content, "tools": build_tool, "products": build_product}
