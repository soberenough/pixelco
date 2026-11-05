"""Treasury and company state. Every dollar in or out goes through here.

The state file lives in the private vault repo (never the public one), so
revenue and history stay private. GitHub Actions is its only writer.
"""
import hashlib
import json
import os
import time
from pathlib import Path

STATE_PATH = Path(os.environ.get("PIXELCO_STATE", "vault/state.json"))


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _h(s):
    """One-way hash, so raw Stripe IDs are never stored."""
    return hashlib.sha256(str(s).encode()).hexdigest()[:20]


def default_state():
    return {
        "company": "PixelCo",
        "founded": _now(),
        "cycle": 0,
        "treasury": {"revenue": 0.0, "spend": 0.0, "seed": 0.0},
        "lanes": {},
        "items": [],
        "agents": {},
        "log": [],
        "growth": {"items_per_cycle": 1, "stage": "bootstrap"},
        "seen_sales": [],      # hashed sale IDs
        "processed": [],       # inbox files already handled
        "rejected": [],        # inbox files the guard refused, with reason
        "next_plan": None,     # written for the daily Claude session
    }


class Ledger:
    def __init__(self, path=None):
        self.path = Path(path or STATE_PATH)
        if self.path.exists():
            self.state = {**default_state(), **json.loads(self.path.read_text())}
        else:
            self.state = default_state()
        if os.environ.get("PIXELCO_SEED"):
            self.state["treasury"]["seed"] = float(os.environ["PIXELCO_SEED"])

    # ---------- money ----------
    @property
    def cash(self):
        t = self.state["treasury"]
        return round(t["revenue"] + t["seed"] - t["spend"], 4)

    @property
    def profit(self):
        t = self.state["treasury"]
        return round(t["revenue"] - t["spend"], 4)

    def can_spend(self, amount):
        return amount <= self.cash

    def spend(self, amount, reason):
        if not self.can_spend(amount):
            self.event("accountant", f"BLOCKED ${amount:.2f} for {reason} (cash ${self.cash:.2f})")
            return False
        self.state["treasury"]["spend"] += amount
        self.event("accountant", f"-${amount:.2f} for {reason}")
        return True

    def record_sale(self, sale_id, amount, lane=None, item_id=None, source=""):
        key = _h(sale_id)
        if key in self.state["seen_sales"]:
            return False
        self.state["seen_sales"].append(key)
        self.state["treasury"]["revenue"] += amount
        if lane:
            self.lane(lane)["revenue"] += amount
        if item_id:
            for it in self.state["items"]:
                if it["id"] == item_id:
                    it["revenue"] = round(it.get("revenue", 0) + amount, 4)
                    it["sales"] = it.get("sales", 0) + 1
        self.event("accountant", f"+${amount:.2f} from {source or lane or 'sale'}")
        return True

    # ---------- bookkeeping ----------
    def lane(self, name):
        return self.state["lanes"].setdefault(
            name, {"items": 0, "revenue": 0.0, "alive": True}
        )

    def has_item(self, item_id):
        return any(i["id"] == item_id for i in self.state["items"])

    def add_item(self, item):
        item.setdefault("created", _now())
        item.setdefault("revenue", 0.0)
        self.state["items"].append(item)
        self.lane(item["lane"])["items"] += 1

    def agent(self, name, status, task=""):
        self.state["agents"][name] = {"status": status, "task": task, "updated": _now()}

    def event(self, who, msg):
        print(f"[{who}] {msg}")
        self.state["log"].append({"t": _now(), "who": who, "msg": msg})
        self.state["log"] = self.state["log"][-300:]

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state["cash"] = self.cash
        self.state["profit"] = self.profit
        self.state["updated"] = _now()
        self.path.write_text(json.dumps(self.state, indent=2))
