#!/usr/bin/env python3
"""Merge output response CSVs into results.csv."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

OUTPUT_COLUMNS = [
    "experiment",
    "participant",
    "trialNumber",
    "searchTarget",
    "task",
    "setSize",
    "correctResponse",
    "rt",
    "timeoutOrKeyNotPressed",
]


def _parse_experiment(path: Path) -> tuple[int | None, str | None]:
    parts = list(path.parts)
    for idx, part in enumerate(parts):
        if part in {"ex1", "ex2"}:
            if idx + 1 >= len(parts):
                return None, None
            experiment = 1 if part == "ex1" else 2
            participant = parts[idx + 1]
            return experiment, participant
    return None, None


def _map_search_target(row: pd.Series) -> str:
    if "realFace" in row and row["realFace"] == 1:
        return "real face"
    if "pFace" in row and row["pFace"] == 1:
        return "face"
    if "nonFace" in row and row["nonFace"] == 1:
        return "non-face object"
    if "PFstimulus" in row:
        return "face" if row["PFstimulus"] == 1 else "non-face object"
    return "unknown"


def _map_task(row: pd.Series) -> str:
    return "target present" if row.get("targetPresent", 0) == 1 else "target absent"


def _map_bool(value: int | float | str) -> str:
    return "TRUE" if int(value) == 1 else "FALSE"


def _convert_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    experiment, participant = _parse_experiment(path)
    if experiment is None or participant is None:
        raise ValueError(f"Could not infer experiment/participant from {path}")

    mapped = pd.DataFrame(
        {
            "experiment": experiment,
            "participant": participant,
            "trialNumber": df["trialNumber"].astype(int),
            "searchTarget": df.apply(_map_search_target, axis=1),
            "task": df.apply(_map_task, axis=1),
            "setSize": df["setSize"].astype(int),
            "correctResponse": df["correctResponse"].apply(_map_bool),
            "rt": df["rt"].astype(int),
            "timeoutOrKeyNotPressed": df["timeoutOrKeyNotPressed"].apply(_map_bool),
        }
    )

    return mapped


def _collect_response_csvs(output_dir: Path) -> list[Path]:
    return sorted(output_dir.rglob("responseData/*.csv"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge output response CSVs into results.csv"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Root output directory (default: output)",
    )
    parser.add_argument(
        "--results-csv",
        type=Path,
        default=Path("results.csv"),
        help="Results CSV to append to (default: results.csv)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview merged row counts without writing",
    )
    args = parser.parse_args()

    csv_paths = _collect_response_csvs(args.output_dir)
    if not csv_paths:
        print(f"No response CSVs found under {args.output_dir}")
        return 1

    frames = []
    for csv_path in csv_paths:
        try:
            frames.append(_convert_csv(csv_path))
        except Exception as exc:
            print(f"Skipping {csv_path}: {exc}")

    if not frames:
        print("No valid response CSVs to merge")
        return 1

    merged = pd.concat(frames, ignore_index=True)

    if args.results_csv.exists():
        existing = pd.read_csv(args.results_csv)
        combined = pd.concat([existing, merged], ignore_index=True)
    else:
        combined = merged

    combined = combined[OUTPUT_COLUMNS]
    combined = combined.drop_duplicates()

    if args.dry_run:
        print(f"Found {len(merged)} new rows from output")
        print(f"Total rows after merge: {len(combined)}")
        return 0

    combined.to_csv(args.results_csv, index=False)
    print(f"Wrote {len(combined)} rows to {args.results_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
