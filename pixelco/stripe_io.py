"""Payments through Stripe, with Stripe as merchant of record (Managed Payments).

The agents create their own products and checkout links and read completed
sales back. They cannot move money out. Use a *restricted* key with only:
  Products: write, Prices: write, Payment Links: write, Checkout Sessions: read

Only sales from PixelCo's own checkout links are counted. Anything else on the
Stripe account (another app, another AI) is ignored.
"""
import os

import requests

API = "https://api.stripe.com/v1"
# Managed Payments on Payment Links needs this API version (Stripe changelog 2026-03-25).
MP_VERSION = "2026-03-25.preview"


class Stripe:
    def __init__(self, ledger, cfg=None):
        cfg = cfg or {}
        self.key = os.environ.get("STRIPE_KEY", "")
        self.ledger = ledger
        self.enabled = bool(self.key)
        self.managed = cfg.get("managed_payments", True)
        fees = cfg.get("fees", {})
        self.fee_pct = fees.get("percent", 0.064)   # 2.9% card + 3.5% Managed Payments
        self.fee_fixed = fees.get("fixed", 0.30)
        self.support_link = cfg.get("support_link_id", "")

    def _post(self, path, data, version=None):
        headers = {"Stripe-Version": version} if version else {}
        r = requests.post(f"{API}/{path}", data=data, auth=(self.key, ""),
                          headers=headers, timeout=60)
        if r.status_code >= 400:
            raise StripeError(r.json().get("error", {}).get("message", r.text[:300]))
        return r.json()

    def create_payment_link(self, item, price, redirect_url):
        try:
            prod = self._post("products", {
                "name": item["title"][:250],
                "description": (item.get("description") or item["title"])[:500],
                "metadata[pixelco_item]": item["id"],
            })
            pr = self._post("prices", {
                "product": prod["id"], "currency": "usd",
                "unit_amount": int(round(price * 100)),
            })
            data = {"line_items[0][price]": pr["id"], "line_items[0][quantity]": 1,
                    "metadata[pixelco_item]": item["id"],
                    "after_completion[type]": "redirect",
                    "after_completion[redirect][url]": redirect_url}
            if self.managed:
                data["managed_payments[enabled]"] = "true"
            link = self._post("payment_links", data, MP_VERSION if self.managed else None)
            self.ledger.event("cashier", f"checkout ready: {item['title']} at ${price:.2f}")
            return {"id": link["id"], "url": link["url"]}
        except (StripeError, requests.RequestException) as e:
            # No silent fallback: without Managed Payments you'd become the seller of record.
            self.ledger.event("cashier", f"Stripe refused checkout for {item['title']}: {e}")
            return None

    def sync_sales(self):
        """Book net revenue for completed checkouts on PixelCo's own links."""
        if not self.enabled:
            self.ledger.event("accountant", "no Stripe key yet, skipping sales sync")
            return
        by_link = {i["stripe_link"]: i for i in self.ledger.state["items"] if i.get("stripe_link")}
        params, new, ignored = {"limit": 100, "status": "complete"}, 0, 0
        while True:
            r = requests.get(f"{API}/checkout/sessions", params=params,
                             auth=(self.key, ""), timeout=60)
            if r.status_code >= 400:
                raise StripeError(r.json().get("error", {}).get("message", r.text[:300]))
            d = r.json()
            for s in d["data"]:
                if s.get("payment_status") != "paid":
                    continue
                link = s.get("payment_link")
                item = by_link.get(link)
                if not item and not (self.support_link and link == self.support_link):
                    ignored += 1
                    continue
                gross = (s.get("amount_total") or 0) / 100
                net = max(0.0, gross - (gross * self.fee_pct + self.fee_fixed))
                if self.ledger.record_sale(
                    s["id"], round(net, 2),
                    lane=item["lane"] if item else "tips",
                    item_id=item["id"] if item else None,
                    source=item["title"] if item else "tip",
                ):
                    new += 1
            if not d.get("has_more"):
                break
            params["starting_after"] = d["data"][-1]["id"]
        msg = f"sales sync: {new} new"
        if ignored:
            msg += f", {ignored} not PixelCo's (ignored)"
        self.ledger.event("accountant", msg)


class StripeError(Exception):
    pass
