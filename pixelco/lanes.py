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
    included = bundle_parts(spec, ledger)   # fail before writing anything
    value = round(sum(float(p.get("price") or 0) for p in included), 2)
    # Delivery: zip at an unguessable path, only revealed after checkout.
    token = secrets.token_urlsafe(18)
    dl = SITE / "dl" / token
    dl.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in spec["files"].items():
            z.writestr(name, body)
        for part in included:
            kit_slug = part["url"].strip("/").split("/")[-1]
            with zipfile.ZipFile(SITE / "dl" / part["dl"] / f"{kit_slug}.zip") as kit:
                for n in kit.namelist():
                    if n != "LICENSE.txt" and not n.endswith("/"):
                        z.writestr(f"{kit_slug}/{n}", kit.read(n))
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
    if included:
        item["includes"] = [p["id"] for p in included]
        item["value"] = value
    attach_checkout(item, cfg, stripe, ledger)
    return item


def bundle_parts(spec, ledger):
    """The kits a bundle packs in. Raises ValueError if any isn't a built kit."""
    parts = []
    for s in spec.get("includes") or []:
        it = next((i for i in ledger.state["items"] if i["id"] == f"product-{s}"), None)
        if not it or it.get("includes") or not it.get("dl"):
            raise ValueError(f"bundle part not in the shop (or is a bundle): {s}")
        if not (SITE / "dl" / it["dl"] / f"{s}.zip").is_file():
            raise ValueError(f"bundle part's download is missing: {s}")
        parts.append(it)
    if parts:
        value = sum(float(p.get("price") or 0) for p in parts)
        if not 0.3 * value <= spec["price"] <= 0.9 * value:
            raise ValueError(f"bundle price ${spec['price']:.2f} must be 30-90% "
                             f"of its kits' ${value:.2f}")
    return parts


def attach_checkout(item, cfg, stripe, ledger=None):
    """Create the Stripe checkout for a product (retried each run until it works)."""
    if stripe.enabled and not item.get("buy_url"):
        base = cfg.get("site_url", "").rstrip("/")
        buy = stripe.create_payment_link(item, item["price"], f"{base}/dl/{item['dl']}/")
        if buy:
            item["stripe_link"] = buy["id"]
            item["buy_url"] = buy["url"]
            item["stripe_mode"] = stripe.mode
    write_product_page(item, item.get("files", []), ledger)


def bundle_for(item, ledger):
    """The biggest buyable bundle that contains this product, if any."""
    if not ledger or item.get("includes"):
        return None
    bs = [b for b in ledger.state["items"]
          if item["id"] in (b.get("includes") or []) and b.get("buy_url")]
    return max(bs, key=lambda b: len(b["includes"]), default=None)


def link_mode(item):
    if item.get("stripe_mode"):
        return item["stripe_mode"]
    return "test" if "/test_" in item.get("buy_url", "") else "live"


def reset_checkout(item):
    """Forget a checkout from the other Stripe mode, so a new one is made.

    The download moves to a fresh secret folder too: the old checkout still
    exists in Stripe and still redirects to the old folder, so leaving it
    would let anyone with a test card download the kit for free.
    """
    for k in ("buy_url", "stripe_link", "stripe_product", "stripe_price",
              "tax_code_set", "stripe_mode"):
        item.pop(k, None)
    old = item.get("dl")
    if old and (SITE / "dl" / old).is_dir():
        new = secrets.token_urlsafe(18)
        (SITE / "dl" / old).rename(SITE / "dl" / new)
        item["dl"] = new
        return None
    return f"download folder missing for {item.get('title', item.get('id'))}; old link may still work"


def write_product_page(item, files, ledger=None):
    price = float(item.get("price") or 0)
    desc = item.get("description") or ""
    buy = (f'<p><a class=btn href="{H.escape(item["buy_url"])}">Buy for ${price:.2f}</a></p>'
           if item.get("buy_url") else "<p><i>Checkout opens soon.</i></p>")
    inside = "".join(f"<li>{H.escape(n)}</li>" for n in files)
    value = ""
    if item.get("includes") and ledger:
        by_id = {i["id"]: i for i in ledger.state["items"]}
        parts = [by_id[k] for k in item["includes"] if k in by_id]
        inside += "".join(f'<li><a href="../../{p["url"]}">{H.escape(p["title"])}</a> '
                          f'<span class=small>(${float(p.get("price") or 0):.2f} alone)</span></li>'
                          for p in parts)
        if item.get("value", 0) > price:
            value = (f'<p class=small>{len(parts)} kits worth ${item["value"]:.2f} if bought '
                     f'separately. You save ${item["value"] - price:.2f}.</p>')
    upsell = ""
    b = bundle_for(item, ledger)
    if b:
        upsell = (f'<aside class=deal><b>Better value:</b> get this kit and '
                  f'{len(b["includes"]) - 1} more in the <a href="../../{b["url"]}">'
                  f'{H.escape(b["title"])}</a> for ${b["price"]:.2f}.</aside>')
    body = (f"<h1>{H.escape(item['title'])}</h1><p>{H.escape(desc)}</p>"
            f"<p class=price>${price:.2f}</p>{value}{buy}{upsell}"
            "<h2>What's inside</h2><ul>"
            + inside
            + "<li>LICENSE.txt</li></ul>"
            "<p class=small>Instant download after checkout. Payments are processed by Stripe. "
            'See our <a href="../../refunds/">refund policy</a>.</p>')
    out = SITE / item["url"] / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(item["title"], desc, body, depth=2))


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
aside.deal{margin:20px 0;padding:12px 16px;border:2px solid var(--btn);border-radius:8px}
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
