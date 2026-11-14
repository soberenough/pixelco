"""Turn a kit's source files into files any buyer can open with no extra software.

Source files are written as Markdown (.md) and CSV. Most buyers have never seen a .md file:
double-clicked, it shows raw # and ** symbols and looks broken. So every kit ships as:

  - Word documents (.docx): editable in Microsoft Word, Google Docs, Apple Pages or LibreOffice
  - PDFs (.pdf) of the same documents: open on any phone, tablet or computer
  - Excel spreadsheets (.xlsx) instead of CSV: open in Excel, Google Sheets or Numbers,
    with a bold, frozen header row and sensible column widths
  - "START HERE" (from README.md) in both Word and PDF, plus LICENSE.txt

File names become readable titles ("proposal-template.md" -> "Proposal Template.docx"), and
every mention of the old file names inside the documents is updated to the new names.

Needs pandoc and LibreOffice (soffice) on the machine that builds the kits; the GitHub Action
installs them. If either is missing the kit is left unchanged rather than half-converted.
"""
import csv
import io
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

SMALL = {"and", "or", "of", "a", "an", "the", "to", "for", "in", "on", "vs"}
UPPER = {"faq", "csv", "pdf", "sow", "kpi", "roi"}


def friendly(stem):
    if stem.lower() in ("readme", "start-here", "start_here"):
        return "START HERE"
    words = re.split(r"[-_ ]+", stem)
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        out.append(lw.upper() if lw in UPPER else lw if (i and lw in SMALL) else lw.capitalize())
    return " ".join(out)


def tools_available():
    return bool(shutil.which("pandoc") and (shutil.which("soffice") or shutil.which("libreoffice")))


def _rename_refs(text, names):
    """Replace mentions of source file names with the new readable names.
    Inside fenced code blocks (e.g. folder diagrams) names are swapped as plain text, never bolded."""
    parts = re.split(r"(^```.*?^```[^\n]*$)", text, flags=re.S | re.M)
    out = []
    for i, part in enumerate(parts):
        code = i % 2 == 1
        for old, new in sorted(names.items(), key=lambda kv: -len(kv[0])):
            if code:
                part = re.sub(rf"(?<![\w/.-]){re.escape(old)}(?![\w-])(?!\.\w)", new, part)
            else:
                part = re.sub(rf"\*\*`?{re.escape(old)}`?\*\*|`{re.escape(old)}`|(?<![\w/.-]){re.escape(old)}(?![\w-])(?!\.\w)",
                              f"**{new}**", part)
        # Any other file name the buyer is told to create or look for: use the formats they actually have.
        part = re.sub(r"\b([\w-]+)\.md\b(?!\w)", r"\1.docx", part)
        part = re.sub(r"\b([\w-]+)\.csv\b(?!\w)", r"\1.xlsx", part)
        out.append(part)
    return "".join(out)


def _xlsx(csv_text):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook()
    ws = wb.active
    ws.title = "Tracker"
    rows = list(csv.reader(io.StringIO(csv_text)))
    for r in rows:
        ws.append([_num(v) for v in r])
    if rows:
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="2B3A7A")
            c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A2"
        for i, col in enumerate(zip(*rows), start=1):
            width = min(max(len(str(v)) for v in col) + 2, 45)
            ws.column_dimensions[ws.cell(1, i).column_letter].width = max(width, 10)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _num(v):
    try:
        return int(v) if re.fullmatch(r"-?\d+", v) else float(v) if re.fullmatch(r"-?\d+\.\d+", v) else v
    except ValueError:
        return v


