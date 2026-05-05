"""Data loading and analysis utilities."""

import pandas as pd
from pathlib import Path


def _parse_bool_series(series: pd.Series) -> pd.Series:
    """Parse boolean-like series safely from strings or numbers."""
    if pd.api.types.is_bool_dtype(series):
        return series
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(int).astype(bool)
    normalized = series.astype(str).str.strip().str.lower()
    mapping = {"true": True, "false": False, "1": True, "0": False}
    return normalized.map(mapping)


def _ensure_experiment(df: pd.DataFrame) -> pd.DataFrame:
    if "experiment" in df.columns:
        return df
    df = df.copy()
    if any(col in df.columns for col in ("realFace", "pFace", "nonFace")):
        df["experiment"] = 2
        return df
    if "PFstimulus" in df.columns:
        df["experiment"] = 1
        return df
    return df


def _ensure_search_target(df: pd.DataFrame) -> pd.DataFrame:
    if "searchTarget" in df.columns:
        return df
    df = df.copy()
    if any(col in df.columns for col in ("realFace", "pFace", "nonFace")):
        target = pd.Series(index=df.index, dtype="object")
        if "realFace" in df.columns:
            real_face = _parse_bool_series(df["realFace"]).fillna(False)
            target = target.mask(real_face, "real face")
        if "pFace" in df.columns:
            p_face = _parse_bool_series(df["pFace"]).fillna(False)
            target = target.mask(p_face, "face")
        if "nonFace" in df.columns:
            non_face = _parse_bool_series(df["nonFace"]).fillna(False)
            target = target.mask(non_face, "non-face object")
        df["searchTarget"] = target
        return df
    if "PFstimulus" in df.columns:
        p_face = _parse_bool_series(df["PFstimulus"]).fillna(False)
        df["searchTarget"] = p_face.map({True: "face", False: "non-face object"})
        return df
    return df


def _ensure_task(df: pd.DataFrame) -> pd.DataFrame:
    if "task" in df.columns:
        return df
    if "targetPresent" not in df.columns:
        return df
    df = df.copy()
    df["task"] = df["targetPresent"].map(
        {True: "target present", False: "target absent"}
    )
    return df


def load_results(csv_path: str | Path) -> pd.DataFrame:
    """Load results CSV and normalize fields for visualization."""
    df = pd.read_csv(csv_path)

    # Convert types - ensure boolean columns are actually boolean
    if "correctResponse" in df.columns:
        df["correctResponse"] = _parse_bool_series(df["correctResponse"])
    if "timeoutOrKeyNotPressed" in df.columns:
        df["timeoutOrKeyNotPressed"] = _parse_bool_series(df["timeoutOrKeyNotPressed"])
    if "targetPresent" in df.columns:
        df["targetPresent"] = _parse_bool_series(df["targetPresent"])
    if "task" in df.columns and "targetPresent" not in df.columns:
        task_normalized = df["task"].astype(str).str.strip().str.lower()
        df["targetPresent"] = task_normalized.map(
            {"target present": True, "target absent": False}
        )
    if "setSize" in df.columns:
        df["setSize"] = pd.to_numeric(df["setSize"], errors="coerce").astype(int)
    if "rt" in df.columns:
        df["rt"] = pd.to_numeric(df["rt"], errors="coerce").astype(int)

    df = _ensure_experiment(df)
    df = _ensure_search_target(df)
    df = _ensure_task(df)

    return df


def analyze_by_condition(df: pd.DataFrame) -> dict:
    """Analyze data by experimental conditions."""
    analysis = {}

    # By experiment
    for exp in df["experiment"].unique():
        exp_data = df[df["experiment"] == exp]
        n_participants = (
            exp_data["participant"].nunique()
            if "participant" in exp_data.columns
            else None
        )
        analysis[f"exp{exp}"] = {
            "n_trials": len(exp_data),
            "n_participants": n_participants,
            "accuracy": exp_data["correctResponse"].mean(),
            "mean_rt": exp_data["rt"].mean(),
            "median_rt": exp_data["rt"].median(),
        }

    # By set size
    analysis["by_setsize"] = {}
    for size in sorted(df["setSize"].unique()):
        size_data = df[df["setSize"] == size]
        analysis["by_setsize"][size] = {
            "accuracy": size_data["correctResponse"].mean(),
            "mean_rt": size_data["rt"].mean(),
            "median_rt": size_data["rt"].median(),
        }

    # By search target
    analysis["by_target"] = {}
    for target in df["searchTarget"].unique():
        target_data = df[df["searchTarget"] == target]
        analysis["by_target"][target] = {
            "accuracy": target_data["correctResponse"].mean(),
            "mean_rt": target_data["rt"].mean(),
        }

    return analysis


def print_analysis(analysis: dict) -> None:
    """Print human-readable analysis summary."""
    print("\n" + "=" * 60)
    print("EXPERIMENT ANALYSIS SUMMARY")
    print("=" * 60)

    # Experiment summary
    print("\nBy Experiment:")
    for key, val in analysis.items():
        if key.startswith("exp"):
            print(f"  {key.upper()}:")
            participants = (
                val["n_participants"]
                if val["n_participants"] is not None
                else "unknown"
            )
            print(f"    Trials: {val['n_trials']}, Participants: {participants}")
            print(f"    Accuracy: {val['accuracy']:.2%}")
            print(
                f"    Mean RT: {val['mean_rt']:.0f}ms, Median RT: {val['median_rt']:.0f}ms"
            )

    # Set size
    print("\nBy Set Size:")
    for size, val in sorted(analysis["by_setsize"].items()):
        print(f"  Size {size}:")
        print(f"    Accuracy: {val['accuracy']:.2%}, Mean RT: {val['mean_rt']:.0f}ms")

    # Search target
    print("\nBy Search Target:")
    for target, val in analysis["by_target"].items():
        print(f"  {target}:")
        print(f"    Accuracy: {val['accuracy']:.2%}, Mean RT: {val['mean_rt']:.0f}ms")

    print("\n" + "=" * 60 + "\n")
