from __future__ import annotations

from dataclasses import dataclass
from random import Random
from collections import Counter


@dataclass(frozen=True)
class TrialSpec:
    trial_number: int
    category: int
    trial_type: int
    set_size: int
    target_present: bool
    target_variant: str
    target_source_index: int | None = None


@dataclass(frozen=True)
class TrialOutcome:
    response_key: str
    rt_ms: int
    correct: bool
    timed_out: bool
    array_location: int | None = None


def _no_adjacent_duplicates(values: list[int], rng: Random) -> list[int]:
    if len(values) < 2:
        return values[:]

    shuffled = values[:]
    while True:
        rng.shuffle(shuffled)
        if all(left != right for left, right in zip(shuffled, shuffled[1:])):
            return shuffled[:]


def _category_sequence(category_count: int, repeats: int, rng: Random) -> list[int]:
    categories = list(range(1, category_count + 1)) * repeats
    return _no_adjacent_duplicates(categories, rng)


def build_experiment1_trials(rng: Random) -> list[TrialSpec]:
    category_order = _category_sequence(26, 12, rng)
    trial_type_orders = {category: list(range(1, 13)) for category in range(1, 27)}
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

    return specs


def build_experiment2_trials(rng: Random) -> list[TrialSpec]:
    category_order = _category_sequence(23, 18, rng)
    trial_type_orders = {category: list(range(1, 19)) for category in range(1, 24)}
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

    return specs


def ex1_row(spec: TrialSpec, outcome: TrialOutcome) -> dict[str, int]:
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
