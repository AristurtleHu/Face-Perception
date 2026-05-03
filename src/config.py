"""Configuration definitions for experiments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple


class DisplayProfile(NamedTuple):
    window_size: tuple[int, int]
    stimulus_spacing: int


DISPLAY_PROFILES = {
    1080: DisplayProfile(window_size=(1600, 1100), stimulus_spacing=2),
    float('inf'): DisplayProfile(window_size=(1600, 1200), stimulus_spacing=12),
}


def get_display_profile(screen_height: int) -> DisplayProfile:
    for threshold in sorted(DISPLAY_PROFILES.keys()):
        if screen_height <= threshold:
            return DISPLAY_PROFILES[threshold]
    return DISPLAY_PROFILES[float('inf')]

from resources import resource_path


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
    window_size: tuple[int, int] = (1600, 1100)
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


def build_experiment_config(
    experiment_id: str, repo_root: Path | None = None
) -> ExperimentConfig:
    """Create experiment configuration based on experiment ID."""
    experiment_id = experiment_id.lower()
    root_path = repo_root if repo_root is not None else resource_path()
    if experiment_id == "ex1":
        return ExperimentConfig(
            experiment_id="ex1",
            display_name="Experiment 1",
            material_dir=root_path / "docs" / "materials" / "experiment1materials",
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
            material_dir=root_path / "docs" / "materials" / "experiment2materials",
            stimuli_dir_name="ex2stimuli",
            target_folder_name="targetCategory",
            category_count=23,
            trial_type_count=18,
            set_sizes=(4, 8, 16),
            layout="circle",
            break_points=(69, 138, 207, 276, 345),
        )

    raise ValueError(f"Unknown experiment_id: {experiment_id}")
