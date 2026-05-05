"""Visualization module for Face Perception experiments."""

from .analysis import load_results, analyze_by_condition
from .plots import (
    plot_rt_by_setsize,
    plot_accuracy_by_condition,
    plot_experiment_comparison,
    save_all_plots,
)

__all__ = [
    "load_results",
    "analyze_by_condition",
    "plot_rt_by_setsize",
    "plot_accuracy_by_condition",
    "plot_experiment_comparison",
    "save_all_plots",
]
