from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

Pos = Tuple[int, int]


class GuardState(str, Enum):
    PATROL = "PATROL"
    DETECTION = "DETECTION"
    # MEMORY = lost sight; move/search toward last seen player before returning to PATROL
    MEMORY = "MEMORY"
    CHASE = "CHASE"


class Facing(str, Enum):
    N = "N"
    E = "E"
    S = "S"
    W = "W"


def facing_from_delta(dx: int, dy: int) -> Facing:
    if abs(dx) >= abs(dy):
        return Facing.E if dx > 0 else Facing.W
    return Facing.S if dy > 0 else Facing.N


@dataclass
class Player:
    pos: Pos

    render_pos: Tuple[float, float] = field(default_factory=lambda: (0.0, 0.0))
    facing: Facing = Facing.S

    def update_facing(self, dx: int, dy: int):
        if dx != 0 or dy != 0:
            self.facing = facing_from_delta(dx, dy)

    def apply_move(self, new_pos: Pos) -> None:
        """Move player and keep facing/render_pos in sync."""
        dx = new_pos[0] - self.pos[0]
        dy = new_pos[1] - self.pos[1]
        if dx != 0 or dy != 0:
            self.facing = facing_from_delta(dx, dy)
        self.pos = new_pos
        self.render_pos = (float(new_pos[0]), float(new_pos[1]))


@dataclass
class Guard:
    id: int
    pos: Pos
    
    patrol_path: List[Pos]
    patrol_index: int = 0

    facing: Facing = Facing.S

    # 👇 جديد (للـ animation)
    render_pos: Tuple[float, float] = field(default_factory=lambda: (0.0, 0.0))

    state: GuardState = GuardState.PATROL
    state_timer: int = 0
    memory_timer: int = 0
    vision_range: int = 5

    last_seen_player: Optional[Pos] = None
    last_seen_dir: Optional[tuple[int, int]] = None
    investigation_timer: int = 0
    investigation_origin: Optional[Pos] = None
    investigation_goal: Optional[Pos] = None

    last_visible: set[Pos] = field(default_factory=set)
    last_path: List[Pos] = field(default_factory=list)
    last_explored: List[Pos] = field(default_factory=list)

    roam_goal: Optional[Pos] = None
    roam_last_goal: Optional[Pos] = None
    roam_recent_goals: List[Pos] = field(default_factory=list)

    def step_patrol(self) -> Optional[Pos]:
        if not self.patrol_path:
            return None

        if self.pos in self.patrol_path:
            self.patrol_index = self.patrol_path.index(self.pos)

        next_index = (self.patrol_index + 1) % len(self.patrol_path)
        return self.patrol_path[next_index]

    def apply_move(self, new_pos: Pos) -> None:
        dx = new_pos[0] - self.pos[0]
        dy = new_pos[1] - self.pos[1]

        if dx != 0 or dy != 0:
            self.facing = facing_from_delta(dx, dy)

        self.pos = new_pos
        # Keep render_pos in sync (renderer can still smooth if desired).
        self.render_pos = (float(new_pos[0]), float(new_pos[1]))