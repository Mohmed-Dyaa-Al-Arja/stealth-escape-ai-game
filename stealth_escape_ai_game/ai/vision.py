from __future__ import annotations

from typing import Iterable, List, Set, Tuple

Pos = Tuple[int, int]


def bresenham_line(a: Pos, b: Pos) -> List[Pos]:
    """Return grid cells on a line from a to b (inclusive) using Bresenham.

    Works for any octant. Used for line-of-sight checks.
    """
    x0, y0 = a
    x1, y1 = b

    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)

    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1

    err = dx + dy

    out: List[Pos] = []
    x, y = x0, y0
    while True:
        out.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy

    return out


def has_line_of_sight(start: Pos, end: Pos, is_wall: callable) -> bool:
    """True if no wall blocks the segment start→end (excluding start cell)."""
    for cell in bresenham_line(start, end)[1:]:
        if is_wall(cell):
            return False
    return True


def cone_cells(origin: Pos, facing: str, vision_range: int) -> Set[Pos]:
    """Generate candidate cells in a simple grid 'cone'.

    Cone is a wedge in the facing direction; width grows with distance.
    Facing is one of: 'N','E','S','W'.
    """
    ox, oy = origin
    out: Set[Pos] = set()

    # Forward vector and its perpendicular (for cone widening).
    # Example: facing North => forward (0,-1), perpendicular (1,0)
    fwd = {
        "N": (0, -1),
        "E": (1, 0),
        "S": (0, 1),
        "W": (-1, 0),
    }.get(facing, (0, 1))
    dx, dy = fwd
    px, py = (-dy, dx)

    for d in range(1, vision_range + 1):
        w = d // 2
        for off in range(-w, w + 1):
            out.add((ox + dx * d + px * off, oy + dy * d + py * off))

    return out


def visible_cells(origin: Pos, facing: str, vision_range: int, in_bounds: callable, is_wall: callable) -> Set[Pos]:
    """Compute visible cells within a cone, blocked by walls."""
    candidates = [c for c in cone_cells(origin, facing, vision_range) if in_bounds(c)]

    out: Set[Pos] = set()
    for c in candidates:
        if has_line_of_sight(origin, c, is_wall=is_wall):
            out.add(c)

    return out
