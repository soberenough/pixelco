"""Marketer/publisher. Rebuilds the storefront, policy pages, sitemap and RSS
each run so search engines and feed readers find new work. Organic only.
"""
import html as H
from pathlib import Path

import json
import os

from .lanes import SITE, page, ADS, ads_head, SITEINFO
from . import storefront


def publish(ledger, cfg):
    items = ledger.state["items"]
    base = cfg.get("site_url", "").rstrip("/")
    ADS["client"] = ((cfg.get("ads") or {}).get("adsense_client") or "").strip()
    SITEINFO["base"] = base

    def section(lane, anchor, label, blurb):
        rows = [i for i in items if i["lane"] == lane][::-1]
        if not rows:
            return ""
        lis = "".join(
            f'<li><a href="{i["url"]}">{H.escape(i["title"])}</a>'
            + (f' <span class=small>${i["price"]:.2f}</span>' if i.get("price") else "")
            + "</li>" for i in rows[:80])
        return f'<h2 id="{anchor}">{label}</h2><p class=small>{blurb}</p><ul class=items>{lis}</ul>'

    # Rebuild every product page from state each run, so a page can never be
    # left pointing at an old checkout (for example after a failed push).
    for i in items:
        if i["lane"] == "products":
            try:
                out = SITE / i["url"] / "index.html"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(page(i["title"], i.get("description") or "",
                                    storefront.product_body(i, items, SITE) + product_jsonld(i, base),
                                    depth=2, path=i["url"]))
            except Exception as e:  # one bad item must not lose the whole run
                ledger.alert(f"couldn't rebuild page for {i.get('id')}: {e}")

    try:
        body = storefront.index_body(items, SITE)
    except Exception as e:  # fall back to the plain lists rather than lose the storefront
        ledger.alert(f"storefront layout failed, used plain lists: {e}")
        body = ("<h1>PixelCo</h1><p>Practical templates, free tools and guides.</p>"
                + section("products", "shop", "Shop", "Instant downloads.")
                + section("tools", "tools", "Free tools", "Run in your browser. Nothing is sent anywhere.")
                + section("content", "guides", "Guides", "Plain answers to specific questions."))
    (SITE / "index.html").write_text(page(
        "Business kits for freelancers",
        "Ready-made templates, scripts and spreadsheets for freelancers: proposals, getting paid, "
        "change requests and planning. Plus free calculators and guides.", body, path=""))

    for slug, title, text in policy_pages(cfg):
        out = SITE / slug / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(title, title, f"<h1>{title}</h1>{text}", depth=1))

    urls = [f"{base}/"] + [f"{base}/{i['url']}" for i in items]
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{H.escape(u)}</loc></url>" for u in urls) + "</urlset>")
    (SITE / "robots.txt").write_text(f"User-agent: *\nDisallow: /dl/\nSitemap: {base}/sitemap.xml\n")
    feed = "".join(
        f"<item><title>{H.escape(i['title'])}</title><link>{base}/{i['url']}</link>"
        f"<guid>{base}/{i['url']}</guid></item>" for i in items[::-1][:30])
    (SITE / "feed.xml").write_text(
        '<?xml version="1.0"?><rss version="2.0"><channel><title>PixelCo</title>'
        f"<link>{base}/</link><description>New from PixelCo</description>{feed}</channel></rss>")
    (SITE / ".nojekyll").write_text("")
    if ads_head():  # ads.txt authorises Google to sell ads on this site
        pub = ADS["client"].replace("ca-", "", 1)
        (SITE / "ads.txt").write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")
    elif (SITE / "ads.txt").exists():
        (SITE / "ads.txt").unlink()
    ledger.event("marketer", f"storefront, policies, sitemap and feed updated ({len(items)} items)")
    indexnow(ledger, cfg, base, urls)


