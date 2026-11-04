"""One business day, run by GitHub Actions from the main branch.

  1. Accountant syncs sales from Stripe.
  2. Gatekeeper reads new item files from the `inbox` branch AS DATA ONLY
     (nothing on that branch is ever executed), checks each, and builds the
     ones that pass.
  3. Cashier retries any product still waiting for a checkout link.
  4. Marketer rebuilds the storefront.
  5. CEO plans tomorrow for the daily Claude session.

  python -m pixelco.run                    # normal run (reads origin/inbox)
  python -m pixelco.run --inbox-dir DIR    # local testing from a folder
"""
import argparse
import json
import subprocess
import traceback
from pathlib import Path

import yaml

from . import guard
from .lanes import BUILD, attach_checkout, bundle_parts, link_mode, reset_checkout
from .ledger import Ledger
from .publisher import publish
from .strategist import plan
from .stripe_io import Stripe

AGENT = {"content": "writer", "tools": "builder", "products": "maker"}
MAX_FILE = 600_000


def inbox_from_git(ref="origin/inbox"):
    try:
        subprocess.run(["git", "fetch", "--quiet", "origin", "inbox:refs/remotes/origin/inbox"],
                       check=True, capture_output=True)
    except subprocess.CalledProcessError:
        return []
    names = subprocess.run(["git", "ls-tree", "-r", "--name-only", ref, "--", "queue/"],
                           capture_output=True, text=True).stdout.split()
    out = []
    for n in sorted(names):
        if not n.endswith(".json"):
            continue
        blob = subprocess.run(["git", "show", f"{ref}:{n}"], capture_output=True).stdout
        out.append((n, blob))
    return out


def inbox_from_dir(d):
    return [(str(p.relative_to(d)), p.read_bytes()) for p in sorted(Path(d).rglob("*.json"))]


def business_day(cfg, inbox):
    led = Ledger()
    led.state["cycle"] += 1
    led.event("ceo", f"--- day {led.state['cycle']} --- cash ${led.cash:.2f}")
    led.state["alerts"] = []
    stripe = Stripe(led, cfg.get("stripe", {}))
    if stripe.enabled:
        problem = stripe.check_key()
        if problem:
            led.alert(f"Stripe key rejected ({stripe.mode} mode), checkouts left as they were: {problem}")
            stripe.enabled = False
    if stripe.enabled and stripe.mode == "live" and not led.state.get("live_since"):
        led.go_live()

    led.agent("accountant", "working", "syncing sales")
    try:
        stripe.sync_sales()
    except Exception as e:
        led.event("accountant", f"sales sync failed: {e}")
    led.agent("accountant", "idle", f"cash ${led.cash:.2f}")

    done = set(led.state["processed"])
    for name, blob in inbox:
        if name in done:
            continue
        led.state["processed"].append(name)
        try:
            if len(blob) > MAX_FILE:
                raise guard.Rejected("file too large")
            spec = guard.check(json.loads(blob))
            item_id = {"content": "content-", "tools": "tool-", "products": "product-"}[spec["lane"]] + spec["slug"]
            if led.has_item(item_id):
                raise guard.Rejected("duplicate slug")
            try:
                bundle_parts(spec, led)
            except ValueError as e:
                raise guard.Rejected(str(e))
        except Exception as e:  # any bad inbox file is rejected, never fatal
            led.state["rejected"].append({"file": name, "why": str(e)})
            led.event("gatekeeper", f"rejected {name}: {e}")
            continue
        who = AGENT[spec["lane"]]
        led.agent(who, "working", spec["title"])
        try:
            item = BUILD[spec["lane"]](spec, led, cfg, stripe)
            led.add_item(item)
            led.event(who, f"shipped: {item['title']}")
        except Exception as e:
            led.event(who, f"failed to build {name}: {e}")
            traceback.print_exc()
        led.agent(who, "idle", "")

    for item in led.state["items"]:
        if item["lane"] != "products":
            continue
        if stripe.enabled and item.get("buy_url") and link_mode(item) != stripe.mode:
            problem = reset_checkout(item)
            led.event("cashier", f"moving {item['title']} to a {stripe.mode}-mode checkout")
            if problem:
                led.alert(problem)
        if not item.get("buy_url"):
            try:
                attach_checkout(item, cfg, stripe, led)
            except Exception as e:  # one bad item must not lose the whole run
                led.alert(f"checkout setup failed for {item.get('id')}: {e}")

    led.agent("marketer", "working", "publishing")
    publish(led, cfg)
    led.agent("marketer", "idle", "")

    led.agent("ceo", "working", "planning tomorrow")
    plan(led, cfg.get("strategy", {}))
    led.agent("ceo", "idle", led.state["growth"]["stage"])
    led.state["rejected"] = led.state["rejected"][-50:]
    led.save()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--inbox-dir")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config))
    inbox = inbox_from_dir(a.inbox_dir) if a.inbox_dir else inbox_from_git()
    business_day(cfg, inbox)


if __name__ == "__main__":
    main()
