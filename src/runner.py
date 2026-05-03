"""Main experiment runner using pygame for visual search task."""

from __future__ import annotations

import csv
import json
import shutil
import time
from dataclasses import asdict
from pathlib import Path
from random import Random

import pygame

from config import ExperimentConfig
from stimuli import (
    blit_centered,
    build_circle_layouts,
    build_grid_offsets,
    load_surface,
    make_fixation_surface,
    render_multiline_text,
)
from trials import (
    TrialOutcome,
    TrialSpec,
    build_experiment1_trials,
    build_experiment2_trials,
    ex1_row,
    ex2_row,
)

# Response keys for target present/absent
PRESENT_KEYS = {pygame.K_RIGHT, pygame.K_p}
ABSENT_KEYS = {pygame.K_LEFT, pygame.K_a}


class VisualSearchRunner:
    """Manages the visual search experiment including trials and data collection."""

    def __init__(
        self,
        config: ExperimentConfig,
        project_root: Path,
        output_root: Path,
        subject_id: str,
        seed: int,
        fullscreen: bool = False,
    ) -> None:
        self.config = config
        self.project_root = project_root
        self.output_root = output_root
        self.subject_id = subject_id
        self.seed = seed
        self.rng = Random(seed)
        self.fullscreen = fullscreen

        self.window: pygame.Surface | None = None
        self.clock = pygame.time.Clock()
        self.font_small: pygame.font.Font | None = None
        self.font_large: pygame.font.Font | None = None
        self.grid_offsets = build_grid_offsets()
        self.circle_layouts = build_circle_layouts()

    def run(self) -> Path:
        """Initialize pygame and run complete experiment sequence."""
        pygame.init()
        pygame.font.init()
        flags = pygame.FULLSCREEN if self.fullscreen else 0
        self.window = pygame.display.set_mode(self.config.window_size, flags)
        pygame.display.set_caption(f"Face Search - {self.config.display_name}")
        self.font_small = pygame.font.Font(None, 32)
        self.font_large = pygame.font.Font(None, 42)

        try:
            if self.config.experiment_id == "ex1":
                trial_specs = build_experiment1_trials(self.rng)
                rows = self._run_trials(trial_specs, ex1_row)
            else:
                trial_specs = build_experiment2_trials(self.rng)
                rows = self._run_trials(trial_specs, ex2_row)
            return self._save_outputs(rows, trial_specs)
        finally:
            pygame.quit()

    def _run_trials(
        self, trial_specs: list[TrialSpec], row_builder
    ) -> list[dict[str, int]]:
        self._show_instructions()
        self._show_practice()

        rows: list[dict[str, int]] = []
        self._show_block_banner(1)

        for trial_spec in trial_specs:
            outcome = self._run_trial(trial_spec)
            rows.append(row_builder(trial_spec, outcome))

            if trial_spec.trial_number in self.config.break_points:
                block_index = (
                    self.config.break_points.index(trial_spec.trial_number) + 2
                )
                self._show_break(block_index)

        self._show_completion()
        return rows

    def _run_trial(
        self,
        spec: TrialSpec,
        *,
        target_duration: float | None = None,
        fixation_min: float | None = None,
        fixation_max: float | None = None,
        feedback_duration: float | None = None,
        timeout_seconds: float | None = None,
    ) -> TrialOutcome:
        """A single trial: show target, fixation, search array, and collect response."""
        assert self.window is not None

        target_surface = self._load_target_surface(spec)
        search_surface, array_location = self._build_search_surface(
            spec, target_surface
        )

        target_duration = (
            self.config.target_duration if target_duration is None else target_duration
        )
        fixation_min = (
            self.config.fixation_min if fixation_min is None else fixation_min
        )
        fixation_max = (
            self.config.fixation_max if fixation_max is None else fixation_max
        )
        feedback_duration = (
            self.config.feedback_duration
            if feedback_duration is None
            else feedback_duration
        )
        timeout_seconds = (
            self.config.timeout_seconds if timeout_seconds is None else timeout_seconds
        )

        self.window.fill((0, 0, 0))
        blit_centered(self.window, target_surface, self.window.get_rect().center)
        pygame.display.flip()
        self._wait(target_duration)

        fixation = make_fixation_surface(
            self.config.window_size, (150, 150, 150), (0, 0, 0)
        )
        self.window.blit(fixation, (0, 0))
        pygame.display.flip()
        self._wait(self.rng.uniform(fixation_min, fixation_max))

        self.window.fill((0, 0, 0))
        self.window.blit(search_surface, (0, 0))
        pygame.display.flip()
        search_onset = time.perf_counter()

        response_key, rt_ms, timed_out = self._wait_for_response(
            search_onset, timeout_seconds
        )
        correct = self._is_correct_response(response_key, spec.target_present)
        self._show_feedback(correct, timed_out, feedback_duration)

        return TrialOutcome(
            response_key=response_key,
            rt_ms=rt_ms,
            correct=correct,
            timed_out=timed_out,
            array_location=array_location,
        )

    def _wait_for_response(
        self, search_onset: float, timeout_seconds: float | None
    ) -> tuple[str, int, bool]:
        """Wait for participant response with timeout."""
        assert self.window is not None

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                if event.type != pygame.KEYDOWN:
                    continue
                if event.key in PRESENT_KEYS:
                    return "p", int((time.perf_counter() - search_onset) * 1000), False
                if event.key in ABSENT_KEYS:
                    return "a", int((time.perf_counter() - search_onset) * 1000), False

            # Return timeout response if time exceeded
            if (
                timeout_seconds is not None
                and time.perf_counter() - search_onset > timeout_seconds
            ):
                return "x", 0, True

            self.clock.tick(120)

    def _is_correct_response(self, response_key: str, target_present: bool) -> bool:
        if response_key == "x":
            return False
        if response_key == "p":
            return target_present
        return not target_present

    def _show_feedback(
        self, correct: bool, timed_out: bool, feedback_duration: float
    ) -> None:
        assert self.window is not None
        assert self.font_large is not None
        color = (90, 255, 60) if correct else (180, 0, 30)
        self.window.fill((0, 0, 0))
        fixation = make_fixation_surface(self.config.window_size, color, (0, 0, 0))
        self.window.blit(fixation, (0, 0))

        if timed_out:
            for surface, rect in self._render_feedback_lines(["Time", "Out!"]):
                self.window.blit(surface, rect)

        pygame.display.flip()
        self._wait(0.6 if timed_out else feedback_duration)

    def _render_feedback_lines(
        self, lines: list[str]
    ) -> list[tuple[pygame.Surface, pygame.Rect]]:
        assert self.window is not None
        assert self.font_large is not None
        screen_rect = self.window.get_rect()
        rendered = []
        for index, line in enumerate(lines):
            surface = self.font_large.render(line, True, (255, 255, 255))
            center = (
                screen_rect.centerx + (index - 0.5) * 120,
                screen_rect.centery - 10,
            )
            rendered.append((surface, surface.get_rect(center=center)))
        return rendered

    def _show_instructions(self) -> None:
        assert self.window is not None
        assert self.font_small is not None
        instructions = [
            "press either key to start",
            "your task is to find the target picture as fast as possible",
            "when you find your target picture, press RIGHT or P (YES key | Present)",
            "if you cannot find your target picture, press LEFT or A (NO key | Absent)",
            "focus on the center cross whenever it is on screen",
            "practice trials are next",
        ]
        for text in instructions:
            self.window.fill((128, 128, 128))
            lines = render_multiline_text(self.font_small, text, (50, 50, 50))
            for line_surface in lines:
                self.window.blit(
                    line_surface,
                    line_surface.get_rect(center=self.window.get_rect().center),
                )
            pygame.display.flip()
            self._wait_for_any_key()

    def _show_practice(self) -> None:
        assert self.window is not None
        practice = self._build_practice_trials()
        self.window.fill((0, 0, 0))
        pygame.display.flip()
        self._wait(1.0)

        correct_count = 0
        for spec in practice:
            outcome = self._run_trial(
                spec,
                target_duration=self.config.practice_target_duration,
                fixation_min=self.config.practice_fixation_duration,
                fixation_max=self.config.practice_fixation_duration,
                feedback_duration=1.25,
                timeout_seconds=None,
            )
            if outcome.correct:
                correct_count += 1

        assert self.font_small is not None
        self.window.fill((128, 128, 128))
        summary_lines = [
            f"that was {correct_count}/6 correct for the practice run",
            "press either key when you are ready to begin",
        ]
        y = self.window.get_rect().centery - 30
        for text in summary_lines:
            surface = self.font_small.render(text, True, (50, 50, 50))
            rect = surface.get_rect(center=(self.window.get_rect().centerx, y))
            self.window.blit(surface, rect)
            y += 40
        pygame.display.flip()
        self._wait_for_any_key()

    def _build_practice_trials(self) -> list[TrialSpec]:
        present_trials = {1, 3, 4}
        specs = []
        for index in range(1, 7):
            target_present = index in present_trials
            specs.append(
                TrialSpec(
                    trial_number=index,
                    category=index,  # Used as practice trial index (1..6)
                    trial_type=index,
                    set_size=32 if self.config.experiment_id == "ex1" else 16,
                    target_present=target_present,
                    target_variant="pFace",  # Not used for practice
                    target_source_index=None,
                    is_practice=True,
                )
            )
        return specs

    def _show_break(self, block_index: int) -> None:
        assert self.window is not None
        assert self.font_small is not None
        self.window.fill((128, 128, 128))
        lines = [
            "take a quick break!",
            "press either key to continue",
            f"starting block {block_index}",
        ]
        y = self.window.get_rect().centery - 40
        for text in lines:
            surface = self.font_small.render(text, True, (50, 50, 50))
            self.window.blit(
                surface, surface.get_rect(center=(self.window.get_rect().centerx, y))
            )
            y += 40
        pygame.display.flip()
        self._wait_for_any_key()
        self._show_block_banner(block_index)

    def _show_block_banner(self, block_index: int) -> None:
        assert self.window is not None
        assert self.font_small is not None
        self.window.fill((0, 0, 0))
        banner = self.font_small.render(
            f"Starting block {block_index}", True, (255, 255, 255)
        )
        self.window.blit(banner, banner.get_rect(center=self.window.get_rect().center))
        pygame.display.flip()
        self._wait(2.0)

    def _show_completion(self) -> None:
        assert self.window is not None
        assert self.font_small is not None
        self.window.fill((0, 0, 0))
        lines = ["all done!", "thanks for participating!"]
        y = self.window.get_rect().centery - 20
        for text in lines:
            surface = self.font_small.render(text, True, (255, 255, 255))
            self.window.blit(
                surface, surface.get_rect(center=(self.window.get_rect().centerx, y))
            )
            y += 40
        pygame.display.flip()

    def _wait_for_any_key(self) -> None:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                if event.type == pygame.KEYDOWN:
                    return
            self.clock.tick(120)

    def _wait(self, seconds: float) -> None:
        start = time.perf_counter()
        while time.perf_counter() - start < seconds:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
            self.clock.tick(120)

    def _load_target_surface(self, spec: TrialSpec) -> pygame.Surface:
        if spec.is_practice:
            # Practice trials: read from practiceTrials folder
            practice_dir = (
                self.config.stimuli_root / "practiceTrials" / str(spec.category)
            )
            target_path = str(practice_dir / "0.png")
        else:
            # Main trials: read from target category folder
            category_dir = (
                self.config.stimuli_root
                / self.config.target_folder_name
                / str(spec.category)
            )
            if self.config.experiment_id == "ex1":
                filename = "0.png" if spec.target_variant == "pFace" else "20.png"
                target_path = str(category_dir / filename)
            else:
                target_path = str(category_dir / f"{spec.target_variant}.png")

        surface = load_surface(target_path)

        # Apply mask for ex2 trials
        if self.config.experiment_id == "ex2":
            mask_path = self.config.stimuli_root / "circularMask.png"
            return load_surface(target_path, str(mask_path))

        return surface

    def _build_search_surface(
        self, spec: TrialSpec, target_surface: pygame.Surface
    ) -> tuple[pygame.Surface, int | None]:
        assert self.window is not None
        screen_width, screen_height = self.config.window_size
        search_surface = pygame.Surface((screen_width, screen_height))
        search_surface.fill((0, 0, 0))

        # EX1 logic
        if self.config.experiment_id == "ex1":
            location_order = list(range(1, 65))
            self.rng.shuffle(location_order)

            if spec.is_practice:
                # Practice trials: read from practiceTrials folder (32 items)
                practice_dir = (
                    self.config.stimuli_root / "practiceTrials" / str(spec.category)
                )
                target_location = location_order[0]
                for index in range(spec.set_size):
                    location_index = location_order[index]
                    if index == 0 and spec.target_present:
                        source_surface = target_surface
                    elif index == 0 and not spec.target_present:
                        # For target-absent trials, use image 32 at position 0
                        source_surface = load_surface(str(practice_dir / "32.png"))
                    else:
                        source_surface = load_surface(
                            str(practice_dir / f"{index}.png")
                        )

                    offset_x, offset_y = self.grid_offsets[location_index - 1]
                    rect = source_surface.get_rect(
                        center=(
                            screen_width // 2 + offset_x,
                            screen_height // 2 + offset_y,
                        )
                    )
                    search_surface.blit(source_surface, rect)
            else:
                # Main trials: standard logic
                distractor_order = list(range(1, 66))
                self.rng.shuffle(distractor_order)

                category_dir = (
                    self.config.stimuli_root
                    / self.config.target_folder_name
                    / str(spec.category)
                )
                target_location = location_order[0]
                for index in range(spec.set_size):
                    location_index = location_order[index]
                    if index == 0 and spec.target_present:
                        source_surface = target_surface
                    else:
                        candidate = distractor_order[index]
                        if candidate == spec.target_source_index:
                            candidate = distractor_order[spec.set_size]
                        source_surface = load_surface(
                            str(category_dir / f"{candidate}.png")
                        )

                    offset_x, offset_y = self.grid_offsets[location_index - 1]
                    rect = source_surface.get_rect(
                        center=(
                            screen_width // 2 + offset_x,
                            screen_height // 2 + offset_y,
                        )
                    )
                    search_surface.blit(source_surface, rect)

            return search_surface, target_location

        # EX2 logic
        location_order = list(range(1, spec.set_size + 1))
        self.rng.shuffle(location_order)

        if spec.is_practice:
            # Practice trials: read from practiceTrials folder (16 items for ex2)
            practice_dir = (
                self.config.stimuli_root / "practiceTrials" / str(spec.category)
            )
            mask_path = self.config.stimuli_root / "circularMask.png"
            positions = self.circle_layouts[spec.set_size]
            for index in range(spec.set_size):
                location_index = location_order[index]
                if index == 0 and spec.target_present:
                    source_surface = target_surface
                elif index == 0 and not spec.target_present:
                    # For target-absent trials, use image 17 at position 0
                    source_surface = load_surface(
                        str(practice_dir / "17.png"), str(mask_path)
                    )
                else:
                    source_surface = load_surface(
                        str(practice_dir / f"{index}.png"), str(mask_path)
                    )

                offset_x, offset_y = positions[location_index - 1]
                rect = source_surface.get_rect(
                    center=(screen_width // 2 + offset_x, screen_height // 2 + offset_y)
                )
                search_surface.blit(source_surface, rect)
        else:
            # Main trials: standard logic
            distractor_order = list(range(1, 29))
            self.rng.shuffle(distractor_order)

            category_dir = (
                self.config.stimuli_root
                / self.config.target_folder_name
                / str(spec.category)
            )
            mask_path = self.config.stimuli_root / "circularMask.png"
            positions = self.circle_layouts[spec.set_size]
            for index in range(spec.set_size):
                location_index = location_order[index]
                if index == 0 and spec.target_present:
                    source_surface = target_surface
                else:
                    if spec.set_size == 4:
                        distractor_index = index
                    elif spec.set_size == 8:
                        distractor_index = index + 4
                    else:
                        distractor_index = index + 12
                    filename = f"{distractor_order[distractor_index]}.png"
                    filepath = str(category_dir / filename)
                    source_surface = load_surface(filepath, str(mask_path))

                offset_x, offset_y = positions[location_index - 1]
                rect = source_surface.get_rect(
                    center=(screen_width // 2 + offset_x, screen_height // 2 + offset_y)
                )
                search_surface.blit(source_surface, rect)

        return search_surface, None

    def _save_outputs(
        self, rows: list[dict[str, int]], trial_specs: list[TrialSpec]
    ) -> Path:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        base_dir = (
            self.output_root / self.config.experiment_id / self.subject_id / timestamp
        )
        response_dir = base_dir / "responseData"
        manifest_dir = base_dir / "manifest"
        response_dir.mkdir(parents=True, exist_ok=True)
        manifest_dir.mkdir(parents=True, exist_ok=True)

        csv_path = (
            response_dir
            / f"{self.subject_id}_{self.config.experiment_id}_{timestamp}.csv"
        )
        headers = list(rows[0].keys()) if rows else []
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        manifest_path = manifest_dir / "run.json"
        manifest = {
            "subject_id": self.subject_id,
            "seed": self.seed,
            "config": asdict(self.config),
            "trial_count": len(trial_specs),
            "trial_order": [asdict(spec) for spec in trial_specs],
            "csv_path": str(csv_path),
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, default=str), encoding="utf-8"
        )

        script_copy_dir = base_dir / "scriptCopies"
        script_copy_dir.mkdir(parents=True, exist_ok=True)
        source_file = Path(__file__).resolve().parent / "cli.py"
        shutil.copy2(
            source_file,
            script_copy_dir
            / f"{self.subject_id}_{self.config.experiment_id}_{timestamp}.py",
        )

        return csv_path