def product_jsonld(i, base):
    """schema.org Product data so search engines can show the price in results."""
    if not i.get("price") or not base:
        return ""
    data = {"@context": "https://schema.org", "@type": "Product", "name": i["title"],
            "description": i.get("description") or "", "url": f"{base}/{i['url']}",
            "brand": {"@type": "Brand", "name": "PixelCo"},
            "offers": {"@type": "Offer", "price": f"{float(i['price']):.2f}", "priceCurrency": "USD",
                       "availability": "https://schema.org/InStock", "url": f"{base}/{i['url']}"}}
    js = json.dumps(data).replace("<", "\\u003c")
    return f'<script type="application/ld+json">{js}</script>'


def indexnow(ledger, cfg, base, urls):
    """Tell Bing, Yandex and other IndexNow search engines about our pages (no account needed).
    The key is public by design: it only proves we control this site."""
    key = ((cfg.get("seo") or {}).get("indexnow_key") or "").strip()
    if not key or not base or not key.isalnum() or not (8 <= len(key) <= 128):
        return
    (SITE / f"{key}.txt").write_text(key)
    if os.environ.get("PIXELCO_NO_PING"):
        return
    try:
        import requests
        from urllib.parse import urlparse
        u = urlparse(base)
        r = requests.post("https://api.indexnow.org/indexnow", timeout=20, json={
            "host": u.netloc, "key": key, "keyLocation": f"{base}/{key}.txt", "urlList": urls[:10000]})
        ledger.event("marketer", f"IndexNow: submitted {len(urls)} pages to search engines (HTTP {r.status_code})")
    except Exception as e:  # never fail the business day over a search-engine ping
        ledger.event("marketer", f"IndexNow ping skipped: {e}")


def policy_pages(cfg):
    email = cfg.get("contact_email") or ""
    contact = (f"<p>Email <b>{H.escape(email)}</b>. We aim to reply within two business days.</p>"
               if email else "<p>Contact details are being set up.</p>")
    return [
        ("contact", "Contact",
         contact + "<p>For a problem with an order, include the product name and the email "
         "you used at checkout. Stripe, our payment processor and reseller, can also help "
         "with any payment question from the receipt they sent you.</p>"),
        ("refunds", "Refund policy",
         "<p>If a download is broken, missing, or not as described, you can get a full "
         "refund within 14 days of purchase. Contact us or reply to your Stripe receipt.</p>"
         "<p>Because downloads are delivered instantly, we don't otherwise offer refunds "
         "for change of mind.</p>"),
        ("terms", "Terms",
         "<p>PixelCo sells digital files: templates, checklists, planners and guides. "
         "Checkout is handled by Stripe, which acts as the reseller and merchant of record "
         "and handles payment, sales tax and receipts.</p>"
         "<p>After purchase you may use the files for your own personal and business work. "
         "Please don't resell or redistribute them as they are.</p>"
         "<p>Products, tools and guides are written with the help of AI and reviewed by "
         "automated checks. They are general information, not professional legal, financial "
         "or medical advice.</p>"),
        ("privacy", "Privacy",
         (("<p>This site shows ads from Google AdSense. Google and its partners may use cookies "
           "to show ads based on your visits to this and other sites. You can turn off "
           "personalized ads at <a href=\"https://adssettings.google.com\">Google Ads Settings</a>. "
           "See <a href=\"https://policies.google.com/technologies/ads\">how Google uses data "
           "from sites that show its ads</a>.</p><p>PixelCo itself has no accounts and no analytics. "
           "Our free tools run entirely in your browser and send nothing anywhere.</p>")
          if ads_head() else
          "<p>This site has no accounts, no cookies, no analytics and no tracking scripts. "
          "Our free tools run entirely in your browser and send nothing anywhere.</p>")
         + "<p>When you buy, payment details go directly to Stripe. PixelCo never sees your card "
         "details and does not store your name or email. See Stripe's privacy policy for how "
         "they handle your data.</p>"),
    ]
