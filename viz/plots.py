"""Plotting functions for experimental data visualization."""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path
from collections.abc import Iterable

SET_SIZES_BY_EXPERIMENT = {
    1: [16, 32, 64],
    2: [4, 8, 16],
}


TARGET_ORDER = ["face", "non-face object", "real face"]


def _ensure_target_present(df: pd.DataFrame) -> pd.DataFrame:
    if "targetPresent" in df.columns:
        return df
    if "task" in df.columns:
        task_normalized = df["task"].astype(str).str.strip().str.lower()
        df = df.copy()
        df["targetPresent"] = task_normalized.map(
            {"target present": True, "target absent": False}
        )
        return df
    raise ValueError("Missing target presence column (task or targetPresent).")


def _ordered_targets(targets: Iterable[str]) -> list[str]:
    ordered = [t for t in TARGET_ORDER if t in targets]
    return ordered if ordered else list(targets)


def _filter_rt_trials(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only valid RT trials (correct and not timed out)."""
    filtered = df
    if "correctResponse" in filtered.columns:
        filtered = filtered[filtered["correctResponse"]]
    if "timeoutOrKeyNotPressed" in filtered.columns:
        filtered = filtered[~filtered["timeoutOrKeyNotPressed"]]
    return filtered


def plot_rt_by_setsize(df: pd.DataFrame, save_path: str | Path | None = None) -> None:
    """Plot mean reaction time by set size and target presence."""
    df = _ensure_target_present(df)
    df = _filter_rt_trials(df)
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharey="row")

    presence_order = [(True, "Target Present"), (False, "Target Absent")]
    exp_order = [(1, "Experiment 1"), (2, "Experiment 2")]

    for row, (exp, exp_title) in enumerate(exp_order):
        exp_data = df[df["experiment"] == exp]
        valid_sizes = SET_SIZES_BY_EXPERIMENT[exp]
        exp_data = exp_data[exp_data["setSize"].isin(valid_sizes)]

        for col, (present, present_title) in enumerate(presence_order):
            ax = axes[row, col]
            presence_data = exp_data[exp_data["targetPresent"] == present]
            targets = _ordered_targets(presence_data["searchTarget"].unique())

            for target in targets:
                target_data = presence_data[presence_data["searchTarget"] == target]
                grouped = target_data.groupby("setSize")["rt"].agg(
                    ["mean", "std", "count"]
                )
                grouped = grouped.reindex(valid_sizes)

                ax.errorbar(
                    grouped.index,
                    grouped["mean"],
                    yerr=grouped["std"] / grouped["count"].pow(0.5),
                    marker="o",
                    label=target,
                    capsize=5,
                )

            ax.set_xlabel("Set Size", fontsize=11)
            if col == 0:
                ax.set_ylabel("Reaction Time (ms)", fontsize=11)
            ax.set_title(
                f"{exp_title} - {present_title}", fontsize=12, fontweight="bold"
            )
            ax.set_xticks(valid_sizes)
            ax.legend()
            ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Saved: {save_path}")
    else:
        plt.show()
    plt.close()


def plot_accuracy_by_condition(
    df: pd.DataFrame, save_path: str | Path | None = None
) -> None:
    """Plot accuracy by set size and target presence."""
    df = _ensure_target_present(df)
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharey="row")

    presence_order = [(True, "Target Present"), (False, "Target Absent")]
    exp_order = [(1, "Experiment 1"), (2, "Experiment 2")]

    for row, (exp, exp_title) in enumerate(exp_order):
        exp_data = df[df["experiment"] == exp]
        valid_sizes = SET_SIZES_BY_EXPERIMENT[exp]
        exp_data = exp_data[exp_data["setSize"].isin(valid_sizes)]

        for col, (present, present_title) in enumerate(presence_order):
            ax = axes[row, col]
            presence_data = exp_data[exp_data["targetPresent"] == present]
            targets = _ordered_targets(presence_data["searchTarget"].unique())

            for target in targets:
                target_data = presence_data[presence_data["searchTarget"] == target]
                grouped = target_data.groupby("setSize")["correctResponse"].agg(
                    ["mean", "count"]
                )
                grouped = grouped.reindex(valid_sizes)

                n = grouped["count"].to_numpy(dtype=float)
                p = grouped["mean"].to_numpy(dtype=float)
                safe_n = np.where(n > 0, n, np.nan)
                ci = 1.96 * np.sqrt(np.maximum(p * (1 - p) / safe_n, 0))

                ax.errorbar(
                    grouped.index,
                    grouped["mean"],
                    yerr=ci,
                    marker="s",
                    label=target,
                    capsize=5,
                )

            ax.set_xlabel("Set Size", fontsize=11)
            if col == 0:
                ax.set_ylabel("Accuracy (% Correct)", fontsize=11)
            ax.set_ylim([0, 1.05])
            ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
            ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
            ax.set_title(
                f"{exp_title} - {present_title}", fontsize=12, fontweight="bold"
            )
            ax.set_xticks(valid_sizes)
            ax.legend()
            ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Saved: {save_path}")
    else:
        plt.show()
    plt.close()


def plot_rt_by_presence(df: pd.DataFrame, save_path: str | Path | None = None) -> None:
    """Plot mean reaction time by target presence (no set size)."""
    df = _ensure_target_present(df)
    df = _filter_rt_trials(df)
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), sharey="row")

    presence_order = [(True, "Target Present"), (False, "Target Absent")]
    exp_order = [(1, "Experiment 1"), (2, "Experiment 2")]

    for row, (exp, exp_title) in enumerate(exp_order):
        exp_data = df[df["experiment"] == exp]
        for col, (present, present_title) in enumerate(presence_order):
            ax = axes[row, col]
            presence_data = exp_data[exp_data["targetPresent"] == present]
            grouped = presence_data.groupby("searchTarget")["rt"].agg(
                ["mean", "std", "count"]
            )
            targets = _ordered_targets(grouped.index)
            grouped = grouped.reindex(targets)

            x = np.arange(len(targets))
            ax.bar(x, grouped["mean"], color="#4c78a8", alpha=0.8)
            ax.errorbar(
                x,
                grouped["mean"],
                yerr=grouped["std"] / grouped["count"].pow(0.5),
                fmt="none",
                ecolor="#2f4b7c",
                capsize=5,
            )

            ax.set_xticks(x)
            ax.set_xticklabels(targets, rotation=20, ha="right")
            if col == 0:
                ax.set_ylabel("Reaction Time (ms)", fontsize=11)
            ax.set_title(
                f"{exp_title} - {present_title}", fontsize=12, fontweight="bold"
            )
            ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Saved: {save_path}")
    else:
        plt.show()
    plt.close()


def plot_accuracy_by_presence(
    df: pd.DataFrame, save_path: str | Path | None = None
) -> None:
    """Plot accuracy by target presence (no set size)."""
    df = _ensure_target_present(df)
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), sharey="row")

    presence_order = [(True, "Target Present"), (False, "Target Absent")]
    exp_order = [(1, "Experiment 1"), (2, "Experiment 2")]

    for row, (exp, exp_title) in enumerate(exp_order):
        exp_data = df[df["experiment"] == exp]
        for col, (present, present_title) in enumerate(presence_order):
            ax = axes[row, col]
            presence_data = exp_data[exp_data["targetPresent"] == present]
            grouped = presence_data.groupby("searchTarget")["correctResponse"].agg(
                ["mean", "count"]
            )
            targets = _ordered_targets(grouped.index)
            grouped = grouped.reindex(targets)

            n = grouped["count"].to_numpy(dtype=float)
            p = grouped["mean"].to_numpy(dtype=float)
            safe_n = np.where(n > 0, n, np.nan)
            ci = 1.96 * np.sqrt(np.maximum(p * (1 - p) / safe_n, 0))

            x = np.arange(len(targets))
            ax.bar(x, grouped["mean"], color="#72b7b2", alpha=0.8)
            ax.errorbar(
                x,
                grouped["mean"],
                yerr=ci,
                fmt="none",
                ecolor="#3b6963",
                capsize=5,
            )

            ax.set_xticks(x)
            ax.set_xticklabels(targets, rotation=20, ha="right")
            if col == 0:
                ax.set_ylabel("Accuracy (% Correct)", fontsize=11)
            ax.set_ylim([0, 1.05])
            ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
            ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
            ax.set_title(
                f"{exp_title} - {present_title}", fontsize=12, fontweight="bold"
            )
            ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Saved: {save_path}")
    else:
        plt.show()
    plt.close()


def plot_experiment_comparison(
    df: pd.DataFrame, save_path: str | Path | None = None
) -> None:
    """Compare overall performance metrics between experiments."""
    df_rt = _filter_rt_trials(df)
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))

    # Define distinct colors for the 3 search targets
    colors_3 = ["#1f77b4", "#ff7f0e", "#2ca02c"]  # Blue, Orange, Green

    # Mean RT by experiment and target
    rt_data = df_rt.groupby(["experiment", "searchTarget"])["rt"].mean().unstack()
    rt_data.plot(kind="bar", ax=ax1, color=colors_3)
    ax1.set_title("Mean Reaction Time by Experiment", fontweight="bold")
    ax1.set_ylabel("RT (ms)")
    ax1.set_xlabel("Experiment")
    ax1.legend(title="Search Target", labels=rt_data.columns)
    ax1.grid(True, alpha=0.3, axis="y")

    # Accuracy by experiment and target
    acc_data = (
        df.groupby(["experiment", "searchTarget"])["correctResponse"].mean().unstack()
    )
    acc_data.plot(kind="bar", ax=ax2, color=colors_3)
    ax2.set_title("Accuracy by Experiment", fontweight="bold")
    ax2.set_ylabel("Accuracy")
    ax2.set_ylim([0, 1])
    ax2.set_xlabel("Experiment")
    ax2.legend(title="Search Target", labels=acc_data.columns)
    ax2.grid(True, alpha=0.3, axis="y")

    # RT distribution
    for exp in sorted(df_rt["experiment"].unique()):
        exp_data = df_rt[df_rt["experiment"] == exp]
        ax3.hist(exp_data["rt"], bins=50, alpha=0.6, label=f"Exp {exp}")
    ax3.set_title("Reaction Time Distribution", fontweight="bold")
    ax3.set_xlabel("RT (ms)")
    ax3.set_ylabel("Frequency")
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis="y")

    # Error rate by experiment
    errors = df.groupby("experiment").apply(
        lambda x: (~x["correctResponse"].astype(bool)).sum() / len(x)
    )
    colors_exp = ["#d62728", "#d62728"]
    ax4.bar(errors.index, errors.values, color=colors_exp, alpha=0.7)
    ax4.set_title("Error Rate by Experiment", fontweight="bold")
    ax4.set_ylabel("Error Rate")
    ax4.set_ylim([0, max(errors.values) * 1.2])
    ax4.set_xlabel("Experiment")
    ax4.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Saved: {save_path}")
    else:
        plt.show()
    plt.close()


def save_all_plots(
    results_csv: str | Path, output_dir: str | Path = "viz/outputs"
) -> None:
    """Generate and save all plots."""
    from .analysis import load_results, print_analysis

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    df = load_results(results_csv)

    # Print analysis
    analysis = {}
    # Add your analysis here if needed

    # Generate plots
    print("Generating visualizations...")
    plot_rt_by_setsize(df, output_dir / "01_rt_by_setsize.png")
    plot_accuracy_by_condition(df, output_dir / "02_accuracy_by_setsize.png")
    plot_rt_by_presence(df, output_dir / "03_rt_by_presence.png")
    plot_accuracy_by_presence(df, output_dir / "04_accuracy_by_presence.png")
    plot_experiment_comparison(df, output_dir / "05_experiment_comparison.png")

    print(f"\nAll plots saved to: {output_dir.absolute()}")
