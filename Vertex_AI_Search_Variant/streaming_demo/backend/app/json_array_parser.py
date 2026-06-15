"""Incremental parser for a streamed top-level JSON array.

Discovery Engine `:streamAnswer` returns a single JSON array whose elements
arrive on the wire as the model generates. We yield each element the moment
its closing brace lands, then trim the buffer so memory stays bounded across
long answers.

Differences from the version in the public guide:
- After yielding, the buffer is trimmed up to and including the closing `}`,
  so the working buffer never grows past the in-progress object.
- Surrogate decoding errors in the upstream are tolerated: malformed top-level
  objects are logged and skipped rather than aborting the stream.
"""

from __future__ import annotations

import json
import logging
from typing import Iterator

log = logging.getLogger(__name__)


class JsonArrayParser:
    def __init__(self) -> None:
        self.buf: str = ""
        self.depth: int = 0
        self.in_str: bool = False
        self.esc: bool = False
        self.start: int = -1

    def feed(self, chunk: str) -> Iterator[dict]:
        if not chunk:
            return
        scan_from = len(self.buf)
        self.buf += chunk
        i = scan_from
        while i < len(self.buf):
            c = self.buf[i]
            if self.in_str:
                if self.esc:
                    self.esc = False
                elif c == "\\":
                    self.esc = True
                elif c == '"':
                    self.in_str = False
            elif c == '"':
                self.in_str = True
            elif c == "{":
                if self.depth == 0:
                    self.start = i
                self.depth += 1
            elif c == "}":
                self.depth -= 1
                if self.depth == 0 and self.start >= 0:
                    raw = self.buf[self.start : i + 1]
                    self.start = -1
                    try:
                        yield json.loads(raw)
                    except json.JSONDecodeError as e:
                        log.warning("malformed JSON object skipped: %s", e)
                    # Trim emitted bytes so the buffer stays small across long
                    # answers. We're between top-level objects (depth==0,
                    # start==-1) so it's safe to drop everything up to and
                    # including this closing brace.
                    self.buf = self.buf[i + 1 :]
                    i = -1
            i += 1
