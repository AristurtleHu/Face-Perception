"""Command-line interface for running face perception experiments."""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from time import time_ns

from config import build_experiment_config
from runner import VisualSearchRunner
from resources import resource_path


def _default_project_root() -> Path:
    return resource_path()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the face pareidolia visual-search experiment"
    )
    parser.add_argument(
        "experiment",
        nargs="?",
        choices=("ex1", "ex2"),
        default=None,
        help="Which experiment to run",
    )
    parser.add_argument(
        "--subject-id", default=None, help="Participant ID used in output filenames"
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Random seed for trial order"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None, help="Directory for results"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Repository root containing docs/materials",
    )
    parser.add_argument(
        "--fullscreen", action="store_true", help="Open the task in fullscreen mode"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the selected experiment."""
    parser = build_parser()
    args = parser.parse_args(argv)

    experiment = args.experiment
    if experiment is None:
        if sys.stdin.isatty():
            experiment = input("choose experiment (ex1/ex2): ").strip().lower() or "ex1"
        else:
            experiment = "ex1"

    project_root = args.project_root or _default_project_root()
    config = build_experiment_config(experiment, project_root)

    # Prompt for subject ID if not provided
    subject_id = args.subject_id or input("type subject ID: ").strip() or "anon"

    # Use provided seed or generate random seed from current time
    seed = args.seed if args.seed is not None else time_ns() % (2**31)
    output_dir = args.output_dir or (Path.cwd() / "output")

    try:
        runner = VisualSearchRunner(
            config=config,
            project_root=project_root,
            output_root=output_dir,
            subject_id=subject_id,
            seed=seed,
            fullscreen=args.fullscreen,
        )
        csv_path = runner.run()
        print(csv_path)
        return 0
    except Exception:
        traceback.print_exc()
        if sys.stdin.isatty():
            input("Press Enter to exit...")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
