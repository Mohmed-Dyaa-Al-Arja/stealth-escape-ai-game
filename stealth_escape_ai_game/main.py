
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import pygame

from .config import DIFFICULTIES, Difficulty, MEDIUM
from .game import Algorithm, Game
from .rendering import RenderConfig, Renderer


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="stealth_escape_ai_game")
    p.add_argument("--map", default=None, help="Map name (e.g., map1, map2, map3, map4). If omitted, shows GUI menu.")
    p.add_argument("--debug", action="store_true", help="Start with debug mode on")
    p.add_argument("--difficulty", type=int, default=2, choices=[1, 2, 3], help="1=Easy, 2=Medium, 3=Hard")
    return p.parse_args()


def _assets_maps_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "maps"


def _list_maps() -> list[str]:
    maps_dir = _assets_maps_dir()
    names = [p.stem for p in maps_dir.glob("map*.txt")]
    names.sort()
    return names


def _draw_menu(
    screen: pygame.Surface,
    font: pygame.font.Font,
    title_font: pygame.font.Font,
    maps: list[str],
    selected_map_idx: int,
    difficulty_num: int,
    algorithm: Algorithm,
    guard_speed: int,
    debug: bool,
) -> None:
    screen.fill(pygame.Color(12, 12, 14))

    def draw(text: str, x: int, y: int, color: pygame.Color = pygame.Color(230, 230, 235)) -> None:
        surf = font.render(text, True, color)
        screen.blit(surf, (x, y))

    title = title_font.render("Escape Room AI", True, pygame.Color(240, 240, 250))
    screen.blit(title, (24, 20))

    draw(
        "Map: UP/DOWN | Difficulty: LEFT/RIGHT | Algorithm: A/D | Guard Speed: Q/E | Debug: F1",
        24,
        64,
        pygame.Color(200, 200, 210),
    )
    draw("Tip: Exit (E) stays locked until you collect all Keys (K).", 24, 88, pygame.Color(180, 180, 190))
    draw("ENTER: Start   ESC: Quit", 24, 110, pygame.Color(180, 180, 190))

    y0 = 130
    for i, name in enumerate(maps):
        is_sel = i == selected_map_idx
        prefix = ">" if is_sel else " "
        color = pygame.Color(255, 230, 80) if is_sel else pygame.Color(230, 230, 235)
        draw(f"{prefix} {name}", 40, y0 + i * 22, color)

    diff_name = DIFFICULTIES.get(difficulty_num, MEDIUM).name
    y_settings = y0 + len(maps) * 22 + 18
    draw(f"Difficulty: {difficulty_num} ({diff_name})", 24, y_settings)
    draw(f"Algorithm: {algorithm.value}", 24, y_settings + 22)
    draw(f"Guard Speed: {guard_speed}x", 24, y_settings + 44)
    draw(f"Debug: {'ON' if debug else 'OFF'}", 24, y_settings + 66)


