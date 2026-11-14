"""Keep each kit's original source files (Markdown/CSV) in the private vault, so packaging
fixes can always be re-applied to published kits from the originals.

    python -m pixelco.sources <vault-dir>

For every product in state.json without vault/src/<slug>.zip, walk the vault's git history
(newest first) for the last published zip of that kit that still held the .md/.csv sources,
and save it as vault/src/<slug>.zip. Needs a full-history checkout of the vault.
"""
import json
import subprocess
import sys
from pathlib import Path
import io
import zipfile


def _has_sources(b):
    try:
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            return any(n.lower().endswith(".md") for n in z.namelist())
    except zipfile.BadZipFile:
        return False


def recover(vault):
    vault = Path(vault)
    state = json.loads((vault / "state.json").read_text())
    src = vault / "src"
    src.mkdir(exist_ok=True)
    missing = [i["url"].strip("/").split("/")[-1] for i in state["items"]
               if i.get("lane") == "products" and i.get("url")]
    missing = [s for s in missing if not (src / f"{s}.zip").exists()]
    if not missing:
        return 0
    git = lambda *a: subprocess.run(["git", "-C", str(vault), *a], capture_output=True, check=True).stdout
    commits = git("log", "--format=%H", "--", "dl").decode().split()
    found = 0
    for c in commits:
        if not missing:
            break
        paths = git("ls-tree", "-r", "--name-only", c, "dl").decode().splitlines()
        for slug in list(missing):
            for p in paths:
                if p.endswith(f"/{slug}.zip"):
                    b = git("show", f"{c}:{p}")
                    if _has_sources(b):
                        (src / f"{slug}.zip").write_bytes(b)
                        missing.remove(slug)
                        found += 1
                    break
    # Kits built after packaging started have converted zips only: their sources are the
    # product specs on the pixelco repo's inbox branch (the repo this runs in).
    if missing:
        try:
            run = lambda *a: subprocess.run(["git", *a], capture_output=True, check=True).stdout
            run("fetch", "--quiet", "origin", "inbox:refs/remotes/origin/inbox")
            for n in run("ls-tree", "-r", "--name-only", "origin/inbox", "--", "queue/").decode().split():
                if not n.endswith(".json"):
                    continue
                for slug in list(missing):
                    if n.endswith(f"products-{slug}.json"):
                        spec = json.loads(run("show", f"origin/inbox:{n}"))
                        buf = io.BytesIO()
                        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                            for name, body in spec.get("files", {}).items():
                                z.writestr(name, body)
                        (src / f"{slug}.zip").write_bytes(buf.getvalue())
                        missing.remove(slug)
                        found += 1
        except (subprocess.CalledProcessError, ValueError) as e:
            print("inbox lookup failed:", e)
    if missing:
        print("no sources found for:", ", ".join(missing))
    return found


if __name__ == "__main__":
    print("recovered sources for", recover(sys.argv[1] if len(sys.argv) > 1 else "vault"), "kits")
