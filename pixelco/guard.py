"""The gatekeeper. Everything the AI writes is checked here before it can
go live. It rejects rather than repairs: a refused item is logged and
skipped, and the company carries on.

What it stops:
  - scripts, frames, forms, or tracking that could harm or spy on visitors
  - any outside URL inside a tool (tools must run fully offline)
  - risky file names or types in product downloads
  - oversize content, missing fields, prices outside the allowed range
"""
import re

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{2,59}$")
FILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,59}\.(md|csv|txt)$")

# Never allowed anywhere
BANNED_ANY = [
    (r"<\s*iframe", "frames"), (r"<\s*object", "embedded objects"),
    (r"<\s*embed", "embedded objects"), (r"<\s*base\b", "base tag"),
    (r"<\s*link\b", "external stylesheet/link tag"),
    (r"<\s*meta\b(?![^>]*(charset|name\s*=\s*[\"']viewport))", "meta tags other than charset/viewport"),
    (r"<\s*form\b", "forms"), (r"javascript\s*:", "javascript: URLs"),
    (r"document\.cookie", "cookie access"),
    (r"\bdata:\s*text/html", "embedded HTML documents"),
]
# Articles: plain reading pages, no code at all
BANNED_ARTICLE = [
    (r"<\s*script", "scripts"), (r"<\s*style", "custom styles"),
    (r"\son[a-z]+\s*=", "inline event handlers"),
    (r"\ssrc\s*=", "embedded external media"),
]
# Tools: inline code allowed, but no network or outside resources
BANNED_TOOL = [
    (r"https?://", "outside URLs"), (r"//[a-z0-9.-]+\.[a-z]{2,}", "outside URLs"),
    (r"<\s*script[^>]*\ssrc\s*=", "external scripts"),
    (r"\bfetch\s*\(", "network calls"), (r"XMLHttpRequest", "network calls"),
    (r"WebSocket", "network calls"), (r"sendBeacon", "network calls"),
    (r"EventSource", "network calls"), (r"\bimport\s*\(", "dynamic imports"),
    (r"\beval\s*\(", "eval"), (r"new\s+Function\s*\(", "eval"),
    (r"\bWorker\s*\(", "workers"), (r"window\.open", "pop-ups"),
    (r"\blocation\s*(\.href)?\s*=(?!=)", "redirects"), (r"\.submit\s*\(", "form submits"),
    (r"<\s*img[^>]*\ssrc\s*=\s*[\"'](?!data:)", "outside images"),
]

CSP = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
       "img-src data:; font-src data:; form-action 'none'; base-uri 'none'")

LIMITS = {"content": 80_000, "tools": 120_000}


class Rejected(Exception):
    pass


def _scan(text, rules):
    for pat, why in rules:
        if re.search(pat, text, re.I):
            raise Rejected(f"contains {why}")


def _text(spec, key, maxlen, required=True):
    v = spec.get(key, "")
    if not isinstance(v, str) or (required and not v.strip()):
        raise Rejected(f"missing {key}")
    if len(v) > maxlen:
        raise Rejected(f"{key} too long")
    if re.search(r"[<>]", v) and key in ("title", "description"):
        raise Rejected(f"{key} contains markup")
    return v.strip()


def check(spec):
    """Return a cleaned copy of the spec or raise Rejected."""
    if not isinstance(spec, dict):
        raise Rejected("not an object")
    lane = spec.get("lane")
    if lane not in ("content", "tools", "products"):
        raise Rejected(f"unknown lane {lane!r}")
    slug = spec.get("slug", "")
    if not isinstance(slug, str) or not SLUG.match(slug):
        raise Rejected("bad slug")
    out = {"lane": lane, "slug": slug,
           "title": _text(spec, "title", 120),
           "description": _text(spec, "description", 500)}

    if lane in ("content", "tools"):
        html = _text(spec, "html", LIMITS[lane])
        _scan(html, BANNED_ANY)
        if lane == "content":
            _scan(html, BANNED_ARTICLE)
            # every outside link must be plain https
            for href in re.findall(r"href\s*=\s*[\"']([^\"']*)", html, re.I):
                internal = re.match(r"^\.\./\.\./(tools|shop|blog)/[a-z0-9-]+/$", href)
                if not (href.startswith("https://") or href.startswith("#") or internal):
                    raise Rejected(f"link not allowed: {href[:60]}")
        else:
            _scan(html, BANNED_TOOL)
            if not re.match(r"\s*<!doctype html>", html, re.I) or not re.search(r"<head[^>]*>", html, re.I):
                raise Rejected("tool must be a full HTML document with <head>")
        out["html"] = html

    if lane == "products":
        try:
            price = float(spec.get("price"))
        except (TypeError, ValueError):
            raise Rejected("bad price")
        if not 5 <= price <= 49:
            raise Rejected("price outside $5-$49")
        files = spec.get("files")
        if not isinstance(files, dict) or not 1 <= len(files) <= 10:
            raise Rejected("needs 1-10 files")
        clean = {}
        for name, body in files.items():
            if not FILE.match(name or ""):
                raise Rejected(f"file name not allowed: {str(name)[:40]}")
            if not isinstance(body, str) or not body.strip() or len(body) > 100_000:
                raise Rejected(f"file {name} empty or too big")
            _scan(body, BANNED_ANY + [(r"<\s*script", "scripts")])
            clean[name] = body
        out["price"] = round(price, 2)
        out["files"] = clean
    return out


def lock_tool(html):
    """Insert a Content-Security-Policy as the first thing in <head>, so the
    browser itself blocks any network access the scanner missed."""
    tag = f'<meta http-equiv="Content-Security-Policy" content="{CSP}">'
    return re.sub(r"(<head[^>]*>)", r"\1" + tag, html, count=1, flags=re.I)
