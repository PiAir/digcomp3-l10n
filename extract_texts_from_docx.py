import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


# ----------------------------
# Helpers: normalization
# ----------------------------
def norm(s: str) -> str:
    s = s or ""
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s+\n", "\n", s)
    s = re.sub(r"\n\s+", "\n", s)
    return s.strip()


def norm_ci(s: str) -> str:
    return norm(s).lower()


def join_hard_wrapped_lines(text: str) -> str:
    # Conservative join: only join lines that look like hard-wrapped prose,
    # keep blank lines as paragraph boundaries.
    lines = text.splitlines()
    out: List[str] = []
    buf: List[str] = []
    for ln in lines:
        if not ln.strip():
            if buf:
                out.append(" ".join(buf).strip())
                buf = []
            out.append("")
            continue
        buf.append(ln.strip())
    if buf:
        out.append(" ".join(buf).strip())
    return "\n".join(out).strip()


def is_heading(par: Paragraph) -> bool:
    style = getattr(par.style, "name", "") or ""
    return style.lower().startswith("heading")


def heading_level(par: Paragraph) -> Optional[int]:
    style = getattr(par.style, "name", "") or ""
    m = re.match(r"Heading\s+(\d+)", style, flags=re.IGNORECASE)
    return int(m.group(1)) if m else None


# ----------------------------
# Iterate DOCX in document order (paragraphs + tables)
# ----------------------------
def iter_block_items(doc: Document) -> Iterable[Any]:
    """
    Yield Paragraph and Table objects in the order they appear in the document.
    """
    parent = doc.element.body
    for child in parent.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, doc)
        elif child.tag.endswith("}tbl"):
            yield Table(child, doc)


# ----------------------------
# Data structures
# ----------------------------
@dataclass
class Item:
    kind: str  # 'p' or 'table'
    text: str
    meta: Dict[str, Any]


@dataclass
class Unit:
    key: str
    context: str
    source: str


# ----------------------------
# CSV IO
# ----------------------------
def load_existing_targets(csv_path: Path) -> Dict[str, str]:
    if not csv_path.exists():
        return {}
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        out = {}
        for row in reader:
            loc = (row.get("location") or "").strip()
            tgt = row.get("target") or ""
            if loc:
                out[loc] = tgt
        return out


def write_csv(csv_path: Path, rows: List[Dict[str, str]]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["location", "context", "source", "target"]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)


# ----------------------------
# Build linearized document stream
# ----------------------------
def table_to_text(table: Table, fmt: str = "tsv") -> str:
    rows: List[str] = []
    for r in table.rows:
        cells = [norm(c.text) for c in r.cells]
        if fmt == "tsv":
            rows.append("\t".join(cells))
        else:
            # fallback: pipe-like
            rows.append(" | ".join(cells))
    return "\n".join(rows).strip()


def build_stream(doc: Document, include_tables: bool, table_format: str, table_prefix: str) -> List[Item]:
    stream: List[Item] = []
    for obj in iter_block_items(doc):
        if isinstance(obj, Paragraph):
            txt = obj.text or ""
            txt = norm(txt)
            meta = {
                "is_heading": is_heading(obj),
                "heading_level": heading_level(obj)
            }
            stream.append(Item(kind="p", text=txt, meta=meta))
        elif isinstance(obj, Table) and include_tables:
            ttxt = table_to_text(obj, fmt=table_format)
            if ttxt:
                stream.append(Item(kind="table", text=f"{table_prefix}:\n{ttxt}", meta={"rows": len(obj.rows), "cols": len(obj.columns)}))
    return stream


# ----------------------------
# Anchor resolution
# ----------------------------
def anchor_candidates(anchor: Dict[str, Any]) -> List[str]:
    if "any_of" in anchor and isinstance(anchor["any_of"], list):
        return [str(x) for x in anchor["any_of"] if str(x).strip()]
    if "value" in anchor and str(anchor["value"]).strip():
        return [str(anchor["value"])]
    return []