def _menu_select(
    screen: pygame.Surface,
    font: pygame.font.Font,
    title_font: pygame.font.Font,
    maps: list[str],
    initial_map: Optional[str],
    initial_difficulty: int,
) -> Optional[tuple[str, int, Algorithm, bool, int]]:

    if not maps:
        return None

    selected_map_idx = 0
    if initial_map in maps:
        selected_map_idx = maps.index(initial_map)

    difficulty_num = initial_difficulty
    algorithms = [Algorithm.BFS, Algorithm.ASTAR, Algorithm.BIBFS, Algorithm.GREEDY, Algorithm.WEIGHTED_ASTAR]
    alg_idx = 1
    debug = False
    guard_speed = 1

    clock = pygame.time.Clock()
    while True:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None

            if event.type != pygame.KEYDOWN:
                continue

            if event.key == pygame.K_ESCAPE:
                return None

            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return (maps[selected_map_idx], difficulty_num, algorithms[alg_idx], debug, guard_speed)

            if event.key == pygame.K_UP:
                selected_map_idx = (selected_map_idx - 1) % len(maps)
            elif event.key == pygame.K_DOWN:
                selected_map_idx = (selected_map_idx + 1) % len(maps)
            elif event.key == pygame.K_LEFT:
                difficulty_num = max(1, difficulty_num - 1)
            elif event.key == pygame.K_RIGHT:
                difficulty_num = min(3, difficulty_num + 1)
            elif event.key == pygame.K_a:
                alg_idx = (alg_idx - 1) % len(algorithms)
            elif event.key == pygame.K_d:
                alg_idx = (alg_idx + 1) % len(algorithms)
            elif event.key == pygame.K_q:
                guard_speed = max(1, guard_speed - 1)
            elif event.key == pygame.K_e:
                guard_speed = min(3, guard_speed + 1)
            elif event.key == pygame.K_F1:
                debug = not debug

        _draw_menu(screen, font, title_font, maps, selected_map_idx, difficulty_num, algorithms[alg_idx], guard_speed, debug)
        pygame.display.flip()


def main() -> int:
    args = parse_args()

    pygame.init()
    pygame.display.set_caption("Escape Room AI (Puzzles + Chase)")

    rcfg = RenderConfig(tile_size=32, hud_height=72)
    screen = pygame.display.set_mode((30 * rcfg.tile_size, 20 * rcfg.tile_size + rcfg.hud_height))

    font = pygame.font.SysFont("segoeui", 18)
    title_font = pygame.font.SysFont("segoeui", 26, bold=True)

    clock = pygame.time.Clock()

    selected_map: Optional[str] = args.map
    selected_diff = args.difficulty
    selected_alg: Algorithm = Algorithm.ASTAR
    selected_debug: bool = bool(args.debug)
    selected_guard_speed: int = 1

    while True:
        if selected_map is None:
            maps = _list_maps()
            chosen = _menu_select(screen, font, title_font, maps, "map1", selected_diff)
            if chosen is None:
                pygame.quit()
                return 0

            selected_map, selected_diff, selected_alg, selected_debug, selected_guard_speed = chosen

        difficulty: Difficulty = DIFFICULTIES.get(int(selected_diff), MEDIUM)

        game = Game(
            map_name=str(selected_map),
            difficulty=difficulty,
            algorithm=selected_alg,
            debug=selected_debug,
            guard_moves_per_turn=selected_guard_speed,
        )

        # سرعة العدو حسب الصعوبة
        guard_move_delay = 250 - (difficulty.guard_speed * 50)

        #  سرعة اللاعب (أسرع)
        player_move_delay = 90

        last_guard_move_time = pygame.time.get_ticks()
        last_player_move_time = 0

        w = game.grid.width * rcfg.tile_size
        h = game.grid.height * rcfg.tile_size + rcfg.hud_height
        screen = pygame.display.set_mode((w, h))

        renderer = Renderer(screen=screen, font=font, cfg=rcfg)

        running = True
        while running:
            clock.tick(60)

            current_time = pygame.time.get_ticks()

            if current_time - last_guard_move_time >= guard_move_delay:
                if not game.state.won and not game.state.lost:
                    game._guards_turn()  
                last_guard_move_time = current_time

            keys = pygame.key.get_pressed()

            if current_time - last_player_move_time >= player_move_delay:
                dx, dy = 0, 0

                if keys[pygame.K_w]:
                    dy = -1
                elif keys[pygame.K_s]:
                    dy = 1
                elif keys[pygame.K_a]:
                    dx = -1
                elif keys[pygame.K_d]:
                    dx = 1

                if (dx != 0 or dy != 0) and not game.state.won and not game.state.lost:
                    game.try_move_player(dx, dy)
                    last_player_move_time = current_time

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            renderer.draw(
                game.grid,
                game.player,
                game.active_guards,
                overlays=game.overlays(),
            )

            pygame.display.flip()

        selected_map = None