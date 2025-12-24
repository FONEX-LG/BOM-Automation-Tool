# src/bom_po_tool/models.py
from dataclasses import dataclass


@dataclass
class PartLine:
    # Input data (from BOM)
    mpn: str
    qty: int
    description: str = ""
    refs: str = ""

    # Enriched data (New fields)
    supplier: str = ""
    supplier_pn: str = ""
    manufacturer: str = ""
    unit_price: float = 0.0  # <--- This was missing!
    total_price: float = 0.0
    stock_available: int = 0
    link: str = ""
    status: str = "Pending"