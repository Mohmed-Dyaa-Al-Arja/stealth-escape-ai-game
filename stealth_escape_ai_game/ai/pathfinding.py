from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from collections import deque
from typing import Dict, Iterable, List, Optional, Set, Tuple

Pos = Tuple[int, int]


@dataclass
class PathResult:
    path: List[Pos]
    nodes_explored: List[Pos]
    reason: str
    algorithm: str
    g_costs: Optional[Dict[Pos, int]] = None
    f_costs: Optional[Dict[Pos, int]] = None


def reconstruct_path(came_from: Dict[Pos, Pos], start: Pos, goal: Pos) -> List[Pos]:
    if start == goal:
        return [start]

    if goal not in came_from:
        return []

    cur = goal
    out = [cur]
    while cur != start:
        cur = came_from[cur]
        out.append(cur)
    out.reverse()
    return out


def bfs(start: Pos, goal: Pos, passable_neighbors: callable) -> PathResult:
    """Breadth-first search on an unweighted grid.

    `passable_neighbors(pos)` must return iterable of neighbor positions.
    """
    if start == goal:
        return PathResult(path=[start], nodes_explored=[start], reason="start==goal", algorithm="BFS")

    q = deque([start])
    came_from: Dict[Pos, Pos] = {}
    visited: Set[Pos] = {start}
    explored: List[Pos] = []

    while q:
        cur = q.popleft()
        explored.append(cur)

        if cur == goal:
            break

        for nb in passable_neighbors(cur):
            if nb in visited:
                continue
            visited.add(nb)
            came_from[nb] = cur
            q.append(nb)

    path = reconstruct_path(came_from, start, goal)
    reason = "found" if path else "no path"
    return PathResult(path=path, nodes_explored=explored, reason=reason, algorithm="BFS")


def bfs_distances(start: Pos, passable_neighbors: callable) -> tuple[Dict[Pos, int], List[Pos]]:
    """Return (distance_map, explored_order) from start over the whole reachable grid."""
    q = deque([start])
    dist: Dict[Pos, int] = {start: 0}
    explored: List[Pos] = []

    while q:
        cur = q.popleft()
        explored.append(cur)
        for nb in passable_neighbors(cur):
            if nb in dist:
                continue
            dist[nb] = dist[cur] + 1
            q.append(nb)

    return dist, explored


def manhattan(a: Pos, b: Pos) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(start: Pos, goal: Pos, passable_neighbors: callable) -> PathResult:
    """A* search with Manhattan heuristic on a 4-neighbor grid.

    Implemented from scratch; no external libraries.
    """
    if start == goal:
        return PathResult(
            path=[start],
            nodes_explored=[start],
            reason="start==goal",
            algorithm="A*",
            g_costs={start: 0},
            f_costs={start: manhattan(start, goal)},
        )

    open_heap: List[Tuple[int, int, Pos]] = []
    tie = 0

    came_from: Dict[Pos, Pos] = {}
    g: Dict[Pos, int] = {start: 0}
    f: Dict[Pos, int] = {start: manhattan(start, goal)}

    heappush(open_heap, (f[start], tie, start))
    open_set: Set[Pos] = {start}

    explored: List[Pos] = []

    while open_heap:
        _, _, cur = heappop(open_heap)
        if cur not in open_set:
            continue
        open_set.remove(cur)
        explored.append(cur)

        if cur == goal:
            break

        for nb in passable_neighbors(cur):
            tentative_g = g[cur] + 1

            if nb not in g or tentative_g < g[nb]:
                came_from[nb] = cur
                g[nb] = tentative_g
                f[nb] = tentative_g + manhattan(nb, goal)
                if nb not in open_set:
                    tie += 1
                    heappush(open_heap, (f[nb], tie, nb))
                    open_set.add(nb)

    path = reconstruct_path(came_from, start, goal)
    reason = "found" if path else "no path"
    return PathResult(path=path, nodes_explored=explored, reason=reason, algorithm="A*", g_costs=g, f_costs=f)


