"""Run the gatekeeper on item files before pushing them.

  python -m pixelco.check queue/2026-10-28/*.json
"""
import json
import sys

from .guard import Rejected, check


def main(paths):
    bad = 0
    for p in paths:
        try:
            spec = check(json.load(open(p)))
            print(f"PASS  {p}  ({spec['lane']}: {spec['title']})")
        except (Rejected, ValueError) as e:
            bad += 1
            print(f"FAIL  {p}  {e}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
