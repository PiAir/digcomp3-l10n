#!/usr/bin/env python3
"""
split_pack_csv_raw.py

Doel:
- CSV opsplitsen in N delen zonder inhoud te wijzigen (quotes blijven exact behouden).
- CSV weer samenvoegen door delen te concatenaten (met header-controle).

Gebruik:
  # Splits in 9 delen
  python split_pack_csv_raw.py --unpack input.csv --outdir chunks --parts 9

  # Voeg weer samen
  python split_pack_csv_raw.py --pack chunks --output merged.csv

Let op:
- Dit werkt "raw" per fysieke regel. Dat is perfect als elke record op 1 regel staat (meestal het geval).
- Als je CSV multiline velden bevat (newline binnen quotes), dan is raw-splitting per regel ongeschikt.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

MANIFEST_NAME = "manifest.json"


@dataclass
class Manifest:
    source_file: str
    parts: int
    part_files: List[str]
    row_counts: List[int]  # aantal datarijen per part (excl. header)


def _split_indices(n_rows: int, parts: int) -> List[Tuple[int, int]]:
    """Verdeel n_rows zo gelijk mogelijk over parts. Retourneert (start,end) per part."""
    if parts <= 0:
        raise ValueError("parts moet > 0 zijn")
    base = n_rows // parts
    rem = n_rows % parts
    out = []
    start = 0
    for i in range(parts):
        size = base + (1 if i < rem else 0)
        end = start + size
        out.append((start, end))
        start = end
    return out


def _read_lines_bytes(path: Path) -> List[bytes]:
    """
    Lees bestand als bytes-lijnen, inclusief line endings (keepends).
    Dit behoudt exact \n vs \r\n en alle quoting.
    """
    data = path.read_bytes()
    # splitlines(keepends=True) behoudt line endings
    lines = data.splitlines(keepends=True)
    return lines


def unpack(input_csv: Path, outdir: Path, parts: int) -> None:
    lines = _read_lines_bytes(input_csv)
    if not lines:
        raise ValueError(f"Lege CSV: {input_csv}")

    header = lines[0]
    data_lines = lines[1:]
    n = len(data_lines)

    cuts = _split_indices(n, parts)

    outdir.mkdir(parents=True, exist_ok=True)
    stem = input_csv.stem
    part_files: List[str] = []
    row_counts: List[int] = []

    for idx, (s, e) in enumerate(cuts, start=1):
        part_name = f"{stem}_part{idx:02d}_of{parts:02d}.csv"
        part_path = outdir / part_name

        chunk = [header] + data_lines[s:e]
        part_path.write_bytes(b"".join(chunk))

        part_files.append(part_name)
        row_counts.append(e - s)

    manifest = Manifest(
        source_file=input_csv.name,
        parts=parts,
        part_files=part_files,
        row_counts=row_counts,
    )
    (outdir / MANIFEST_NAME).write_text(json.dumps(manifest.__dict__, indent=2), encoding="utf-8")

    approx = (n / parts) if parts else 0
    print(f"[OK] Ingelezen: {input_csv} (header + {n} datarijen)")
    print(f"[OK] Uitgeschreven naar: {outdir} ({parts} delen; gemiddeld ~{approx:.1f} rijen/deel)")
    for fn, rc in zip(part_files, row_counts):
        print(f"  - {fn}: {rc} rijen")


def _load_manifest(indir: Path) -> Optional[Manifest]:
    mpath = indir / MANIFEST_NAME
    if not mpath.exists():
        return None
    obj = json.loads(mpath.read_text(encoding="utf-8"))
    return Manifest(
        source_file=str(obj.get("source_file", "")),
        parts=int(obj.get("parts", 0)),
        part_files=list(obj.get("part_files", [])),
        row_counts=list(obj.get("row_counts", [])),
    )


def _discover_part_files(indir: Path) -> List[Path]:
    """Fallback als manifest ontbreekt: vind *_part??_of??.csv en sorteer op partnummer."""
    files = list(indir.glob("*_part??_of??.csv"))

    def key(p: Path) -> int:
        m = re.search(r"_part(\d+)_of\d+\.csv$", p.name)
        return int(m.group(1)) if m else 10**9

    files.sort(key=key)
    return files


def pack(indir: Path, output_csv: Path) -> None:
    manifest = _load_manifest(indir)
    if manifest and manifest.part_files:
        part_paths = [indir / fn for fn in manifest.part_files]
    else:
        part_paths = _discover_part_files(indir)

    if not part_paths:
        raise FileNotFoundError(f"Geen part-bestanden gevonden in {indir}")

    # Header van eerste part
    first_lines = _read_lines_bytes(part_paths[0])
    if not first_lines:
        raise ValueError(f"Leeg part-bestand: {part_paths[0]}")
    header = first_lines[0]

    # Schrijf output: header één keer, daarna alle dataregels van alle parts (zonder hun header)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    out_chunks: List[bytes] = []
    out_chunks.append(header)

    for p in part_paths:
        lines = _read_lines_bytes(p)
        if not lines:
            raise ValueError(f"Leeg part-bestand: {p}")
        if lines[0] != header:
            raise ValueError(f"Header mismatch in {p.name}. Bestand kan niet veilig worden samengevoegd.")
        data = lines[1:]
        out_chunks.extend(data)
        total_rows += len(data)

    output_csv.write_bytes(b"".join(out_chunks))

    print(f"[OK] Samengevoegd: {len(part_paths)} delen -> {output_csv}")
    print(f"[OK] Totaal datarijen (excl. header): {total_rows}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Split (unpack) en merge (pack) CSV-bestanden (raw, quotes blijven exact).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--unpack", metavar="INPUT_CSV", help="Pad naar input CSV om te splitsen.")
    group.add_argument("--pack", metavar="INPUT_DIR", help="Map met part-CSV’s om samen te voegen.")

    parser.add_argument("--outdir", default="chunks", help="Outputmap voor --unpack (default: chunks).")
    parser.add_argument("--parts", type=int, default=9, help="Aantal delen voor --unpack (default: 9).")
    parser.add_argument("--output", default="merged.csv", help="Output CSV pad voor --pack (default: merged.csv).")

    args = parser.parse_args(argv)

    try:
        if args.unpack:
            unpack(Path(args.unpack), Path(args.outdir), int(args.parts))
        else:
            pack(Path(args.pack), Path(args.output))
        return 0
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
