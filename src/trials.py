"""Trial specification and sequence generation for experiments."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from collections import Counter

# Sample a shorter randomized subset for quick runs.
TEST_SAMPLE_DIVISOR = 6


@dataclass(frozen=True)
class TrialSpec:
    """Immutable trial configuration parameters."""

    trial_number: int
    category: int
    trial_type: int
    set_size: int
    target_present: bool
    target_variant: str
    target_source_index: int | None = None
    is_practice: bool = False


@dataclass(frozen=True)
class TrialOutcome:
    """Immutable trial response data."""

    response_key: str
    rt_ms: int
    correct: bool
    timed_out: bool
    array_location: int | None = None


def _no_adjacent_duplicates(values: list[int], rng: Random) -> list[int]:
    """Shuffle list ensuring no consecutive identical values using greedy algorithm."""
    if len(values) < 2:
        return values[:]

    # Count occurrences of each value
    counts = Counter(values)
    result: list[int] = []
    last_value = None
    available = list(counts.keys())

    while available:
        # Find candidates (aren't the last placed value and have remaining count)
        candidates = [v for v in available if v != last_value and counts[v] > 0]

        if not candidates:
            # No valid candidate; need to pick from remaining values even if adjacent
            # This shouldn't happen with valid input, but fallback to any available
            candidates = [v for v in available if counts[v] > 0]

        # Randomly pick from valid candidates
        chosen = rng.choice(candidates)
        result.append(chosen)
        counts[chosen] -= 1

        # Remove values with 0 count
        available = [v for v in available if counts[v] > 0]
        last_value = chosen

    return result


def _category_sequence(category_count: int, repeats: int, rng: Random) -> list[int]:
    """Create randomized category sequence with no adjacent repeats."""
    categories = list(range(1, category_count + 1)) * repeats
    return _no_adjacent_duplicates(categories, rng)


def _sample_trials(
    specs: list[TrialSpec], rng: Random, divisor: int
) -> list[TrialSpec]:
    """Randomly sample a subset of trials and renumber trial indices."""
    if divisor <= 1:
        return specs

    count = max(1, len(specs) // divisor)
    shuffled = specs[:]
    rng.shuffle(shuffled)
    sampled = shuffled[:count]

    return [
        TrialSpec(
            trial_number=index,
            category=spec.category,
            trial_type=spec.trial_type,
            set_size=spec.set_size,
            target_present=spec.target_present,
            target_variant=spec.target_variant,
            target_source_index=spec.target_source_index,
            is_practice=spec.is_practice,
        )
        for index, spec in enumerate(sampled, start=1)
    ]


def build_experiment1_trials(rng: Random) -> list[TrialSpec]:
    """Generate complete trial sequence for Experiment 1 (26 categories x 12 types)."""
    category_order = _category_sequence(26, 12, rng)
    trial_type_orders = {category: list(range(1, 13)) for category in range(1, 27)}
    # Randomize trial type order within each category
    for order in trial_type_orders.values():
        rng.shuffle(order)

    category_counts = {category: 0 for category in range(1, 27)}
    specs: list[TrialSpec] = []

    for trial_number, category in enumerate(category_order, start=1):
        index = category_counts[category]
        category_counts[category] += 1
        trial_type = trial_type_orders[category][index]

        target_present = trial_type in {1, 2, 3, 7, 8, 9}
        set_size = {
            1: 16,
            2: 32,
            3: 64,
            4: 16,
            5: 32,
            6: 64,
            7: 16,
            8: 32,
            9: 64,
            10: 16,
            11: 32,
            12: 64,
        }[trial_type]
        target_variant = "pFace" if trial_type <= 6 else "nonFace"

        specs.append(
            TrialSpec(
                trial_number=trial_number,
                category=category,
                trial_type=trial_type,
                set_size=set_size,
                target_present=target_present,
                target_variant=target_variant,
                target_source_index=20,
            )
        )

    return _sample_trials(specs, rng, TEST_SAMPLE_DIVISOR)


def build_experiment2_trials(rng: Random) -> list[TrialSpec]:
    """Generate complete trial sequence for Experiment 2 (23 categories x 18 types)."""
    category_order = _category_sequence(23, 18, rng)
    trial_type_orders = {category: list(range(1, 19)) for category in range(1, 24)}
    # Randomize trial type order within each category
    for order in trial_type_orders.values():
        rng.shuffle(order)

    category_counts = {category: 0 for category in range(1, 24)}
    presence_pattern = [1, 0] * 9
    variant_pattern = ["nonFace", "pFace", "realFace"] * 6
    set_size_pattern = [4, 8, 16] * 6

    specs: list[TrialSpec] = []
    for trial_number, category in enumerate(category_order, start=1):
        index = category_counts[category]
        category_counts[category] += 1
        trial_type = trial_type_orders[category][index]

        specs.append(
            TrialSpec(
                trial_number=trial_number,
                category=category,
                trial_type=trial_type,
                set_size=set_size_pattern[trial_type - 1],
                target_present=bool(presence_pattern[trial_type - 1]),
                target_variant=variant_pattern[trial_type - 1],
            )
        )

    return _sample_trials(specs, rng, TEST_SAMPLE_DIVISOR)


def ex1_row(spec: TrialSpec, outcome: TrialOutcome) -> dict[str, int]:
    """Format trial data for Experiment 1 CSV output."""
    return {
        "trialNumber": spec.trial_number,
        "type": spec.trial_type,
        "stimulusCategory": spec.category,
        "PFstimulus": int(spec.target_variant == "pFace"),
        "setSize": spec.set_size,
        "targetPresent": int(spec.target_present),
        "correctResponse": int(outcome.correct),
        "rt": outcome.rt_ms,
        "timeoutOrKeyNotPressed": int(outcome.timed_out),
        "targetYokedImageSource": int(spec.target_source_index or 0),
        "targetArrayLocation": int(outcome.array_location or 0),
    }


def ex2_row(spec: TrialSpec, outcome: TrialOutcome) -> dict[str, int]:
    """Format trial data for Experiment 2 CSV output."""
    return {
        "trialNumber": spec.trial_number,
        "type": spec.trial_type,
        "stimulusCategory": spec.category,
        "nonFace": int(spec.target_variant == "nonFace"),
        "pFace": int(spec.target_variant == "pFace"),
        "realFace": int(spec.target_variant == "realFace"),
        "setSize": spec.set_size,
        "targetPresent": int(spec.target_present),
        "correctResponse": int(outcome.correct),
        "rt": outcome.rt_ms,
        "timeoutOrKeyNotPressed": int(outcome.timed_out),
    }
