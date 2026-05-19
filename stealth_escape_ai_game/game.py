from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .ai.pathfinding import (
    PathResult,
    astar,
    bfs,
    bfs_distances,
    bidirectional_bfs,
    greedy_best_first,
    manhattan,
    weighted_astar,
)
from .ai.vision import has_line_of_sight, visible_cells
from .config import DIFFICULTIES, Difficulty, MEDIUM
from .entities import Facing, Guard, GuardState, Player
from .grid import Grid, load_map_meta, load_text_map

Pos = Tuple[int, int]


class Algorithm(str, Enum):
    BFS = "BFS"
    ASTAR = "A*"
    GREEDY = "Greedy"
    WEIGHTED_ASTAR = "WA*"
    BIBFS = "BiBFS"


@dataclass
class GameState:
    won: bool = False
    lost: bool = False


class Game:
    def __init__(
        self,
        map_name: str = "map1",
        difficulty: Difficulty = MEDIUM,
        algorithm: Algorithm = Algorithm.ASTAR,
        debug: bool = False,
        guard_moves_per_turn: int = 1,
    ):
        self.map_name = map_name
        self.difficulty = difficulty
        self.algorithm = algorithm
        self.debug = debug
        self.guard_moves_per_turn = max(1, int(guard_moves_per_turn))

        self.state = GameState()
        self.message: str = ""

        self.turn_index: int = 0

        self._player_last_dir: tuple[int, int] = (0, 0)
        self.keys_collected: int = 0
        self.keys_total: int = 0

        self._load_level()

    def _assets_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent / "assets" / "maps"

    def _load_level(self) -> None:
        maps = self._assets_dir()
        map_path = maps / f"{self.map_name}.txt"
        meta_path = maps / f"{self.map_name}_meta.json"

        map_data = load_text_map(map_path)
        self.grid = Grid(map_data)
        self.player = Player(pos=self.grid.player_spawn)
        self.player.render_pos = tuple(map(float, self.player.pos))

        self.keys_collected = 0
        self.keys_total = self.grid.total_keys

        meta = load_map_meta(meta_path)
        guards_meta = meta.get("guards", [])

        self.guards: List[Guard] = []

        for i, spawn in enumerate(self.grid.guard_spawns):
            patrol = guards_meta[i].get("patrol_path", [list(spawn)]) if i < len(guards_meta) else [list(spawn)]
            patrol_path = [(int(x), int(y)) for x, y in patrol]
            g = Guard(id=i, pos=spawn, patrol_path=patrol_path)

            # Per-guard vision range (optional in meta; otherwise deterministic variation).
            meta_vision = None
            if i < len(guards_meta):
                meta_vision = guards_meta[i].get("vision_range")
            if meta_vision is not None:
                g.vision_range = max(3, int(meta_vision))
            else:
                base = int(self.difficulty.vision_range)
                g.vision_range = max(3, base + ((i % 3) - 1))

            g.render_pos = tuple(map(float, g.pos))

            self.guards.append(g)

        self.active_guards = self.guards[: max(1, min(self.difficulty.active_guard_count, len(self.guards)))]

        self.state = GameState(won=False, lost=False)
        if self.keys_total > 0:
            self.message = "Collect all keys, then escape."
        else:
            self.message = "Reach the exit without being caught."

        self._player_last_dir = (0, 0)
        self.turn_index = 0

    def restart(self) -> None:
        self._load_level()

    def set_difficulty(self, num: int) -> None:
        if num in DIFFICULTIES:
            self.difficulty = DIFFICULTIES[num]
            self.restart()

    def toggle_debug(self) -> None:
        self.debug = not self.debug
        self.message = "Debug mode ON" if self.debug else "Debug mode OFF"

    def toggle_algorithm(self) -> None:
        self.algorithm = Algorithm.BFS if self.algorithm == Algorithm.ASTAR else Algorithm.ASTAR
        self.message = f"Switched algorithm to {self.algorithm.value}"

    def try_move_player(self, dx: int, dy: int) -> None:
        if self.state.won or self.state.lost:
            return

        new_pos = (self.player.pos[0] + dx, self.player.pos[1] + dy)
        if not self.grid.passable(new_pos):
            return

        old = self.player.pos
        self.player.apply_move(new_pos)
        self._player_last_dir = (new_pos[0] - old[0], new_pos[1] - old[1])

        if self.grid.collect_key(self.player.pos):
            self.keys_collected += 1
            self.message = f"Key collected! ({self.keys_collected}/{self.keys_total})"

        if self.player.pos == self.grid.exit_pos:
            if self.keys_collected >= self.keys_total:
                self.state.won = True
                self.message = "You escaped!"
                return
            self.message = f"Exit locked: collect keys ({self.keys_collected}/{self.keys_total})"

        # NOTE: Guards move on the main loop timer (real-time). Avoid moving them here
        # to prevent “speed spikes” and double-updates.

    def _guards_turn(self) -> None:
        if self.state.won or self.state.lost:
            return

        for g in self.active_guards:
            for _ in range(self.guard_moves_per_turn):
                self.turn_index += 1
                self._update_guard(g)

                if g.pos == self.player.pos:
                    self.state.lost = True
                    self.message = "Caught by a guard!"
                    return

        # Win condition is handled on player movement; keep guard turn focused.

    def _find_path(self, start: Pos, goal: Pos) -> PathResult:
        neighbors = self.grid.neighbors4

        if self.algorithm == Algorithm.BFS:
            return bfs(start, goal, neighbors)

        if self.algorithm == Algorithm.BIBFS:
            return bidirectional_bfs(start, goal, neighbors)

        if self.algorithm == Algorithm.GREEDY:
            return greedy_best_first(start, goal, neighbors)

        if self.algorithm == Algorithm.WEIGHTED_ASTAR:
            return weighted_astar(start, goal, neighbors, weight=2.0)

        return astar(start, goal, neighbors)

    def _memory_turns(self) -> int:
        # More than 1 so it feels like a real “search” phase.
        return max(1, int(self.difficulty.investigation_turns) * 6)

    def _update_guard(self, g: Guard) -> None:
        """One guard AI step (movement + state transitions)."""

        sees_player = self._update_guard_vision(g)

        # --- State transitions ---
        if sees_player:
            g.last_seen_player = self.player.pos
            g.last_seen_dir = self._player_last_dir
            g.memory_timer = self._memory_turns()

            if g.state in (GuardState.PATROL, GuardState.MEMORY):
                if self.difficulty.detection_pause_turns > 0:
                    g.state = GuardState.DETECTION
                    g.state_timer = int(self.difficulty.detection_pause_turns)
                else:
                    g.state = GuardState.CHASE
            elif g.state == GuardState.DETECTION:
                # Keep the pause short, but don't drop detection if player is still visible.
                g.state_timer = max(g.state_timer, 1)

        else:
            if g.state == GuardState.DETECTION:
                # Lost sight before committing to a chase.
                g.state = GuardState.PATROL
                g.state_timer = 0

            elif g.state == GuardState.CHASE:
                # Transition into MEMORY/search.
                if g.last_seen_player is not None:
                    g.state = GuardState.MEMORY
                    g.memory_timer = max(g.memory_timer, self._memory_turns())
                    g.investigation_timer = g.memory_timer
                    g.investigation_origin = g.last_seen_player
                    g.investigation_goal = None
                else:
                    g.state = GuardState.PATROL

            elif g.state == GuardState.MEMORY:
                g.memory_timer -= 1
                g.investigation_timer = max(0, g.memory_timer)
                if g.memory_timer <= 0:
                    g.state = GuardState.PATROL
                    g.last_seen_player = None
                    g.last_seen_dir = None
                    g.investigation_origin = None
                    g.investigation_goal = None
                    g.roam_goal = None

        # --- Behavior ---
        if g.state == GuardState.PATROL:
            self._guard_patrol_step(g)
            return

        if g.state == GuardState.DETECTION:
            self._guard_detection_step(g)
            return

        if g.state == GuardState.CHASE:
            self._guard_chase_step(g, sees_player=sees_player)
            return

        if g.state == GuardState.MEMORY:
            self._guard_memory_step(g)
            return


    def _update_guard_vision(self, g: Guard) -> bool:
        g.last_visible = visible_cells(
            origin=g.pos,
            facing=g.facing.value,
            vision_range=getattr(g, "vision_range", self.difficulty.vision_range),
            in_bounds=self.grid.in_bounds,
            is_wall=self.grid.is_wall,
        )

        return self.player.pos in g.last_visible


    def _apply_detection_transition(self, g: Guard, sees_player: bool) -> None:
        if not sees_player:
            return

        g.last_seen_player = self.player.pos
        g.last_seen_dir = self._player_last_dir

        if g.state not in (GuardState.CHASE, GuardState.DETECTION):
            g.state = GuardState.DETECTION
            g.state_timer = self.difficulty.detection_pause_turns

            if self.debug:
                print(f"[Guard {g.id}] DETECTION: player seen at {self.player.pos}")

    def _guard_patrol_step(self, g: Guard) -> None:
        """Patrol behavior.

        - If patrol_path defines waypoints (len>=2): walk between them using pathfinding.
        - Otherwise: use smart roam goals to cover the full map.
        """
        if g.patrol_path and len(g.patrol_path) >= 2:
            if self._guard_follow_patrol_waypoints(g):
                return

        self._guard_roam_step(g)

    def _guard_follow_patrol_waypoints(self, g: Guard) -> bool:
        """Return True if we took a patrol step."""
        waypoint = g.step_patrol()
        if waypoint is None or waypoint == g.pos:
            return False

        result = bfs(g.pos, waypoint, self.grid.neighbors4)
        if self.debug:
            g.last_path = result.path
            g.last_explored = result.nodes_explored
        else:
            g.last_path = []
            g.last_explored = []

        if len(result.path) >= 2:
            g.apply_move(result.path[1])
            return True

        return False


    def _guard_roam_step(self, g: Guard) -> None:
        if g.roam_goal is None or g.pos == g.roam_goal:
            g.roam_goal = self._pick_roam_goal(g)

        goal = g.roam_goal
        if goal is None:
            return

        result = bfs(g.pos, goal, self.grid.neighbors4)

        if len(result.path) >= 2:
            g.apply_move(result.path[1])
        else:
            g.roam_goal = None

        if self.debug:
            g.last_path = result.path
            g.last_explored = result.nodes_explored
        else:
            g.last_path = []
            g.last_explored = []


    def _pick_roam_goal(self, g: Guard) -> Optional[Pos]:
        dist, _ = bfs_distances(g.pos, self.grid.neighbors4)

        if not dist:
            return None

        items = [(d, p) for p, d in dist.items() if p != self.grid.exit_pos]
        if not items:
            items = [(d, p) for p, d in dist.items()]

        items.sort(reverse=True)
        top_n = min(50, len(items))

        base_idx = (g.id * 31 + self.turn_index) % top_n
        candidates = [items[(base_idx + j) % top_n][1] for j in range(min(10, top_n))]

        recent = set(g.roam_recent_goals[-5:])
        goal = next((p for p in candidates if p not in recent), candidates[0])

        if goal == g.roam_last_goal and top_n > 1:
            goal = candidates[1] if len(candidates) > 1 else goal

        g.roam_last_goal = goal
        g.roam_recent_goals.append(goal)

        if len(g.roam_recent_goals) > 30:
            g.roam_recent_goals = g.roam_recent_goals[-20:]

        return goal


    def _guard_detection_step(self, g: Guard) -> None:
        """Short pause when the guard first spots the player."""
        g.state_timer -= 1
        if g.state_timer <= 0:
            g.state = GuardState.CHASE
            g.memory_timer = max(g.memory_timer, self._memory_turns())
            if self.debug:
                print(f"[Guard {g.id}] CHASE: starting chase")

        # No movement in DETECTION.
        g.last_path = []
        g.last_explored = []


    def _guard_chase_step(self, g: Guard, sees_player: bool) -> None:
        """CHASE: pursue the player.

        Important: no speed spike here — this method moves at most 1 tile.
        """
        if sees_player:
            g.last_seen_player = self.player.pos
            g.last_seen_dir = self._player_last_dir
            g.memory_timer = max(g.memory_timer, self._memory_turns())

        if g.last_seen_player is None:
            g.state = GuardState.PATROL
            g.roam_goal = None
            return

        target: Pos = self.player.pos if sees_player else g.last_seen_player

        intercept_target = self._compute_intercept_target(g, visible=sees_player)
        if intercept_target is not None:
            target = intercept_target

        result = self._find_path(g.pos, target)
        g.last_path = result.path
        g.last_explored = result.nodes_explored

        if self.debug:
            self._print_path_debug(g, target, result)

        if len(result.path) >= 2:
            g.apply_move(result.path[1])
            return

        # Fallback: take any step that gets closer (never idle unless blocked).
        candidates = self.grid.neighbors4(g.pos)
        if not candidates:
            return
        candidates.sort(key=lambda p: manhattan(p, target))
        g.apply_move(candidates[0])

    def _guard_memory_step(self, g: Guard) -> None:
        """MEMORY: move/search toward the last seen position, then return to patrol."""
        if g.last_seen_player is None:
            g.state = GuardState.PATROL
            g.roam_goal = None
            return

        # Phase A: go to last seen.
        target: Pos = g.last_seen_player
        if g.pos == g.last_seen_player:
            # Phase B: search around origin while timer lasts.
            inv_target = self._compute_investigation_target(g)
            if inv_target is not None:
                target = inv_target

        result = self._find_path(g.pos, target)
        g.last_path = result.path
        g.last_explored = result.nodes_explored

        if self.debug:
            self._print_path_debug(g, target, result)

        if len(result.path) >= 2:
            g.apply_move(result.path[1])
            return

        # Fallback: keep moving (smart roam) rather than jittering randomly.
        self._guard_roam_step(g)
    def _predict_player_position(self, start: Pos, direction: tuple[int, int], max_steps: int) -> Pos:
        dx, dy = direction
        if dx == 0 and dy == 0:
            return start

        cur = start
        for _ in range(max_steps):
            nxt = (cur[0] + dx, cur[1] + dy)
            if not self.grid.passable(nxt):
                break
            cur = nxt
        return cur


    def _compute_intercept_target(self, g: Guard, visible: bool) -> Optional[Pos]:
        """Pick an intercept target ahead of the player's likely path."""
        horizon = self.difficulty.prediction_horizon
        if horizon <= 0:
            return None

        # تقدير مكان اللاعب
        if visible:
            est_player = self.player.pos
        elif g.last_seen_player is not None:
            est_player = g.last_seen_player
            est_dir = g.last_seen_dir or (0, 0)
            est_player = self._predict_player_position(est_player, est_dir, max_steps=3)
        else:
            return None

        objectives = self._candidate_player_objectives(est_player)
        if not objectives:
            return None

        dist_map, _ = bfs_distances(g.pos, self.grid.neighbors4)

        best: Optional[tuple[int, int, Pos, Pos]] = None  # (advantage, -guard_steps, intercept, objective)

        # 🔹 Option A: اعتراض مباشر في اتجاه الحركة الحالي
        if visible and g.last_seen_dir is not None:
            dpath = [est_player]
            cur = est_player
            dx, dy = g.last_seen_dir

            for _ in range(max(1, min(5, horizon))):
                nxt = (cur[0] + dx, cur[1] + dy)
                if not self.grid.passable(nxt):
                    break
                dpath.append(nxt)
                cur = nxt

            for i in range(1, len(dpath)):
                p = dpath[i]
                guard_steps = dist_map.get(p)
                if guard_steps is None:
                    continue

                advantage = i - guard_steps
                if advantage < self.difficulty.intercept_min_advantage:
                    continue

                score = (advantage, -guard_steps)
                if best is None or score > (best[0], best[1]):
                    best = (advantage, -guard_steps, p, p)

        # 🔹 Option B: اعتراض في طريق الأهداف (Keys أو Exit)
        for objective in objectives:
            player_plan = bfs(est_player, objective, self.grid.neighbors4)
            if not player_plan.path:
                continue

            max_i = min(horizon, len(player_plan.path) - 1)

            for i in range(1, max_i + 1):
                p = player_plan.path[i]
                guard_steps = dist_map.get(p)
                if guard_steps is None:
                    continue

                advantage = i - guard_steps
                if advantage < self.difficulty.intercept_min_advantage:
                    continue

                score = (advantage, -guard_steps)
                if best is None or score > (best[0], best[1]):
                    best = (advantage, -guard_steps, p, objective)

        if best is None:
            return None

        adv, _, chosen, objective = best

        if self.debug:
            print(
                f"[Guard {g.id}] INTERCEPT: est_player={est_player} "
                f"objective={objective} chosen={chosen} advantage={adv}"
            )

        return chosen


    def _candidate_player_objectives(self, est_player: Pos) -> List[Pos]:
        remaining_keys = list(self.grid.keys)

        if not remaining_keys:
            return [self.grid.exit_pos]

        dist, _ = bfs_distances(est_player, self.grid.neighbors4)

        keyed: List[tuple[int, Pos]] = []
        for k in remaining_keys:
            d = dist.get(k)
            if d is not None:
                keyed.append((d, k))

        if not keyed:
            return [self.grid.exit_pos]

        keyed.sort()
        return [p for _, p in keyed[:2]]


    def _compute_investigation_target(self, g: Guard) -> Optional[Pos]:
        if g.investigation_timer <= 0:
            return None

        origin = g.investigation_origin or g.last_seen_player
        if origin is None:
            return None

        if g.investigation_goal is not None and g.pos != g.investigation_goal:
            return g.investigation_goal

        dist_from_origin, _ = bfs_distances(origin, self.grid.neighbors4)
        if not dist_from_origin:
            return None

        radius = min(8, 3 + self.difficulty.vision_range // 2)
        candidates = [p for p, d in dist_from_origin.items() if 2 <= d <= radius]

        if not candidates:
            return None

        dist_from_guard, _ = bfs_distances(g.pos, self.grid.neighbors4)
        recent = set(g.roam_recent_goals[-8:])

        scored: List[tuple[int, int, Pos]] = []
        for p in candidates:
            gd = dist_from_guard.get(p)
            if gd is None:
                continue
            scored.append((dist_from_origin.get(p, 0), -gd, p))

        scored.sort(reverse=True)

        chosen = next((p for _, __, p in scored if p not in recent), scored[0][2])
        g.investigation_goal = chosen

        if self.debug:
            print(f"[Guard {g.id}] INVESTIGATE: origin={origin} goal={chosen}")

        return chosen
    def _print_path_debug(self, g: Guard, target: Pos, result: PathResult) -> None:
        if not result.path:
            print(
                f"[Guard {g.id}] {result.algorithm}: no path from {g.pos} to {target}. "
                f"explored={len(result.nodes_explored)}"
            )
            return

        next_step = result.path[1] if len(result.path) >= 2 else result.path[0]

        print(
            f"[Guard {g.id}] {result.algorithm}: from={g.pos} to={target} "
            f"path_len={len(result.path)-1} explored={len(result.nodes_explored)} next={next_step}"
        )

        if result.g_costs is not None and result.f_costs is not None:
            g0 = result.g_costs.get(g.pos, 0)
            h0 = manhattan(g.pos, target)
            f0 = g0 + h0

            gn = result.g_costs.get(next_step, None)
            hn = manhattan(next_step, target)
            fn = (gn + hn) if gn is not None else None

            print(f"[Guard {g.id}] costs: start g={g0} h={h0} f~={f0}")
            if fn is not None:
                print(f"[Guard {g.id}] costs: next  g={gn} h={hn} f~={fn}")


    def overlays(self) -> Dict:
        stats = " | ".join(
            f"G{g.id}:{g.state.value} exp={len(g.last_explored)} path={max(0, len(g.last_path) - 1)}"
            for g in self.active_guards
        )

        msg = self.message
        if self.debug and stats:
            msg = f"{msg}   {stats}" if msg else stats

        keys = f"{self.keys_collected}/{self.keys_total}" if self.keys_total else "0/0"
        exit_locked = self.keys_collected < self.keys_total

        return {
            "algorithm": self.algorithm.value,
            "difficulty": self.difficulty.name,
            "debug": self.debug,
            "message": msg,
            "keys": keys,
            "exit_locked": exit_locked,
        }
    def _has_line_of_sight(self, start, end, grid):
        x1, y1 = start
        x2, y2 = end

        dx = x2 - x1
        dy = y2 - y1

        steps = max(abs(dx), abs(dy))

        if steps == 0:
            return True

        for i in range(1, steps + 1):
            t = i / steps
            x = int(round(x1 + dx * t))
            y = int(round(y1 + dy * t))

            if grid.is_wall((x, y)):
                return False

        return True
    def _can_see_player(self, g):
     px, py = self.player.pos
     gx, gy = g.pos

     dx = px - gx
     dy = py - gy

     vision = getattr(g, "vision_range", 5)

     if abs(dx) > vision or abs(dy) > vision:
          return False

     # 👇 اتجاه
     if g.facing == Facing.N and dy >= 0:
          return False
     if g.facing == Facing.S and dy <= 0:
          return False
     if g.facing == Facing.E and dx <= 0:
          return False
     if g.facing == Facing.W and dx >= 0:
          return False

     # 👇 يمنع الرؤية عبر الحيطان
     return self._has_line_of_sight(g.pos, self.player.pos, self.grid)
