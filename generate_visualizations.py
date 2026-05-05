#!/usr/bin/env python3
"""Main script to generate visualizations from results CSV."""

from pathlib import Path
from viz.analysis import load_results, analyze_by_condition, print_analysis
from viz.plots import save_all_plots


def main():
    """Generate analysis and visualizations."""
    # Path to results CSV
    results_csv = Path(__file__).parent / "results.csv"

    if not results_csv.exists():
        print(f"Error: {results_csv} not found")
        return

    print(f"Loading data from: {results_csv}")
    df = load_results(results_csv)
    participant_count = (
        df["participant"].nunique() if "participant" in df.columns else "unknown"
    )
    print(f"Loaded {len(df)} trials from {participant_count} participants")

    # Print analysis summary
    analysis = analyze_by_condition(df)
    print_analysis(analysis)

    # Generate and save plots
    save_all_plots(results_csv)


if __name__ == "__main__":
    main()
