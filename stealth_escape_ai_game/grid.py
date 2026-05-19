from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

Pos = Tuple[int, int]


@dataclass
class MapData:
    width: int
    height: int
    walls: Set[Pos]
    exit_pos: Pos
    player_spawn: Pos
    guard_spawns: List[Pos]
    keys: Set[Pos]


class Grid:
    def __init__(self, map_data: MapData):
        self.width = map_data.width
        self.height = map_data.height
        self.walls = set(map_data.walls)
        self.exit_pos = map_data.exit_pos
        self.player_spawn = map_data.player_spawn
        self.guard_spawns = list(map_data.guard_spawns)
        self.keys = set(map_data.keys)

    @property
    def total_keys(self) -> int:
        return len(self.keys)

    def has_key(self, p: Pos) -> bool:
        return p in self.keys

    def collect_key(self, p: Pos) -> bool:
        if p in self.keys:
            self.keys.remove(p)
            return True
        return False

    def in_bounds(self, p: Pos) -> bool:
        x, y = p
        return 0 <= x < self.width and 0 <= y < self.height

    def is_wall(self, p: Pos) -> bool:
        return p in self.walls

    def passable(self, p: Pos) -> bool:
        return self.in_bounds(p) and not self.is_wall(p)
        

    def neighbors4(self, p: Pos) -> List[Pos]:
        x, y = p
        candidates = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        return [c for c in candidates if self.passable(c)]


def load_text_map(path: Path) -> MapData:
    """Load a fixed-size text map.

    Legend:
      # = wall
      . = empty
      P = player spawn
      G = guard spawn
      E = exit
    """
    lines = path.read_text(encoding="utf-8").splitlines()

    height = len(lines)
    width = len(lines[0]) if lines else 0

    walls: Set[Pos] = set()
    keys: Set[Pos] = set()
    exit_pos: Optional[Pos] = None
    player_spawn: Optional[Pos] = None
    guard_spawns: List[Pos] = []

    for y, row in enumerate(lines):
        if len(row) != width:
            raise ValueError(f"Map is not rectangular: {path}")
        for x, ch in enumerate(row):
            if ch == "#":
                walls.add((x, y))
            elif ch == "E":
                exit_pos = (x, y)
            elif ch == "P":
                player_spawn = (x, y)
            elif ch == "G":
                guard_spawns.append((x, y))
            elif ch == "K":
                keys.add((x, y))

    if exit_pos is None:
        raise ValueError(f"Map has no exit E: {path}")
    if player_spawn is None:
        raise ValueError(f"Map has no player spawn P: {path}")

    return MapData(
        width=width,
        height=height,
        walls=walls,
        exit_pos=exit_pos,
        player_spawn=player_spawn,
        guard_spawns=guard_spawns,
        keys=keys,
    )


def load_map_meta(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))