def greedy_best_first(start: Pos, goal: Pos, passable_neighbors: callable) -> PathResult:
    """Greedy Best-First Search using only the heuristic (Manhattan).

    Faster but less optimal/stable than A*.
    """
    if start == goal:
        return PathResult(
            path=[start],
            nodes_explored=[start],
            reason="start==goal",
            algorithm="Greedy",
        )

    open_heap: List[Tuple[int, int, Pos]] = []
    tie = 0

    came_from: Dict[Pos, Pos] = {}
    visited: Set[Pos] = {start}
    explored: List[Pos] = []

    heappush(open_heap, (manhattan(start, goal), tie, start))

    while open_heap:
        _, _, cur = heappop(open_heap)
        explored.append(cur)

        if cur == goal:
            break

        for nb in passable_neighbors(cur):
            if nb in visited:
                continue
            visited.add(nb)
            came_from[nb] = cur
            tie += 1
            heappush(open_heap, (manhattan(nb, goal), tie, nb))

    path = reconstruct_path(came_from, start, goal)
    reason = "found" if path else "no path"
    return PathResult(path=path, nodes_explored=explored, reason=reason, algorithm="Greedy")


def weighted_astar(start: Pos, goal: Pos, passable_neighbors: callable, weight: float = 2.0) -> PathResult:
    """Weighted A* (WA*) where f = g + weight * h.

    Typically faster (explores fewer nodes) but can produce suboptimal paths.
    """
    if start == goal:
        h0 = int(weight * manhattan(start, goal))
        return PathResult(
            path=[start],
            nodes_explored=[start],
            reason="start==goal",
            algorithm=f"WA*({weight:g})",
            g_costs={start: 0},
            f_costs={start: h0},
        )

    open_heap: List[Tuple[int, int, Pos]] = []
    tie = 0

    came_from: Dict[Pos, Pos] = {}
    g: Dict[Pos, int] = {start: 0}
    f: Dict[Pos, int] = {start: int(weight * manhattan(start, goal))}

    heappush(open_heap, (f[start], tie, start))
    open_set: Set[Pos] = {start}
    explored: List[Pos] = []

    while open_heap:
        _, _, cur = heappop(open_heap)
        if cur not in open_set:
            continue
        open_set.remove(cur)
        explored.append(cur)

        if cur == goal:
            break

        for nb in passable_neighbors(cur):
            tentative_g = g[cur] + 1
            if nb not in g or tentative_g < g[nb]:
                came_from[nb] = cur
                g[nb] = tentative_g
                f[nb] = int(tentative_g + weight * manhattan(nb, goal))
                if nb not in open_set:
                    tie += 1
                    heappush(open_heap, (f[nb], tie, nb))
                    open_set.add(nb)

    path = reconstruct_path(came_from, start, goal)
    reason = "found" if path else "no path"
    return PathResult(path=path, nodes_explored=explored, reason=reason, algorithm=f"WA*({weight:g})", g_costs=g, f_costs=f)


def bidirectional_bfs(start: Pos, goal: Pos, passable_neighbors: callable) -> PathResult:
    """Bidirectional BFS (unweighted grid).

    Often faster than BFS on large open maps.
    """
    if start == goal:
        return PathResult(path=[start], nodes_explored=[start], reason="start==goal", algorithm="BiBFS")

    q_start = deque([start])
    q_goal = deque([goal])
    came_from_start: Dict[Pos, Pos] = {}
    came_from_goal: Dict[Pos, Pos] = {}
    visited_start: Set[Pos] = {start}
    visited_goal: Set[Pos] = {goal}
    explored: List[Pos] = []

    meet: Optional[Pos] = None

    while q_start and q_goal and meet is None:
        # Expand from start side
        for _ in range(len(q_start)):
            cur = q_start.popleft()
            explored.append(cur)
            for nb in passable_neighbors(cur):
                if nb in visited_start:
                    continue
                visited_start.add(nb)
                came_from_start[nb] = cur
                if nb in visited_goal:
                    meet = nb
                    break
                q_start.append(nb)
            if meet is not None:
                break

        if meet is not None:
            break

        # Expand from goal side
        for _ in range(len(q_goal)):
            cur = q_goal.popleft()
            explored.append(cur)
            for nb in passable_neighbors(cur):
                if nb in visited_goal:
                    continue
                visited_goal.add(nb)
                came_from_goal[nb] = cur
                if nb in visited_start:
                    meet = nb
                    break
                q_goal.append(nb)
            if meet is not None:
                break

    if meet is None:
        return PathResult(path=[], nodes_explored=explored, reason="no path", algorithm="BiBFS")

    left = reconstruct_path(came_from_start, start, meet)
    right = reconstruct_path(came_from_goal, goal, meet)
    if not left or not right:
        return PathResult(path=[], nodes_explored=explored, reason="no path", algorithm="BiBFS")

    right_rev = list(reversed(right))  # meet -> goal
    path = left + right_rev[1:]
    return PathResult(path=path, nodes_explored=explored, reason="found", algorithm="BiBFS")
