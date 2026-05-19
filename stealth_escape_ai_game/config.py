from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Difficulty:
    name: str
    active_guard_count: int
    vision_range: int
    detection_pause_turns: int
    investigation_turns: int
    prediction_horizon: int
    intercept_min_advantage: int
    guard_speed: int  


EASY = Difficulty(
    name="Easy",
    active_guard_count=2,
    vision_range=5,
    detection_pause_turns=1,
    investigation_turns=2,
    prediction_horizon=0,
    intercept_min_advantage=999,
    guard_speed=1,
)

MEDIUM = Difficulty(
    name="Medium",
    active_guard_count=3,
    vision_range=7,
    detection_pause_turns=1,
    investigation_turns=3,
    prediction_horizon=6,
    intercept_min_advantage=0,
    guard_speed=1,
)

HARD = Difficulty(
    name="Hard",
    active_guard_count=4,
    vision_range=9,
    detection_pause_turns=1,
    investigation_turns=4,
    prediction_horizon=10,
    intercept_min_advantage=1,
    guard_speed=2,
)


DIFFICULTIES = {
    1: EASY,
    2: MEDIUM,
    3: HARD,
}