def locate_anchor(stream: List[Item], anchor: Dict[str, Any]) -> Optional[int]:
    atype = anchor.get("type")

    if atype == "start_of_document":
        return 0

    cands = [norm_ci(x) for x in anchor_candidates(anchor)]
    if not cands:
        return None

    # Two-pass strategy:
    # - For headings: prefer heading matches
    # - For paragraph_contains: any paragraph
    if atype in ("heading_text", "heading_contains"):
        # pass 1: headings only
        for i, it in enumerate(stream):
            if it.kind != "p" or not it.meta.get("is_heading") or not it.text:
                continue
            hay = norm_ci(it.text)
            for needle in cands:
                if atype == "heading_text" and hay == needle:
                    return i
                if atype == "heading_contains" and needle in hay:
                    return i
        # pass 2 fallback: any paragraph (still exact/contains rules)
        for i, it in enumerate(stream):
            if it.kind != "p" or not it.text:
                continue
            hay = norm_ci(it.text)
            for needle in cands:
                if atype == "heading_text" and hay == needle:
                    return i
                if atype == "heading_contains" and needle in hay:
                    return i
        return None

    if atype == "paragraph_contains":
        for i, it in enumerate(stream):
            if it.kind != "p" or not it.text:
                continue
            hay = norm_ci(it.text)
            for needle in cands:
                if needle in hay:
                    return i
        return None

    return None


def compute_ranges(stream: List[Item], sections: List[Dict[str, Any]]) -> Dict[str, Tuple[int, int]]:
    """
    Uses ALL sections (including ignore/export) as boundaries if they have anchors.
    Range end = next found start anchor in document order.
    """
    starts: List[Tuple[int, str]] = []
    for s in sections:
        anchor = s.get("docx_anchor") or {}
        idx = locate_anchor(stream, anchor) if anchor else None
        if idx is not None:
            starts.append((idx, s["id"]))

    starts_sorted = sorted(starts, key=lambda x: x[0])
    ranges: Dict[str, Tuple[int, int]] = {}

    for j, (idx, sid) in enumerate(starts_sorted):
        end = starts_sorted[j + 1][0] if j + 1 < len(starts_sorted) else len(stream)
        ranges[sid] = (idx, end)

    return ranges


# ----------------------------
# Unit creation
# ----------------------------
def to_units_atomic(
    section: Dict[str, Any],
    stream: List[Item],
    start: int,
    end: int,
    key_prefix: str,
    defaults: Dict[str, Any]
) -> List[Unit]:
    """
    One unit per heading/paragraph/table, stable numbering u0001.. in encountered order.
    """
    units: List[Unit] = []
    counter = 0

    for it in stream[start:end]:
        if not it.text:
            continue

        # Skip the section's own start anchor if it's a heading and equals the first heading?
        # We keep it: headings are content (useful for rebuild).
        counter += 1
        key = f"{key_prefix}.u{counter:04d}"

        if it.kind == "p" and it.meta.get("is_heading"):
            lvl = it.meta.get("heading_level") or 0
            ctx = f"{section['id']}|heading|l{lvl}"
        elif it.kind == "table":
            ctx = f"{section['id']}|table"
        else:
            ctx = f"{section['id']}|paragraph"

        src = it.text

        if defaults.get("join_hard_wrapped_lines", True):
            src = join_hard_wrapped_lines(src)

        units.append(Unit(key=key, context=ctx, source=src))

    return units


