# src/bom_po_tool/bom_reader.py
from __future__ import annotations

import os
from typing import List, Tuple, Dict, Any
import pandas as pd

from models import PartLine


def _read_bom(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext in [".xlsx", ".xlsm", ".xls"]:
        return pd.read_excel(path)

    # CSV: try common encodings
    for enc in ["utf-8-sig", "cp1252", "latin1"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, encoding="latin1")


def _pick_first_nonempty(row: pd.Series, candidates: list[str]) -> str:
    for c in candidates:
        if c in row.index:
            v = row[c]
            if pd.notna(v):
                s = str(v).strip()
                if s:
                    return s
    return ""


def parse_bom(path: str) -> Tuple[List[PartLine], Dict[str, Any]]:
    """
    Returns:
      - list[PartLine]
      - debug info (detected columns, chosen qty column, counts)
    """

    df = _read_bom(path)

    # Candidates tuned for your Altium-style BOM
    mpn_candidates = [
        "Manufacturer Part Number 1",
        "Manufacturer Part Number",
        "MPN",
        "Name",
    ]
    desc_candidates = ["Description", "Item Description", "Part Description", "Name"]
    ref_candidates = ["Designator", "References", "RefDes", "Ref"]

    qty_col = None
    for c in ["Quantity", "Qty", "QUANTITY"]:
        if c in df.columns:
            qty_col = c
            break

    if qty_col is None:
        raise ValueError(f"Could not find quantity column. Columns: {list(df.columns)}")

    parts: List[PartLine] = []
    skipped = 0

    for _, row in df.iterrows():
        # quantity
        q = row.get(qty_col)
        if pd.isna(q):
            skipped += 1
            continue
        try:
            qty = int(q)
        except Exception:
            skipped += 1
            continue
        if qty <= 0:
            skipped += 1
            continue

        mpn = _pick_first_nonempty(row, mpn_candidates)
        desc = _pick_first_nonempty(row, desc_candidates)
        refs = _pick_first_nonempty(row, ref_candidates)

        # If a row has no mpn, we still keep it but flag it (so you notice)
        if not mpn:
            mpn = "[MISSING MPN]"

        parts.append(PartLine(mpn=mpn, qty=qty, description=desc, refs=refs))

    debug = {
        "columns": list(df.columns),
        "qty_col": qty_col,
        "rows_total": len(df),
        "rows_parsed": len(parts),
        "rows_skipped": skipped,
    }
    return parts, debug
