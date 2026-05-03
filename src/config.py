"""Configuration definitions for experiments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExperimentConfig:
    """Immutable configuration container for experiment parameters."""

    experiment_id: str
    display_name: str
    material_dir: Path
    stimuli_dir_name: str
    target_folder_name: str
    category_count: int
    trial_type_count: int
    set_sizes: tuple[int, ...]
    layout: str
    break_points: tuple[int, ...]
    window_size: tuple[int, int] = (1600, 1200)
    target_duration: float = 1.6
    fixation_min: float = 0.4
    fixation_max: float = 0.6
    timeout_seconds: float = 15.0
    feedback_duration: float = 0.25
    practice_target_duration: float = 1.8
    practice_fixation_duration: float = 0.7

    @property
    def stimuli_root(self) -> Path:
        return self.material_dir / self.stimuli_dir_name


def build_experiment_config(experiment_id: str, repo_root: Path) -> ExperimentConfig:
    """Create experiment configuration based on experiment ID."""
    experiment_id = experiment_id.lower()
    if experiment_id == "ex1":
        return ExperimentConfig(
            experiment_id="ex1",
            display_name="Experiment 1",
            material_dir=repo_root / "docs" / "materials" / "experiment1materials",
            stimuli_dir_name="ex1Stimuli",
            target_folder_name="stimulusCategories",
            category_count=26,
            trial_type_count=12,
            set_sizes=(16, 32, 64),
            layout="grid",
            break_points=(52, 104, 156, 208, 260),
        )

    if experiment_id == "ex2":
        return ExperimentConfig(
            experiment_id="ex2",
            display_name="Experiment 2",
            material_dir=repo_root / "docs" / "materials" / "experiment2materials",
            stimuli_dir_name="ex2stimuli",
            target_folder_name="targetCategory",
            category_count=23,
            trial_type_count=18,
            set_sizes=(4, 8, 16),
            layout="circle",
            break_points=(69, 138, 207, 276, 345),
        )

    raise ValueError(f"Unknown experiment_id: {experiment_id}")
