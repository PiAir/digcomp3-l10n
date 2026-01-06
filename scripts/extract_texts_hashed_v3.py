#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_texts_hashed_v3.py

Like v2, but with additional controls over paragraph chunking:

- --no-merge-paragraphs
    Write ONE paragraph per string (never concatenates multiple paragraphs into a single CSV row).
    This is often preferable for colophons, lists, and front matter where each line/paragraph is a logical unit.

- --max-paras-per-block N
    If merging is enabled, flush after N paragraphs even if --max-len is not reached.

- --split-on-linebreaks
    Additionally split manual line breaks inside a paragraph (Shift+Enter => '\n' in python-docx) into
    separate pseudo-paragraphs before chunking.

CSV schema: location, context, source, target
Output: <repo-root>/digcomp3-l10n/locale/texts/en.csv and nl.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Tuple

from docx import Document  # python-docx
from docx.text.paragraph import Paragraph
from docx.table import Table, _Cell

# ------------------------- helpers -------------------------

_HEADING_TOKENS = ("heading", "kop", "title", "titel")
_HEADING_LEVEL_RE = re.compile(r"(\d+)$")


def _norm_ws(s: str) -> str:
    # Preserve internal newlines (manual line breaks), normalize spaces/tabs
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.strip()
    s = re.sub(r"[ \t]+", " ", s)
    return s


def _slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[\u00A0\s]+", " ", s)  # NBSP to space
    s = re.sub(r"[^\w\s\-.:/]", "", s)
    s = s.replace(" ", "_")
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "section"


def _style_name(par: Paragraph) -> str:
    try:
        return (par.style.name or "").strip()
    except Exception:
        return ""


def _is_heading(par: Paragraph) -> Tuple[bool, Optional[int]]:
    name = _style_name(par)
    if not name:
        return (False, None)
    lname = name.lower().strip()

    if any(tok in lname for tok in _HEADING_TOKENS):
        m = _HEADING_LEVEL_RE.search(lname)
        if m:
            try:
                lvl = int(m.group(1))
                if 1 <= lvl <= 9:
                    return (True, lvl)
            except Exception:
                pass
        if "title" in lname or "titel" in lname:
            return (True, 1)
        if "kop" in lname:
            return (True, 1)
        return (True, 1)

    return (False, None)


def _iter_block_items(doc: Document) -> Iterator[object]:
    body = doc.element.body
    for child in body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            yield Paragraph(child, doc)
        elif tag == "tbl":
            yield Table(child, doc)


def _cell_text(cell: _Cell) -> str:
    parts: List[str] = []
    for p in cell.paragraphs:
        t = _norm_ws(p.text)
        if t:
            parts.append(t)
    return "\n".join(parts).strip()


@dataclass
class Chunk:
    location: str
    context: str
    source: str


def _sha_key(section_id: str, kind: str, text: str, prefix: str = "doc") -> str:
    payload = f"{section_id}\n{kind}\n{text}".encode("utf-8")
    h = hashlib.sha1(payload).hexdigest()[:12]
    return f"{prefix}.{section_id}.{kind}.{h}"


def _load_manifest(manifest_path: str) -> Dict[str, str]:
    if not manifest_path:
        return {}
    if not os.path.exists(manifest_path):
        return {}
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    mapping: Dict[str, str] = {}
    secs = data.get("sections") or []
    for s in secs:
        sid = s.get("id")
        anchor = ((s.get("docx_anchor") or {}).get("value") or "").strip()
        if sid and anchor:
            mapping[_norm_ws(anchor).lower()] = sid
    return mapping


# ------------------------- extraction -------------------------

