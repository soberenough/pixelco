"""Which checkout a buyer sees for a product.

Gumroad listings (config.yaml `gumroad.products`) win: Gumroad takes the payment
itself, so those kits are buyable today without a live Stripe key. Otherwise a
live-mode Stripe link is shown. A Stripe *test-mode* link is never shown in
public: it would let anyone pay with a test card and download the kit for free.
"""
from functools import lru_cache
from pathlib import Path

import yaml


@lru_cache(maxsize=1)
def _cfg():
    p = Path("config.yaml")
    return yaml.safe_load(p.read_text()) if p.exists() else {}


def _slug(item):
    i = item.get("id", "")
    return i[len("product-"):] if i.startswith("product-") else i


def gumroad_url(item, cfg=None):
    g = (cfg if cfg is not None else _cfg()).get("gumroad") or {}
    return (g.get("products") or {}).get(_slug(item)) or None


def is_live_stripe(item):
    url = item.get("buy_url") or ""
    mode = item.get("stripe_mode") or ("test" if "/test_" in url else "live")
    return bool(url) and mode == "live"


def buy_link(item, cfg=None):
    """(url, processor) for the public Buy button, or (None, None)."""
    g = gumroad_url(item, cfg)
    if g:
        return g, "Gumroad"
    if is_live_stripe(item):
        return item["buy_url"], "Stripe"
    return None, None
