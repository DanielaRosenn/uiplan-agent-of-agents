"""Dry-run the InvoiceIntake_Demo pipeline in Python.

Mirrors Main.xaml + Workflows/*.xaml exactly so we can validate behavior
before opening Studio.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

DEFAULT_PROJECT = (
    r"C:\Users\DanielaRosenstein\OneDrive - Cato Networks\Documents\UiPath"
    r"\InvoiceIntake_Demo"
)

EXPECTED = {
    "INV-1001.json": ("Acme Office Supplies", "1250.00", "AutoPost"),
    "INV-1002.json": ("Globex Logistics",     "8400.00", "NeedsReview"),
    "INV-1003.json": ("Initech Consulting",    "250.75", "AutoPost"),
}


def extract(raw: str) -> dict[str, str]:
    inv = re.search(r"INV[-_]?\d+", raw)
    tot = re.search(r"Total[^\d]{0,10}(\d+(?:\.\d{1,2})?)", raw)
    first = next(
        (line.strip() for line in raw.splitlines() if line.strip()),
        "",
    )
    fields = {
        "InvoiceNumber": inv.group(0) if inv else "",
        "TotalAmount":   tot.group(1) if tot else "",
        "VendorName":    first,
    }
    if not fields["InvoiceNumber"]:
        raise ValueError("Invoice number not found")
    return fields


def apply_policy(fields: dict[str, str]) -> str:
    try:
        total = float(fields["TotalAmount"])
    except (KeyError, ValueError):
        return "NeedsReview"
    if total < 0:
        return "NeedsReview"
    return "AutoPost" if total <= 5000 else "NeedsReview"


def main() -> int:
    root = Path(os.environ.get("UIPATH_INVOICE_DEMO_DIR", DEFAULT_PROJECT))
    in_dir = root / "Data" / "Input"
    out_dir = root / "Data" / "Output"
    if not in_dir.exists():
        raise SystemExit(f"no input folder: {in_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    for f in out_dir.iterdir():
        if f.is_file():
            f.unlink()

    csv_path = out_dir / "run-summary.csv"
    csv_path.write_text("InvoiceNumber,VendorName,TotalAmount,Status\n", encoding="utf-8")

    processed = 0
    for pdf in sorted(in_dir.glob("*.pdf")):
        try:
            raw = pdf.read_text(encoding="utf-8")
            fields = extract(raw)
            status = apply_policy(fields)
            payload = {
                "InvoiceNumber": fields["InvoiceNumber"],
                "VendorName":    fields["VendorName"],
                "TotalAmount":   fields["TotalAmount"],
                "Status":        status,
                "SourceFile":    pdf.name,
            }
            (out_dir / f"{fields['InvoiceNumber']}.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            with csv_path.open("a", encoding="utf-8") as fh:
                fh.write(
                    f"{fields['InvoiceNumber']},{fields['VendorName']},"
                    f"{fields['TotalAmount']},{status}\n"
                )
            processed += 1
            print(f"[dry-run] {pdf.name} -> {fields['InvoiceNumber']} / {status}")
        except Exception as e:
            print(f"[dry-run] FAILED {pdf.name}: {e}")

    print(f"[dry-run] processed {processed} invoices")

    failures: list[str] = []
    for name, (vendor, total, status) in EXPECTED.items():
        p = out_dir / name
        if not p.exists():
            failures.append(f"missing {name}")
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("VendorName") != vendor:
            failures.append(f"{name}: vendor {data.get('VendorName')!r} != {vendor!r}")
        if data.get("TotalAmount") != total:
            failures.append(f"{name}: total {data.get('TotalAmount')!r} != {total!r}")
        if data.get("Status") != status:
            failures.append(f"{name}: status {data.get('Status')!r} != {status!r}")
    if failures:
        for f in failures:
            print("  FAIL:", f)
        return 1
    print("[dry-run] OK - outputs match expected values")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