def convert(files):
    """files: {name: text or bytes} -> {new_name: bytes}. Returns None if tools are missing."""
    if not tools_available():
        return None
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    names = {}
    for name in files:
        p = Path(name)
        if p.suffix.lower() == ".md":
            names[name] = friendly(p.stem)
        elif p.suffix.lower() == ".csv":
            names[name] = f"{friendly(p.stem)}.xlsx"
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        docx = []
        for name, body in files.items():
            p = Path(name)
            text = body.decode("utf-8", "replace") if isinstance(body, bytes) else body
            if p.suffix.lower() == ".md":
                stem = friendly(p.stem)
                src = t / f"{p.stem}.md"
                text = _rename_refs(text, names)
                if p.stem.lower() == "readme" and any(n.lower().endswith(".md") and n != name for n in files):
                    lines = text.split("\n", 1)
                    note = ("\n\n> **Where your files are:** the documents are in the **Word and PDF** folder. "
                            "Edit the Word (.docx) version in Word, Google Docs or Pages, or open the PDF to read "
                            "or print. Spreadsheets (.xlsx) open in Excel, Google Sheets or Numbers. "
                            "No extra software needed.\n")
                    text = lines[0] + note + (lines[1] if len(lines) > 1 else "")
                src.write_text(text, encoding="utf-8")
                dst = t / f"{stem}.docx"
                subprocess.run(["pandoc", str(src), "-f", "gfm-tex_math_dollars", "-o", str(dst)], check=True, timeout=120)
                docx.append(dst)
            elif p.suffix.lower() == ".csv":
                out[f"{friendly(p.stem)}.xlsx"] = _xlsx(text)
            elif name == "LICENSE.txt":
                continue  # added by the caller
            else:
                out[name] = body if isinstance(body, bytes) else body.encode("utf-8")
        if docx:
            pdfdir = t / "pdf"
            pdfdir.mkdir()
            subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(pdfdir), *map(str, docx)],
                           check=True, timeout=600, capture_output=True)
            for d in docx:
                pdf = pdfdir / (d.stem + ".pdf")
                if not pdf.exists():
                    return None  # never ship a half-converted kit
                folder = "" if d.stem == "START HERE" else "Word and PDF/"
                out[f"{folder}{d.stem}.docx"] = d.read_bytes()
                out[f"{folder}{d.stem}.pdf"] = pdf.read_bytes()
    return out


LICENSE = ("You may use these files for personal and business work.\n"
           "Please don't resell or share them as-is.\n\n"
           "Opening the files: the .docx files open in Microsoft Word, Google Docs (free), Apple Pages (free)\n"
           "or LibreOffice (free); the .pdf files open on any phone, tablet or computer; the .xlsx\n"
           "spreadsheets open in Excel, Google Sheets (free) or Numbers (free).\n")


def build_zip(files, top=""):
    """Zip a kit, converted for buyers when possible. files: {name: text or bytes}."""
    conv = convert(files) or {k: (v if isinstance(v, bytes) else v.encode("utf-8"))
                              for k, v in files.items() if k != "LICENSE.txt"}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(conv):
            z.writestr(f"{top}{name}", conv[name])
        z.writestr(f"{top}LICENSE.txt", LICENSE)
    return buf.getvalue(), sorted(conv) + ["LICENSE.txt"]


PACKAGING_VERSION = 2   # bump when a packaging fix should be re-applied to published kits


def needs_upgrade(zip_bytes):
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        return any(n.lower().endswith((".md", ".csv")) for n in z.namelist())


def upgrade_zip(zip_bytes):
    """Re-package an already-published kit in place (same download link). None if nothing to do."""
    if not needs_upgrade(zip_bytes) or not tools_available():
        return None
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        top = ""
        if names and all("/" in n for n in names) and len({n.split("/")[0] for n in names}) == 1:
            top = names[0].split("/")[0] + "/"
        files = {n[len(top):]: z.read(n) for n in names}
    if convert(files) is None:
        return None
    return build_zip(files, top)


def sources_from_zip(zip_bytes):
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        top = ""
        if names and all("/" in n for n in names) and len({n.split("/")[0] for n in names}) == 1:
            top = names[0].split("/")[0] + "/"
        return {n[len(top):]: z.read(n) for n in names}, top


def upgrade_published(items, site, src_dir=None):
    """Re-package published kits, in place (same download link). A kit is rebuilt when it still
    ships .md/.csv files, or when its original sources are in src_dir and it was packaged by an
    older PACKAGING_VERSION. Returns the number of kits rebuilt; updates "files" and "pack_v"."""
    done = 0
    for it in items:
        if it.get("lane") != "products" or not it.get("dl"):
            continue
        slug = it.get("url", "").strip("/").split("/")[-1]
        z = Path(site) / "dl" / it["dl"] / f"{slug}.zip"
        if not z.exists():
            continue
        src = Path(src_dir) / f"{slug}.zip" if src_dir else None
        res = None
        if src and src.exists() and it.get("pack_v", 0) < PACKAGING_VERSION:
            files, top = sources_from_zip(src.read_bytes())
            if convert(files) is not None:
                res = build_zip(files, top)
        if res is None:
            res = upgrade_zip(z.read_bytes())
        if res:
            z.write_bytes(res[0])
            it["files"] = res[1]
            done += 1
        if res or not needs_upgrade(z.read_bytes()):
            if src and src.exists():
                it["pack_v"] = PACKAGING_VERSION
    return done
