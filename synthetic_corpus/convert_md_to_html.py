"""
Convert the synthetic Confluence corpus from Markdown to HTML.

Vertex AI Search unstructured data stores accept HTML, PDF, TXT, DOCX, PPTX,
XLSX -- but NOT .md. This script reads every pages/*.md, parses its YAML
front-matter, converts the Markdown body to HTML, and writes pages/*.html.

It also emits `metadata.jsonl` next to the pages/ folder, ready for use as
the metadata sidecar in a Discovery Engine `documents.import` call:

    {"id": "TLCOE-2010001",
     "structData": { ...front-matter fields... },
     "content": {"mimeType": "text/html",
                 "uri": "gs://<bucket>/pages/TLCOE-2010001.html"}}

Usage:
    python convert_md_to_html.py                       # converts in place, keeps .md
    python convert_md_to_html.py --delete-md           # converts and removes .md
    python convert_md_to_html.py --gcs-prefix gs://...

This file has no third-party dependencies.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

PAGES_DIR_NAME = "pages"

# ---------------------------------------------------------------------------
# YAML front-matter parser (handles the subset used by generate.py)
# ---------------------------------------------------------------------------

_LIST_KEYS = {"secondary_kpis", "related_test_ids"}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (metadata_dict, body_markdown)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_block = text[3:end].strip("\n")
    body = text[end + 4 :].lstrip("\n")

    meta: dict[str, object] = {}
    current_list_key: str | None = None
    for raw in fm_block.splitlines():
        if not raw.strip():
            current_list_key = None
            continue
        if raw.startswith("  - "):
            if current_list_key:
                meta.setdefault(current_list_key, []).append(raw[4:].strip())
            continue
        if raw.startswith("  []"):
            if current_list_key:
                meta[current_list_key] = []
            continue
        if ":" not in raw:
            current_list_key = None
            continue
        key, _, val = raw.partition(":")
        key = key.strip()
        val = val.strip()
        if key in _LIST_KEYS and val == "":
            current_list_key = key
            meta[key] = []
            continue
        current_list_key = None
        # strip surrounding quotes
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
            val = val[1:-1]
        # coerce ints/floats
        if re.fullmatch(r"-?\d+", val):
            meta[key] = int(val)
        elif re.fullmatch(r"-?\d+\.\d+", val):
            meta[key] = float(val)
        else:
            meta[key] = val
    return meta, body


# ---------------------------------------------------------------------------
# Markdown -> HTML converter (subset matching generate.py output)
# Supports: ATX headings, blockquotes, pipe tables, bullet lists,
#           bold (**), italic (*, _), inline code (`), thematic break ---,
#           paragraphs. No nested lists, no code fences.
# ---------------------------------------------------------------------------

_INLINE_PATTERNS = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"(?<!\w)_(.+?)_(?!\w)"), r"<em>\1</em>"),
    (re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)"), r"<em>\1</em>"),
    (re.compile(r"`([^`]+)`"), r"<code>\1</code>"),
    (re.compile(r"\[([^\]]+)\]\(([^)]+)\)"), r'<a href="\2">\1</a>'),
]


def _inline(text: str) -> str:
    text = html.escape(text, quote=False)
    # un-escape backticks we just escaped? No, escape() leaves them alone.
    for pat, repl in _INLINE_PATTERNS:
        text = pat.sub(repl, text)
    return text


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)

    def flush_paragraph(buf: list[str]) -> None:
        if buf:
            joined = " ".join(s.strip() for s in buf).strip()
            if joined:
                out.append(f"<p>{_inline(joined)}</p>")

    while i < n:
        line = lines[i]
        stripped = line.rstrip()

        # blank line
        if not stripped.strip():
            i += 1
            continue

        # horizontal rule
        if re.fullmatch(r"-{3,}", stripped.strip()):
            out.append("<hr/>")
            i += 1
            continue

        # heading
        m = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if m:
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2).strip())}</h{level}>")
            i += 1
            continue

        # blockquote (consecutive `>` lines)
        if stripped.startswith(">"):
            block = []
            while i < n and lines[i].lstrip().startswith(">"):
                block.append(lines[i].lstrip()[1:].strip())
                i += 1
            inner = "<br/>".join(_inline(b) for b in block if b)
            out.append(f"<blockquote>{inner}</blockquote>")
            continue

        # pipe table  (header line followed by separator |---|---|)
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\|[\s\-:|]+\|\s*$", lines[i + 1]):
            header_cells = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows: list[list[str]] = []
            while i < n and lines[i].lstrip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            thead = "".join(f"<th>{_inline(c)}</th>" for c in header_cells)
            body_rows = "".join(
                "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>"
                for r in rows
            )
            out.append(
                f"<table><thead><tr>{thead}</tr></thead><tbody>{body_rows}</tbody></table>"
            )
            continue

        # bullet list  ("- " or "* ")
        if re.match(r"^[-*]\s+", stripped):
            items: list[str] = []
            while i < n and re.match(r"^[-*]\s+", lines[i].rstrip()):
                items.append(re.sub(r"^[-*]\s+", "", lines[i].rstrip()))
                i += 1
            li = "".join(f"<li>{_inline(it)}</li>" for it in items)
            out.append(f"<ul>{li}</ul>")
            continue

        # paragraph (until blank line or block element)
        para: list[str] = []
        while i < n and lines[i].strip() and not re.match(
            r"^(#{1,6} |>|\||[-*]\s+|-{3,}$)", lines[i].rstrip()
        ):
            para.append(lines[i])
            i += 1
        flush_paragraph(para)

    return "\n".join(out)


# ---------------------------------------------------------------------------
# HTML document wrapper with metadata as <meta> tags + JSON-LD
# ---------------------------------------------------------------------------

def render_html_document(meta: dict, body_html: str) -> str:
    title = html.escape(str(meta.get("title", meta.get("confluence_page_id", "GAP T&L COE Test Report"))))
    canonical = html.escape(str(meta.get("confluence_url", "")), quote=True)

    # Per-field <meta> tags (Vertex AI Search may surface these as field-level metadata)
    meta_tags: list[str] = []
    for k, v in meta.items():
        if isinstance(v, list):
            content = ", ".join(str(x) for x in v)
        else:
            content = str(v)
        meta_tags.append(
            f'<meta name="{html.escape(k)}" content="{html.escape(content, quote=True)}"/>'
        )

    # Full metadata as JSON-LD for downstream parsers
    json_ld = html.escape(json.dumps(meta, ensure_ascii=False), quote=False)

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8"/>\n'
        f"  <title>{title}</title>\n"
        + (f'  <link rel="canonical" href="{canonical}"/>\n' if canonical else "")
        + "  " + "\n  ".join(meta_tags) + "\n"
        f'  <script type="application/ld+json">{json_ld}</script>\n'
        "</head>\n"
        "<body>\n"
        f"{body_html}\n"
        "</body>\n"
        "</html>\n"
    )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default=PAGES_DIR_NAME, help="folder containing .md files")
    ap.add_argument("--delete-md", action="store_true", help="remove .md files after successful conversion")
    ap.add_argument(
        "--gcs-prefix",
        default="gs://gap-genai-discovery-corpus-md/pages",
        help="GCS URI prefix used in metadata.jsonl content.uri",
    )
    args = ap.parse_args()

    root = Path(__file__).parent
    pages_dir = root / args.pages
    md_files = sorted(pages_dir.glob("*.md"))
    if not md_files:
        print(f"No .md files found in {pages_dir}")
        return

    manifest: list[dict] = []
    for md_path in md_files:
        text = md_path.read_text(encoding="utf-8")
        meta, body_md = parse_frontmatter(text)
        body_html = md_to_html(body_md)
        doc = render_html_document(meta, body_html)

        html_path = md_path.with_suffix(".html")
        html_path.write_text(doc, encoding="utf-8")

        doc_id = str(meta.get("confluence_page_id") or md_path.stem)
        manifest.append({
            "id": doc_id,
            "structData": meta,
            "content": {
                "mimeType": "text/html",
                "uri": f"{args.gcs_prefix.rstrip('/')}/{html_path.name}",
            },
        })

        if args.delete_md:
            md_path.unlink()

    (root / "metadata.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in manifest) + "\n",
        encoding="utf-8",
    )

    print(f"Converted {len(md_files)} files -> {pages_dir}/*.html")
    print(f"Wrote manifest -> {root / 'metadata.jsonl'}")
    if args.delete_md:
        print("Removed original .md files.")


if __name__ == "__main__":
    main()
