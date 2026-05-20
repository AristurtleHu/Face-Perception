#!/usr/bin/env python3
"""DDM fitting for Experiment 1 and Experiment 2 using PyDDM.

This script:
- Loads trial-level CSV data (see ../results.csv format).
- Cleans RTs, infers response, and validates conditions.
- Fits PyDDM models with drift rate varying by manipulation.
- Compares competing models using AIC/BIC (PyDDM is ML-based, not MCMC).
- Generates publication-style matplotlib figures for observed vs predicted RTs.

Run from docs/data:
    python ddm_fit.py --csv results.csv
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    from pyddm import Model, Sample, Fittable
    from pyddm.functions import fit_adjust_model
    from pyddm.models import Drift, Bound, BoundConstant, NoiseConstant, ICPointSourceCenter, Overlay, OverlayNonDecision
    from pyddm.models import LossRobustLikelihood
except Exception:  # pragma: no cover - runtime import check
    Model = None
    Sample = None
    Fittable = None
    fit_adjust_model = None
    Drift = None
    Bound = None
    BoundConstant = None
    NoiseConstant = None
    ICPointSourceCenter = None
    Overlay = None
    OverlayNonDecision = None
    LossRobustLikelihood = None


# -----------------------------
# Configuration and constants
# -----------------------------
MIN_RT_SEC = 0.2
MAX_RT_SEC = 10.0
DEFAULT_N_SAMPLES = 0
DEFAULT_BURN = 0
DEFAULT_THIN = 1
DEFAULT_N_CHAINS = 1

EX1_SET_SIZES = {16, 32, 64}
EX2_SET_SIZES = {4, 8, 16}

EX1_TARGETS = {"illusory face", "nonface object"}
EX2_TARGETS = {"illusory face", "nonface object", "real face"}
EX2_TARGET_ORDER = ["nonface object", "illusory face", "real face"]

TASK_PRESENT = "target present"
TASK_ABSENT = "target absent"


@dataclass
class FitConfig:
    csv_path: Path
    out_dir: Path
    n_samples: int
    burn: int
    thin: int
    n_chains: int
    seed: int


# -----------------------------
# Data loading and preprocessing
# -----------------------------
# 关键思路（中文说明）:
# - DDM 使用 trial-level RT + response 做似然估计，不需要先做分位数分箱。
# - PyDDM 使用最大似然拟合，因此不产生 MCMC 的 posterior 与 trace。
# - 过滤极端 RT (200-3000 ms) 以减少非决策过程或偶然失误对拟合的干扰。
def _normalize_text(value: str) -> str:
    return str(value).strip().lower()


def _infer_response(task_label: str, correct: bool) -> int:
    """Infer participant response (1=present, 0=absent).

    中文说明：
    这里没有直接的反应键值，但有 trial 的真实条件（present/absent）
    与正确性。二选一任务中，错误意味着选择了相反选项，因此：
    - 正确：response 与真实条件一致
    - 错误：response 反转
    """
    task_label = _normalize_text(task_label)
    is_present = task_label == TASK_PRESENT
    if correct:
        return 1 if is_present else 0
    return 0 if is_present else 1


def _detect_rt_unit(rt_values: pd.Series) -> str:
    """Detect RT unit by magnitude. Returns "ms" or "sec".

    中文说明：
    从实验代码可知 RT 以毫秒写入 CSV（runner/trials 输出 rt_ms），
    因此默认按毫秒处理。若你之后换了数据来源，再用该函数自动判断。
    """
    median_rt = float(np.nanmedian(rt_values.values))
    return "ms" if median_rt > 20 else "sec"


def _convert_rt_to_seconds(rt_values: pd.Series, unit: str) -> pd.Series:
    if unit == "ms":
        return rt_values / 1000.0
    return rt_values.astype(float)


def load_and_clean(csv_path: Path) -> Tuple[pd.DataFrame, Dict[str, int]]:
    df = pd.read_csv(csv_path)

    # Normalize key columns
    df["task"] = df["task"].astype(str).str.strip().str.lower()
    df["searchTarget"] = df["searchTarget"].astype(str).str.strip().str.lower()
    df["participant"] = df["participant"].astype(str)

    # Map historical labels to required ones
    df["searchTarget"] = df["searchTarget"].replace(
        {
            "face": "illusory face",
            "non-face object": "nonface object",
            "real face": "real face",
        }
    )

    # Normalize correctness field
    df["correctResponse"] = df["correctResponse"].astype(str).str.upper()
    df["timeoutOrKeyNotPressed"] = df["timeoutOrKeyNotPressed"].astype(str).str.upper()

    # 删除缺失 trial
    before = len(df)
    df = df.dropna(subset=["rt", "correctResponse", "task", "searchTarget", "setSize"]).copy()
    dropped_missing = before - len(df)

    # 删除 timeout trial（非有效决策过程）
    df = df[df["timeoutOrKeyNotPressed"] == "FALSE"].copy()

    # RT 单位在原始实验代码中为毫秒，这里默认按毫秒处理
    rt_unit = "ms"
    df["rt"] = _convert_rt_to_seconds(df["rt"], rt_unit)

    # 删除异常 RT：过短可能是误触，过长可能是走神或非决策过程
    rt_mask = (df["rt"] >= MIN_RT_SEC) & (df["rt"] <= MAX_RT_SEC)
    dropped_rt = int((~rt_mask).sum())
    df = df[rt_mask].copy()

    # 转成布尔正确性
    df["is_correct"] = df["correctResponse"].map(lambda v: str(v).upper() == "TRUE")

    # 仅保留正确试次
    before_correct = len(df)
    df = df[df["is_correct"]].copy()
    dropped_incorrect = before_correct - len(df)

    # 推断 response 给 PyDDM 使用（1=present, 0=absent）
    df["response"] = df.apply(
        lambda row: _infer_response(row["task"], bool(row["is_correct"])), axis=1
    )

    # 轻量检查：提示是否出现非预期条件（不终止，仅提醒）
    exp1_sizes = set(df[df["experiment"] == 1]["setSize"].unique())
    exp2_sizes = set(df[df["experiment"] == 2]["setSize"].unique())
    if exp1_sizes and not exp1_sizes.issubset(EX1_SET_SIZES):
        print(f"Warning: Experiment 1 unexpected setSize values: {sorted(exp1_sizes)}")
    if exp2_sizes and not exp2_sizes.issubset(EX2_SET_SIZES):
        print(f"Warning: Experiment 2 unexpected setSize values: {sorted(exp2_sizes)}")

    summary = {
        "total_rows": before,
        "dropped_missing": dropped_missing,
        "dropped_rt": dropped_rt,
        "dropped_incorrect": dropped_incorrect,
        "rt_unit": rt_unit,
        "clean_rows": len(df),
    }

    return df, summary


# -----------------------------
# PyDDM fitting helpers
# -----------------------------
# 理论说明：
# - drift rate v 表征证据积累速度（证据质量/效率）。
# - boundary a 表征谨慎度（speed-accuracy tradeoff）。
# - nondecision time Ter 表征感知/运动等非决策时间。
# - noise parameter s 通常固定（如 s=1）以保证模型可辨识性。
#
# DDM 核心随机微分方程（理论背景说明）：
#   dx = v dt + s dW
#   x: accumulated evidence
#   v: drift rate
#   s: noise magnitude (通常固定)
#   dW: Wiener process
# 决策规则：上界=反应A（present），下界=反应B（absent）。
def _require_pyddm() -> None:
    if Model is None:
        print(
            "PyDDM is not installed. Install it with: pip install pyddm"
        )
        raise SystemExit(1)


class DriftBySetSize(Drift):
    name = "Drift by set size"
    required_parameters = ["v16", "v32", "v64"]
    required_conditions = ["setSize"]

    def get_drift(self, conditions, **kwargs):
        size = int(conditions["setSize"])
        mapping = {16: self.v16, 32: self.v32, 64: self.v64}
        return mapping[size]


class DriftFuncSetSizeLog(Drift):
    name = "Drift by log(set size)"
    required_parameters = ["v0", "v_log_slope"]
    required_conditions = ["setSize"]

    def get_drift(self, conditions, **kwargs):
        size = float(conditions["setSize"])
        return self.v0 + self.v_log_slope * math.log(size)


class DriftByTarget(Drift):
    name = "Drift by target type"
    required_parameters = ["v_illusory", "v_nonface", "v_real"]
    required_conditions = ["searchTarget"]

    def get_drift(self, conditions, **kwargs):
        target = str(conditions["searchTarget"]).strip().lower()
        mapping = {
            "illusory face": self.v_illusory,
            "nonface object": self.v_nonface,
            "real face": self.v_real,
        }
        return mapping[target]


class DriftFuncTargetOrdered(Drift):
    name = "Drift by ordered target"
    required_parameters = ["v0", "v_step"]
    required_conditions = ["searchTarget"]

    def get_drift(self, conditions, **kwargs):
        target = str(conditions["searchTarget"]).strip().lower()
        try:
            rank = EX2_TARGET_ORDER.index(target)
        except ValueError:
            rank = 0
        return self.v0 + self.v_step * float(rank)


class BoundBySetSize(Bound):
    name = "Bound by set size"
    required_parameters = ["a16", "a32", "a64"]
    required_conditions = ["setSize"]

    def get_bound(self, conditions, **kwargs):
        size = int(conditions["setSize"])
        mapping = {16: self.a16, 32: self.a32, 64: self.a64}
        return mapping[size]


class BoundBySetSizeEx2(Bound):
    name = "Bound by set size (ex2)"
    required_parameters = ["a4", "a8", "a16"]
    required_conditions = ["setSize"]

    def get_bound(self, conditions, **kwargs):
        size = int(conditions["setSize"])
        mapping = {4: self.a4, 8: self.a8, 16: self.a16}
        return mapping[size]


class OverlayNonDecisionByTarget(Overlay):
    name = "Nondecision time by target"
    required_parameters = ["t_illusory", "t_nonface", "t_real"]
    required_conditions = ["searchTarget"]

    def apply(self, solution, conditions=None, **kwargs):
        if not conditions:
            return OverlayNonDecision(nondectime=self.t_illusory).apply(solution)
        target = str(conditions["searchTarget"]).strip().lower()
        mapping = {
            "illusory face": self.t_illusory,
            "nonface object": self.t_nonface,
            "real face": self.t_real,
        }
        return OverlayNonDecision(nondectime=mapping[target]).apply(solution)


def _build_sample(df: pd.DataFrame, conditions_columns: Optional[List[str]] = None) -> "Sample":
    _require_pyddm()

    # PyDDM 需要 rt (秒) 和 response (0/1) 以及条件列
    try:
        if not conditions_columns:
            conditions_columns = ["setSize"]
        return Sample.from_pandas_dataframe(
            df,
            rt_column_name="rt",
            choice_column_name="response",
            conditions_columns=conditions_columns,
        )
    except TypeError:
        return Sample.from_pandas_dataframe(
            df,
            rt_column_name="rt",
            choice_column_name="response",
        )


def _slugify(value: str) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _fit_model(model: "Model", sample: "Sample") -> "Model":
    _require_pyddm()
    return fit_adjust_model(sample=sample, model=model, lossfunction=LossRobustLikelihood, verbose=False)


def _model_param_count(model: "Model") -> int:
    try:
        return len(model.get_model_parameters())
    except Exception:
        return 0


def _model_metrics(model: "Model", sample: "Sample") -> Dict[str, Optional[float]]:
    ll = None
    try:
        ll = float(model.loglikelihood(sample))
    except Exception:
        ll = None

    if ll is None:
        fit_result = getattr(model, "fitresult", None)
        if fit_result is not None:
            for attr in ("value", "val", "loss_value", "loss"):
                if not hasattr(fit_result, attr):
                    continue
                value = getattr(fit_result, attr)
                if callable(value):
                    try:
                        value = value()
                    except Exception:
                        continue
                try:
                    ll = -float(value)
                    break
                except (TypeError, ValueError):
                    continue

    if ll is None:
        try:
            loss = LossRobustLikelihood(sample=sample, dt=model.dt, T_dur=model.T_dur).loss(model)
            ll = -float(loss)
        except Exception:
            return {"loglik": None, "aic": None, "bic": None}

    k = _model_param_count(model)
    n = len(sample)
    aic = 2 * k - 2 * ll
    bic = math.log(n) * k - 2 * ll
    return {"loglik": ll, "aic": aic, "bic": bic}


def _model_params_dict(model: "Model", prefix: str) -> Dict[str, float]:
    params = model.get_model_parameters()
    if isinstance(params, dict):
        return {f"{prefix}{k}": float(v) for k, v in params.items()}

    names = list(getattr(model, "get_model_parameter_names", lambda: [])())
    if names and len(names) == len(params):
        return {f"{prefix}{name}": float(value) for name, value in zip(names, params)}

    return {f"{prefix}param_{idx}": float(value) for idx, value in enumerate(params)}


def _model_params_by_name(model: "Model") -> Dict[str, float]:
    params = model.get_model_parameters()
    if isinstance(params, dict):
        return {k: float(v) for k, v in params.items()}

    names = list(getattr(model, "get_model_parameter_names", lambda: [])())
    if names and len(names) == len(params):
        return {name: float(value) for name, value in zip(names, params)}

    return {}


def _derived_v_by_setsize(model: "Model") -> Dict[str, float]:
    params = _model_params_by_name(model)
    v0 = params.get("v0")
    v_slope = params.get("v_log_slope")
    if v0 is None or v_slope is None:
        return {}
    return {
        "v16": v0 + v_slope * math.log(16),
        "v32": v0 + v_slope * math.log(32),
        "v64": v0 + v_slope * math.log(64),
    }


def _derived_v_by_setsize_ex2(model: "Model") -> Dict[str, float]:
    params = _model_params_by_name(model)
    v0 = params.get("v0")
    v_slope = params.get("v_log_slope")
    if v0 is None or v_slope is None:
        return {}
    return {
        "v4": v0 + v_slope * math.log(4),
        "v8": v0 + v_slope * math.log(8),
        "v16": v0 + v_slope * math.log(16),
    }


def _simulate_sample(model: "Model", sample: "Sample", conditions: Dict) -> "Sample":
    solution = model.solve(conditions=conditions)
    try:
        return solution.resample(len(sample))
    except Exception:
        # Fallback: approximate sampling from the PDF
        t = solution.t_domain()
        pdf_up = solution.pdf("upper")
        pdf_lo = solution.pdf("lower")
        pdf_up = np.maximum(pdf_up, 0)
        pdf_lo = np.maximum(pdf_lo, 0)
        p_up = np.trapz(pdf_up, t)
        p_lo = np.trapz(pdf_lo, t)
        p_up = p_up / (p_up + p_lo)

        n = len(sample)
        choices = np.random.binomial(1, p_up, size=n)
        rts = []
        for choice in choices:
            pdf = pdf_up if choice == 1 else pdf_lo
            cdf = np.cumsum(pdf)
            if cdf[-1] <= 0:
                rts.append(float(t[-1]))
                continue
            cdf = cdf / cdf[-1]
            u = np.random.rand()
            idx = int(np.searchsorted(cdf, u))
            rts.append(float(t[min(idx, len(t) - 1)]))

        sim_df = pd.DataFrame({"rt": rts, "response": choices})
        sim_df = sim_df.assign(**conditions)
        return _build_sample(sim_df)


def _sample_to_dataframe(sample: "Sample") -> pd.DataFrame:
    df = sample.to_pandas_dataframe()
    if "rt" not in df.columns:
        for candidate in ("RT", "reaction_time", "reaction_time_sec"):
            if candidate in df.columns:
                df = df.rename(columns={candidate: "rt"})
                break
    return df


def _rt_distribution_plot(
    observed_df: pd.DataFrame,
    simulated_df: pd.DataFrame,
    out_path: Path,
    title: str,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(observed_df["rt"].values, bins=40, alpha=0.6, label="Observed", density=True)
    ax.hist(simulated_df["rt"].values, bins=40, alpha=0.6, label="Simulated", density=True)
    ax.set_title(title)
    ax.set_xlabel("RT (s)")
    ax.set_ylabel("Density")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def _rt_overlay_by_condition(
    observed_df: pd.DataFrame,
    simulated_df: pd.DataFrame,
    condition_col: str,
    out_path: Path,
    title: str,
) -> None:
    """Overlay RT histograms by condition using matplotlib."""
    conditions = sorted(observed_df[condition_col].unique())
    n = len(conditions)
    fig, axes = plt.subplots(n, 1, figsize=(8, 3 * n), sharex=True)
    if n == 1:
        axes = [axes]

    for ax, condition in zip(axes, conditions):
        obs = observed_df[observed_df[condition_col] == condition]["rt"].values
        sim = simulated_df[simulated_df[condition_col] == condition]["rt"].values
        ax.hist(obs, bins=40, alpha=0.6, label="Observed", density=True)
        ax.hist(sim, bins=40, alpha=0.6, label="Simulated", density=True)
        ax.set_title(f"{condition_col}: {condition}")
        ax.set_ylabel("Density")
        ax.legend()

    axes[-1].set_xlabel("RT (s)")
    fig.suptitle(title, y=1.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _plot_drift_params(model: "Model", out_path: Path) -> None:
    params = model.get_model_parameters()
    if isinstance(params, dict):
        drift_params = {k: v for k, v in params.items() if k.startswith("v")}
    else:
        # PyDDM may return a list; map to parameter names if available
        names = list(getattr(model, "get_model_parameter_names", lambda: [])())
        drift_params = {}
        if names and len(names) == len(params):
            for name, value in zip(names, params):
                if name.startswith("v"):
                    drift_params[name] = value
        else:
            # Fallback: keep all parameters, label by index
            drift_params = {f"v_{idx}": val for idx, val in enumerate(params)}
    if not drift_params:
        return

    fig, ax = plt.subplots(figsize=(8, 4.5))
    labels = list(drift_params.keys())
    values = [float(drift_params[k]) for k in labels]
    ax.bar(labels, values, color="#4C78A8")
    ax.set_title("Drift rate estimates")
    ax.set_ylabel("v")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


# -----------------------------
# Experiment-specific pipelines
# -----------------------------
def fit_experiment_1(df: pd.DataFrame, config: FitConfig) -> None:
    exp_df = df[df["experiment"] == 1].copy()
    if exp_df.empty:
        print("Experiment 1: no data")
        return

    exp_dir = config.out_dir / "exp1"
    exp_dir.mkdir(parents=True, exist_ok=True)

    comparison_rows: List[Dict[str, object]] = []

    for task_label in (TASK_PRESENT, TASK_ABSENT):
        for target_label in sorted(EX1_TARGETS):
            subset = exp_df[
                (exp_df["task"] == task_label) & (exp_df["searchTarget"] == target_label)
            ].copy()
            if subset.empty:
                print(f"Experiment 1: no data for {task_label} | {target_label}")
                continue

            sample = _build_sample(subset, conditions_columns=["setSize"])
            tag = f"{_slugify(task_label)}_{_slugify(target_label)}"

            # Model A: 函数约束 drift rate v 随 set size 变化（log 线性，严格下降）
            model_a = Model(
                name=f"exp1_v_setsize_{tag}",
                drift=DriftFuncSetSizeLog(
                    v0=Fittable(minval=-5, maxval=5),
                    v_log_slope=Fittable(minval=-5, maxval=-1e-6),
                ),
                bound=BoundConstant(B=Fittable(minval=0.5, maxval=3.0)),
                noise=NoiseConstant(noise=1.0),
                overlay=OverlayNonDecision(nondectime=Fittable(minval=0.1, maxval=1.0)),
                IC=ICPointSourceCenter(),
                dt=0.001,
                dx=0.01,
                T_dur=MAX_RT_SEC+1.0,  # Ensure T_dur exceeds max RT to capture full distribution
            )
            model_a = _fit_model(model_a, sample)
            metrics_a = _model_metrics(model_a, sample)
            params_a = _model_params_dict(model_a, "param_")
            derived_a = _derived_v_by_setsize(model_a)

            _plot_drift_params(model_a, exp_dir / f"drift_params_model_a_{tag}.png")

            sim_rows = []
            for set_size in sorted(EX1_SET_SIZES):
                sub = subset[subset["setSize"] == set_size]
                if sub.empty:
                    continue
                sim = _simulate_sample(model_a, sample, {"setSize": set_size})
                sim_df = _sample_to_dataframe(sim)
                sim_rows.append(sim_df.assign(setSize=set_size))
            sim_all = pd.concat(sim_rows, ignore_index=True) if sim_rows else subset.iloc[:0]

            _rt_distribution_plot(
                subset,
                sim_all,
                exp_dir / f"rt_overall_model_a_{tag}.png",
                f"Experiment 1 ({task_label}, {target_label}) | Model A | Observed vs Simulated RT",
            )
            _rt_overlay_by_condition(
                subset,
                sim_all,
                "setSize",
                exp_dir / f"rt_by_setsize_model_a_{tag}.png",
                f"Experiment 1 ({task_label}, {target_label}) | Model A | RT by Set Size",
            )

            # Model B: 函数约束 drift rate v + boundary a 随 set size 变化
            model_b = Model(
                name=f"exp1_v_a_setsize_{tag}",
                drift=DriftFuncSetSizeLog(
                    v0=Fittable(minval=-5, maxval=5),
                    v_log_slope=Fittable(minval=-5, maxval=-1e-6),
                ),
                bound=BoundBySetSize(
                    a16=Fittable(minval=0.5, maxval=3.0),
                    a32=Fittable(minval=0.5, maxval=3.0),
                    a64=Fittable(minval=0.5, maxval=3.0),
                ),
                noise=NoiseConstant(noise=1.0),
                overlay=OverlayNonDecision(nondectime=Fittable(minval=0.1, maxval=1.0)),
                IC=ICPointSourceCenter(),
                dt=0.001,
                dx=0.01,
                T_dur=MAX_RT_SEC+1.0,  
            )
            model_b = _fit_model(model_b, sample)
            metrics_b = _model_metrics(model_b, sample)
            params_b = _model_params_dict(model_b, "param_")
            derived_b = _derived_v_by_setsize(model_b)

            _plot_drift_params(model_b, exp_dir / f"drift_params_model_b_{tag}.png")

            sim_rows = []
            for set_size in sorted(EX1_SET_SIZES):
                sub = subset[subset["setSize"] == set_size]
                if sub.empty:
                    continue
                sim = _simulate_sample(model_b, sample, {"setSize": set_size})
                sim_df = _sample_to_dataframe(sim)
                sim_rows.append(sim_df.assign(setSize=set_size))
            sim_all = pd.concat(sim_rows, ignore_index=True) if sim_rows else subset.iloc[:0]

            _rt_distribution_plot(
                subset,
                sim_all,
                exp_dir / f"rt_overall_model_b_{tag}.png",
                f"Experiment 1 ({task_label}, {target_label}) | Model B | Observed vs Simulated RT",
            )
            _rt_overlay_by_condition(
                subset,
                sim_all,
                "setSize",
                exp_dir / f"rt_by_setsize_model_b_{tag}.png",
                f"Experiment 1 ({task_label}, {target_label}) | Model B | RT by Set Size",
            )

            comparison_rows.append(
                {
                    "task": task_label,
                    "searchTarget": target_label,
                    "n_trials": len(subset),
                    "model": "A",
                    **metrics_a,
                    **params_a,
                    **derived_a,
                }
            )
            comparison_rows.append(
                {
                    "task": task_label,
                    "searchTarget": target_label,
                    "n_trials": len(subset),
                    "model": "B",
                    **metrics_b,
                    **params_b,
                    **derived_b,
                }
            )
            comparison_rows.append({})

    if comparison_rows:
        if comparison_rows[-1] == {}:
            comparison_rows.pop()
        pd.DataFrame(comparison_rows).to_csv(exp_dir / "model_comparison.csv", index=False)


def fit_experiment_2(df: pd.DataFrame, config: FitConfig) -> None:
    exp_df = df[df["experiment"] == 2].copy()
    if exp_df.empty:
        print("Experiment 2: no data")
        return

    exp_dir = config.out_dir / "exp2"
    exp_dir.mkdir(parents=True, exist_ok=True)

    comparison_rows: List[Dict[str, object]] = []

    for task_label in (TASK_PRESENT, TASK_ABSENT):
        for target_label in sorted(EX2_TARGETS):
            subset = exp_df[
                (exp_df["task"] == task_label) & (exp_df["searchTarget"] == target_label)
            ].copy()
            if subset.empty:
                print(f"Experiment 2: no data for {task_label} | {target_label}")
                continue

            sample = _build_sample(subset, conditions_columns=["setSize"])
            tag = f"{_slugify(task_label)}_{_slugify(target_label)}"

            # Model A: 函数约束 drift rate v 随 set size 变化（log 线性，严格下降）
            model_a = Model(
                name=f"exp2_v_setsize_{tag}",
                drift=DriftFuncSetSizeLog(
                    v0=Fittable(minval=-5, maxval=5),
                    v_log_slope=Fittable(minval=-5, maxval=-1e-6),
                ),
                bound=BoundConstant(B=Fittable(minval=0.5, maxval=3.0)),
                noise=NoiseConstant(noise=1.0),
                overlay=OverlayNonDecision(nondectime=Fittable(minval=0.1, maxval=1.0)),
                IC=ICPointSourceCenter(),
                dt=0.001,
                dx=0.01,
                T_dur=5.0,
            )
            model_a = _fit_model(model_a, sample)
            metrics_a = _model_metrics(model_a, sample)
            params_a = _model_params_dict(model_a, "param_")
            derived_a = _derived_v_by_setsize_ex2(model_a)

            _plot_drift_params(model_a, exp_dir / f"drift_params_model_a_{tag}.png")

            sim_rows = []
            for set_size in sorted(EX2_SET_SIZES):
                sub = subset[subset["setSize"] == set_size]
                if sub.empty:
                    continue
                sim = _simulate_sample(model_a, sample, {"setSize": set_size})
                sim_df = _sample_to_dataframe(sim)
                sim_rows.append(sim_df.assign(setSize=set_size))
            sim_all = pd.concat(sim_rows, ignore_index=True) if sim_rows else subset.iloc[:0]

            _rt_distribution_plot(
                subset,
                sim_all,
                exp_dir / f"rt_overall_model_a_{tag}.png",
                f"Experiment 2 ({task_label}, {target_label}) | Model A | Observed vs Simulated RT",
            )
            _rt_overlay_by_condition(
                subset,
                sim_all,
                "setSize",
                exp_dir / f"rt_by_setsize_model_a_{tag}.png",
                f"Experiment 2 ({task_label}, {target_label}) | Model A | RT by Set Size",
            )

            # Model B: 函数约束 drift rate v + boundary a 随 set size 变化
            model_b = Model(
                name=f"exp2_v_a_setsize_{tag}",
                drift=DriftFuncSetSizeLog(
                    v0=Fittable(minval=-5, maxval=5),
                    v_log_slope=Fittable(minval=-5, maxval=-1e-6),
                ),
                bound=BoundBySetSizeEx2(
                    a4=Fittable(minval=0.5, maxval=3.0),
                    a8=Fittable(minval=0.5, maxval=3.0),
                    a16=Fittable(minval=0.5, maxval=3.0),
                ),
                noise=NoiseConstant(noise=1.0),
                overlay=OverlayNonDecision(nondectime=Fittable(minval=0.1, maxval=1.0)),
                IC=ICPointSourceCenter(),
                dt=0.001,
                dx=0.01,
                T_dur=5.0,
            )
            model_b = _fit_model(model_b, sample)
            metrics_b = _model_metrics(model_b, sample)
            params_b = _model_params_dict(model_b, "param_")
            derived_b = _derived_v_by_setsize_ex2(model_b)

            _plot_drift_params(model_b, exp_dir / f"drift_params_model_b_{tag}.png")

            sim_rows = []
            for set_size in sorted(EX2_SET_SIZES):
                sub = subset[subset["setSize"] == set_size]
                if sub.empty:
                    continue
                sim = _simulate_sample(model_b, sample, {"setSize": set_size})
                sim_df = _sample_to_dataframe(sim)
                sim_rows.append(sim_df.assign(setSize=set_size))
            sim_all = pd.concat(sim_rows, ignore_index=True) if sim_rows else subset.iloc[:0]

            _rt_distribution_plot(
                subset,
                sim_all,
                exp_dir / f"rt_overall_model_b_{tag}.png",
                f"Experiment 2 ({task_label}, {target_label}) | Model B | Observed vs Simulated RT",
            )
            _rt_overlay_by_condition(
                subset,
                sim_all,
                "setSize",
                exp_dir / f"rt_by_setsize_model_b_{tag}.png",
                f"Experiment 2 ({task_label}, {target_label}) | Model B | RT by Set Size",
            )

            comparison_rows.append(
                {
                    "task": task_label,
                    "searchTarget": target_label,
                    "n_trials": len(subset),
                    "model": "A",
                    **metrics_a,
                    **params_a,
                    **derived_a,
                }
            )
            comparison_rows.append(
                {
                    "task": task_label,
                    "searchTarget": target_label,
                    "n_trials": len(subset),
                    "model": "B",
                    **metrics_b,
                    **params_b,
                    **derived_b,
                }
            )
            comparison_rows.append({})

    if comparison_rows:
        if comparison_rows[-1] == {}:
            comparison_rows.pop()
        pd.DataFrame(comparison_rows).to_csv(exp_dir / "model_comparison.csv", index=False)


# -----------------------------
# Reporting
# -----------------------------
def write_summary_report(config: FitConfig, summary: Dict[str, int]) -> None:
    report_path = config.out_dir / "summary_report.txt"

    lines = [
        "DDM Fitting Summary Report",
        "===========================",
        "",
        f"Input CSV: {config.csv_path}",
        f"Output Dir: {config.out_dir}",
        "",
        "Cleaning Summary:",
        f"- Total rows: {summary['total_rows']}",
        f"- Dropped missing: {summary['dropped_missing']}",
        f"- Dropped RT outliers: {summary['dropped_rt']}",
        f"- Dropped incorrect trials: {summary['dropped_incorrect']}",
        f"- RT unit detected: {summary['rt_unit']}",
        f"- Clean rows: {summary['clean_rows']}",
        "",
        "Modeling Notes:",
        "- Experiment 1: set size 影响 drift rate（证据积累效率）。",
        "- Experiment 2: target type 影响 drift rate（证据质量）。",
        "- Boundary (a), starting point (z), and nondecision time (Ter) are fixed unless specified.",
        "- noise parameter s 通常固定（DDM 可辨识性约束）。",
        "- 不做 quantile binning：PyDDM 使用 trial-level 似然直接拟合。",
        "- PyDDM 为最大似然拟合，不生成 MCMC posterior 或 trace。",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")


# -----------------------------
# Main
# -----------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="DDM fitting for visual search experiments")
    parser.add_argument("--csv", type=Path, default=Path("../results.csv"))
    parser.add_argument("--out", type=Path, default=Path("ddm_outputs"))
    parser.add_argument("--samples", type=int, default=DEFAULT_N_SAMPLES)
    parser.add_argument("--burn", type=int, default=DEFAULT_BURN)
    parser.add_argument("--thin", type=int, default=DEFAULT_THIN)
    parser.add_argument("--chains", type=int, default=DEFAULT_N_CHAINS)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    config = FitConfig(
        csv_path=args.csv,
        out_dir=args.out,
        n_samples=args.samples,
        burn=args.burn,
        thin=args.thin,
        n_chains=args.chains,
        seed=args.seed,
    )

    config.out_dir.mkdir(parents=True, exist_ok=True)

    df, summary = load_and_clean(config.csv_path)
    write_summary_report(config, summary)

    if Model is None:
        _require_pyddm()

    fit_experiment_1(df, config)
    fit_experiment_2(df, config)

    print(f"Done. Outputs saved to {config.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
