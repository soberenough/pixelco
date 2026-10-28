"""The CEO. Decides tomorrow's work and how fast to grow.

Allocation is Thompson sampling on revenue-per-item, so lanes that earn get
more work while every live lane still gets tested (15% exploration floor).
A lane that ships `kill_after` items with $0 revenue is shut down. If every
lane dies, the CEO revives them all.

The result is written to state["next_plan"], which the daily Claude session
reads to know what to make.
"""
import json
import random
import time

STAGES = [  # (min cash, stage, items per day)
    (0, "bootstrap", 2),
    (25, "traction", 3),
    (100, "growth", 4),
    (500, "scale", 6),
    (2000, "expansion", 8),
]
LANES = ["content", "tools", "products"]


def plan(ledger, cfg, rng=random):
    st = ledger.state
    kill_after = cfg.get("kill_after", 12)

    for name in LANES:
        L = ledger.lane(name)
        if L["alive"] and L["items"] >= kill_after and L["revenue"] == 0:
            L["alive"] = False
            ledger.event("ceo", f"shutting down lane '{name}' (no sales after {L['items']} items)")
    alive = [n for n in LANES if ledger.lane(n)["alive"]]
    if not alive:
        for n in LANES:
            ledger.lane(n).update(alive=True, items=0)
        alive = list(LANES)
        ledger.event("ceo", "every lane failed, restarting all of them with fresh ideas")

    stage, per_day = "bootstrap", 2
    for floor, s, n in STAGES:
        if ledger.cash >= floor:
            stage, per_day = s, n
    per_day = min(per_day, cfg.get("max_items_per_day", 8))
    if stage != st["growth"]["stage"]:
        ledger.event("ceo", f"growth stage: {st['growth']['stage']} -> {stage}")
    st["growth"] = {"items_per_cycle": per_day, "stage": stage}

    explore = cfg.get("explore", 0.15)
    picks = []
    for _ in range(per_day):
        if rng.random() < explore:
            picks.append(rng.choice(alive))
            continue
        best = max(alive, key=lambda n: rng.gammavariate(
            1 + ledger.lane(n)["revenue"], 1 / (1 + ledger.lane(n)["items"])))
        picks.append(best)

    st["next_plan"] = {
        "made": time.strftime("%Y-%m-%d", time.gmtime()),
        "stage": stage,
        "slots": picks,
        "brief": brief(ledger),
    }
    ledger.event("ceo", f"tomorrow ({stage}): {', '.join(picks)}")
    return picks


def brief(ledger):
    items = ledger.state["items"]
    winners = sorted((i for i in items if i.get("revenue", 0) > 0),
                     key=lambda i: -i["revenue"])[:8]
    return {
        "already_made": [f"{i['lane']}: {i['title']}" for i in items][-60:],
        "best_sellers": [{"title": i["title"], "lane": i["lane"], "revenue": i["revenue"],
                          "price": i.get("price")} for i in winners],
        "lanes": ledger.state["lanes"],
        "recent_rejections": ledger.state.get("rejected", [])[-5:],
    }
