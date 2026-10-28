"""Marketer/publisher. Rebuilds the storefront, policy pages, sitemap and RSS
each run so search engines and feed readers find new work. Organic only.
"""
import html as H
from pathlib import Path

from .lanes import SITE, page


def publish(ledger, cfg):
    items = ledger.state["items"]
    base = cfg.get("site_url", "").rstrip("/")

    def section(lane, anchor, label, blurb):
        rows = [i for i in items if i["lane"] == lane][::-1]
        if not rows:
            return ""
        lis = "".join(
            f'<li><a href="{i["url"]}">{H.escape(i["title"])}</a>'
            + (f' <span class=small>${i["price"]:.2f}</span>' if i.get("price") else "")
            + "</li>" for i in rows[:80])
        return f'<h2 id="{anchor}">{label}</h2><p class=small>{blurb}</p><ul class=items>{lis}</ul>'

    body = ("<h1>PixelCo</h1><p>Practical templates, free tools and guides, "
            "made and run by a small team of AI agents.</p>"
            + section("products", "shop", "Shop", "Instant downloads.")
            + section("tools", "tools", "Free tools", "Run in your browser. Nothing is sent anywhere.")
            + section("content", "guides", "Guides", "Plain answers to specific questions."))
    (SITE / "index.html").write_text(page("PixelCo", "Templates, free tools and guides.", body))

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
    ledger.event("marketer", f"storefront, policies, sitemap and feed updated ({len(items)} items)")


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
         "<p>This site has no accounts, no cookies, no analytics and no tracking scripts. "
         "Our free tools run entirely in your browser and send nothing anywhere.</p>"
         "<p>When you buy, payment details go directly to Stripe. PixelCo never sees your card "
         "details and does not store your name or email. See Stripe's privacy policy for how "
         "they handle your data.</p>"),
    ]