def chunk_paragraph_units(units: List[Unit], max_chars: int, min_chars: int, key_prefix: str, section_id: str) -> List[Unit]:
    """
    Optional: chunk sequential paragraph/table units into larger blocks.
    Note: keys change in chunked mode. Use atomic mode if you need stable keys across reruns.
    """
    blocks: List[Unit] = []
    buf: List[str] = []
    size = 0
    bi = 0

    def flush():
        nonlocal buf, size, bi
        if not buf:
            return
        bi += 1
        text = "\n\n".join(buf).strip()
        blocks.append(Unit(
            key=f"{key_prefix}.p{bi:03d}",
            context=f"{section_id}|chunk",
            source=text
        ))
        buf = []
        size = 0

    for u in units:
        t = u.source.strip()
        if not t:
            continue
        add = (("\n\n" if buf else "") + t)
        if size + len(add) > max_chars and size >= min_chars:
            flush()
            buf = [t]
            size = len(t)
        else:
            buf.append(t)
            size += len(add)

    flush()
    return blocks


# ----------------------------
# Main
# ----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="manifest.json")
    ap.add_argument("--docx", required=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--mode", choices=["atomic", "chunked"], default=None, help="Override manifest defaults.mode")
    ap.add_argument("--max-chars", type=int, default=None)
    ap.add_argument("--min-chars", type=int, default=None)
    ap.add_argument("--no-tables", action="store_true")
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    defaults = manifest.get("defaults", {})
    sections = manifest.get("sections", [])

    mode = args.mode or defaults.get("mode", "atomic")
    max_chars = args.max_chars or int(defaults.get("max_chars_per_chunk", 1800))
    min_chars = args.min_chars or int(defaults.get("min_chars_per_chunk", 200))

    include_tables = bool(defaults.get("include_tables", True))
    if args.no_tables:
        include_tables = False

    table_format = str(defaults.get("table_format", "tsv"))
    table_prefix = str(defaults.get("table_prefix", "TABLE"))

    doc = Document(args.docx)
    stream = build_stream(doc, include_tables=include_tables, table_format=table_format, table_prefix=table_prefix)

    ranges = compute_ranges(stream, sections)

    # Determine which sections to import
    importable = [s for s in sections if s.get("action") in ("import", "import_export")]

    repo_root = Path(args.repo_root)
    out_dir = repo_root / "locale" / "texts"
    en_path = out_dir / "en.csv"
    nl_path = out_dir / "nl.csv"

    existing_nl = load_existing_targets(nl_path)

    units_all: List[Unit] = []
    missing = []

    for s in importable:
        sid = s["id"]
        r = ranges.get(sid)
        if not r:
            missing.append(sid)
            continue

        start, end = r
        key_prefix = (s.get("import") or {}).get("key_prefix") or f"doc.{sid}"

        atomic_units = to_units_atomic(s, stream, start, end, key_prefix, defaults)

        if mode == "chunked":
            # Chunk across the atomic units
            chunked_units = chunk_paragraph_units(
                atomic_units,
                max_chars=max_chars,
                min_chars=min_chars,
                key_prefix=key_prefix,
                section_id=sid
            )
            units_all.extend(chunked_units)
        else:
            units_all.extend(atomic_units)

    # Write CSVs
    en_rows: List[Dict[str, str]] = []
    nl_rows: List[Dict[str, str]] = []

    for u in units_all:
        en_rows.append({
            "location": u.key,
            "context": u.context,
            "source": u.source,
            "target": ""
        })
        nl_rows.append({
            "location": u.key,
            "context": u.context,
            "source": u.source,
            "target": existing_nl.get(u.key, "")
        })

    write_csv(en_path, en_rows)
    write_csv(nl_path, nl_rows)

    preserved = sum(1 for k, v in existing_nl.items() if v and any(r["location"] == k for r in nl_rows))
    print(f"[OK] Wrote: {en_path} ({len(en_rows)} rows)")
    print(f"[OK] Wrote: {nl_path} ({len(nl_rows)} rows) – preserved {preserved} existing targets")

    if missing:
        print("[WARN] Could not locate anchors for these importable sections:")
        for sid in missing:
            print(" -", sid)
        print("Tip: pas in manifest.json de docx_anchor.value/any_of aan (heading_contains/paragraph_contains).")


if __name__ == "__main__":
    main()
