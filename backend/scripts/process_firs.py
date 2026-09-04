"""Process the supplied FIR corpus into normalized CSV and graph JSON.

Run from the repository root:
    python backend/scripts/process_firs.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.crime_pipeline import build_graph, parse_fir  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract entities and build the Sentinel crime graph")
    parser.add_argument("--input", type=Path, default=BACKEND_ROOT / "data" / "fir_reports.txt")
    parser.add_argument("--csv", type=Path, default=BACKEND_ROOT / "data" / "generated_crime_dataset.csv")
    parser.add_argument("--graph", type=Path, default=BACKEND_ROOT / "data" / "generated_crime_graph.json")
    args = parser.parse_args()

    reports = [item.strip() for item in args.input.read_text(encoding="utf-8").split("---") if item.strip()]
    records = [parse_fir(report) for report in reports]
    fields = ["case_number", "suspect_name", "vehicle_plate", "date", "year", "primary_type", "description", "block", "location_description", "district", "beat", "ward", "community_area", "iucr", "fbi_code", "arrest", "domestic"]
    with args.csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    graph = build_graph([{key: "" if value is None else str(value) for key, value in record.items()} for record in records])
    args.graph.write_text(graph.model_dump_json(indent=2), encoding="utf-8")
    print(f"Processed {len(records)} FIRs -> {len(graph.nodes)} nodes / {len(graph.edges)} edges")
    print(f"CSV: {args.csv}")
    print(f"Graph: {args.graph}")


if __name__ == "__main__":
    main()