def extract(
    docx_path: str,
    max_len: int,
    manifest_map: Dict[str, str],
    merge_paragraphs: bool,
    max_paras_per_block: int,
    split_on_linebreaks: bool,
) -> Tuple[List[Chunk], Dict[str, int]]:
    doc = Document(docx_path)

    stack: List[Optional[str]] = [None] * 6
    current_section = "front"

    def set_section(level: int, heading_text: str):
        nonlocal current_section, stack
        ht = _norm_ws(heading_text)
        mapped = manifest_map.get(ht.lower())
        slug = mapped if mapped else _slugify(ht)
        idx = max(1, min(level, len(stack))) - 1
        stack[idx] = slug
        for j in range(idx + 1, len(stack)):
            stack[j] = None
        current_section = ".".join([s for s in stack if s])

    chunks: List[Chunk] = []
    stats = {"headings": 0, "paragraph_blocks": 0, "table_cells": 0, "front_blocks": 0}

    # paragraph accumulator
    acc_lines: List[str] = []
    acc_len = 0
    acc_paras = 0
    acc_section = current_section

    seen_keys: Dict[str, int] = {}

    def add_chunk(kind: str, section_id: str, text: str):
        key = _sha_key(section_id, kind, text)
        if key in seen_keys:
            seen_keys[key] += 1
            key = f"{key}.{seen_keys[key]}"
        else:
            seen_keys[key] = 0
        ctx = f"{section_id}|{kind}"
        chunks.append(Chunk(location=key, context=ctx, source=text))

    def flush_paragraph_acc():
        nonlocal acc_lines, acc_len, acc_paras, acc_section
        if not acc_lines:
            return
        text = "\n".join(acc_lines).strip()
        acc_lines, acc_len, acc_paras = [], 0, 0
        if not text:
            return
        add_chunk("paragraph", acc_section, text)
        stats["paragraph_blocks"] += 1
        if acc_section == "front":
            stats["front_blocks"] += 1

    def feed_paragraph_text(txt: str):
        nonlocal acc_lines, acc_len, acc_paras, acc_section
        if not txt:
            return
        if not merge_paragraphs:
            add_chunk("paragraph", current_section, txt)
            stats["paragraph_blocks"] += 1
            if current_section == "front":
                stats["front_blocks"] += 1
            return

        if acc_section != current_section:
            flush_paragraph_acc()
            acc_section = current_section

        if max_paras_per_block > 0 and acc_paras >= max_paras_per_block:
            flush_paragraph_acc()
            acc_section = current_section

        prospective = acc_len + (1 if acc_lines else 0) + len(txt)
        if acc_lines and prospective > max_len:
            flush_paragraph_acc()
            acc_section = current_section

        acc_lines.append(txt)
        acc_paras += 1
        acc_len = sum(len(x) for x in acc_lines) + max(0, len(acc_lines) - 1)

    for item in _iter_block_items(doc):
        if isinstance(item, Paragraph):
            raw = (item.text or "").replace("\r\n", "\n").replace("\r", "\n")
            txt = _norm_ws(raw)

            is_head, lvl = _is_heading(item)
            if is_head and txt:
                flush_paragraph_acc()
                stats["headings"] += 1
                set_section(lvl or 1, txt)
                acc_section = current_section
                continue

            if not txt:
                if merge_paragraphs:
                    flush_paragraph_acc()
                continue

            if split_on_linebreaks and "\n" in raw:
                parts = [p.strip() for p in raw.split("\n")]
                parts = [_norm_ws(p) for p in parts if _norm_ws(p)]
                for p in parts:
                    feed_paragraph_text(p)
            else:
                feed_paragraph_text(txt)

        elif isinstance(item, Table):
            flush_paragraph_acc()
            for row in item.rows:
                for cell in row.cells:
                    ctext = _cell_text(cell)
                    if not ctext:
                        continue
                    if len(ctext) <= max_len:
                        add_chunk("table_cell", current_section, ctext)
                        stats["table_cells"] += 1
                    else:
                        parts = [p for p in ctext.split("\n") if p.strip()]
                        buf: List[str] = []
                        blen = 0
                        for p in parts:
                            p = p.strip()
                            if not p:
                                continue
                            newlen = blen + (1 if buf else 0) + len(p)
                            if buf and newlen > max_len:
                                add_chunk("table_cell", current_section, "\n".join(buf))
                                stats["table_cells"] += 1
                                buf, blen = [], 0
                            buf.append(p)
                            blen = sum(len(x) for x in buf) + max(0, len(buf) - 1)
                        if buf:
                            add_chunk("table_cell", current_section, "\n".join(buf))
                            stats["table_cells"] += 1

    flush_paragraph_acc()
    return chunks, stats


def write_csv(path: str, rows: List[Chunk]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(["location", "context", "source", "target"])
        for r in rows:
            w.writerow([r.location, r.context, r.source, ""])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True)
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--manifest", default="")
    ap.add_argument("--max-len", type=int, default=3000)
    ap.add_argument("--no-merge-paragraphs", action="store_true")
    ap.add_argument("--max-paras-per-block", type=int, default=0, help="If merging, flush after N paragraphs (0=unlimited).")
    ap.add_argument("--split-on-linebreaks", action="store_true")
    args = ap.parse_args()

    repo_root = os.path.abspath(args.repo_root)
    out_dir = os.path.join(repo_root, "digcomp3-l10n", "locale", "texts")
    os.makedirs(out_dir, exist_ok=True)

    manifest_map = _load_manifest(args.manifest) if args.manifest else {}
    chunks, stats = extract(
        args.docx,
        args.max_len,
        manifest_map,
        merge_paragraphs=not args.no_merge_paragraphs,
        max_paras_per_block=args.max_paras_per_block,
        split_on_linebreaks=args.split_on_linebreaks,
    )

    en_path = os.path.join(out_dir, "en.csv")
    nl_path = os.path.join(out_dir, "nl.csv")

    write_csv(en_path, chunks)
    write_csv(nl_path, chunks)

    total = len(chunks)
    print(f"[OK] Wrote: {en_path} ({total} rows)")
    print(f"[OK] Wrote: {nl_path} ({total} rows) (targets empty)")
    print(
        f"Chunks: paragraph_blocks={stats['paragraph_blocks']}, table_cells={stats['table_cells']}, "
        f"headings={stats['headings']}, front_blocks={stats['front_blocks']}"
    )


if __name__ == "__main__":
    main()
