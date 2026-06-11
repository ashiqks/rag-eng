"""Generate Vertex AI Search metadata.jsonl from HTML files in a GCS bucket.

Scans every .html object under a GCS prefix (recursively) and emits one JSONL
line per page in the schema Vertex AI Search expects:

    {"id": "...", "structData": {...}, "content": {"mimeType": "text/html", "uri": "gs://..."}}

Conventions
-----------
- ``id`` is derived from the file name (without the ``.html`` suffix).
- ``source_type`` is the FIRST path segment under the bucket root (e.g.
  ``gs://my-bucket/confluence/foo.html`` -> ``confluence``).
- ``structData`` is populated from in-page metadata: every ``<meta name="..."
  content="...">`` tag, plus an optional JSON blob embedded as
  ``<script type="application/json" id="vais-metadata">{...}</script>``.
  The JSON-blob form wins on conflict (richer types, lists, numbers).
- ``title`` falls back to the HTML ``<title>`` tag if not provided in metadata.

Usage
-----
    python generate_metadata_from_gcs.py \
        --bucket gap-genai-discovery-corpus-html \
        --prefix ""                                  \
        --out metadata.jsonl

    # Or scope to a single source folder:
    python generate_metadata_from_gcs.py \
        --bucket gap-genai-discovery-corpus-html \
        --prefix confluence/                          \
        --out metadata_confluence.jsonl

Requires: google-cloud-storage, beautifulsoup4, lxml
    pip install google-cloud-storage beautifulsoup4 lxml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import PurePosixPath
from typing import Any

from bs4 import BeautifulSoup
from google.cloud import storage


def parse_html_metadata(html: str) -> dict[str, Any]:
    """Extract structData from <meta> tags and an optional embedded JSON blob."""
    soup = BeautifulSoup(html, "lxml")
    data: dict[str, Any] = {}

    for meta in soup.find_all("meta"):
        name = meta.get("name") or meta.get("property")
        content = meta.get("content")
        if name and content is not None:
            data[name] = content

    if (title_tag := soup.find("title")) and title_tag.string:
        data.setdefault("title", title_tag.string.strip())

    blob = soup.find("script", {"type": "application/json", "id": "vais-metadata"})
    if blob and blob.string:
        try:
            data.update(json.loads(blob.string))
        except json.JSONDecodeError as e:
            print(f"  WARN: invalid JSON in vais-metadata block: {e}", file=sys.stderr)

    return data


def derive_id_and_source(blob_name: str) -> tuple[str, str]:
    """Return (doc_id, source_type) from the GCS object name."""
    path = PurePosixPath(blob_name)
    doc_id = path.stem
    source_type = path.parts[0] if len(path.parts) > 1 else "root"
    return doc_id, source_type


def build_record(bucket_name: str, blob: storage.Blob) -> dict[str, Any]:
    doc_id, source_type = derive_id_and_source(blob.name)
    html = blob.download_as_text()
    struct = parse_html_metadata(html)
    struct.setdefault("source_type", source_type)
    struct.setdefault("gcs_path", f"gs://{bucket_name}/{blob.name}")
    return {
        "id": doc_id,
        "structData": struct,
        "content": {
            "mimeType": "text/html",
            "uri": f"gs://{bucket_name}/{blob.name}",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bucket", required=True, help="GCS bucket name (no gs:// prefix).")
    ap.add_argument("--prefix", default="", help="Object name prefix (default: bucket root).")
    ap.add_argument("--out", default="metadata.jsonl", help="Output JSONL file path.")
    ap.add_argument(
        "--project",
        default=None,
        help="GCP project for billing (defaults to ADC quota project).",
    )
    args = ap.parse_args()

    client = storage.Client(project=args.project)
    bucket = client.bucket(args.bucket)

    written = skipped = 0
    with open(args.out, "w", encoding="utf-8") as f:
        for blob in client.list_blobs(bucket, prefix=args.prefix):
            if not blob.name.lower().endswith(".html"):
                skipped += 1
                continue
            try:
                record = build_record(args.bucket, blob)
            except Exception as e:
                print(f"  ERROR on {blob.name}: {e}", file=sys.stderr)
                skipped += 1
                continue
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
            if written % 100 == 0:
                print(f"  ...{written} records written", file=sys.stderr)

    print(f"Done. Wrote {written} records to {args.out} (skipped {skipped}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
