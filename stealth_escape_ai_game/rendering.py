from __future__ import annotations
from .entities import GuardState
from dataclasses import dataclass
from typing import Dict, List, Tuple

import pygame

from .entities import Facing, Guard, Player, GuardState
from .grid import Grid

Pos = Tuple[int, int]


@dataclass(frozen=True)
class RenderConfig:
    tile_size: int = 32
    hud_height: int = 72



class Renderer:
    def __init__(self, screen, font, cfg):
        self.screen = screen
        self.font = font
        self.cfg = cfg

        self.floor_color = pygame.Color(30, 30, 35)
        self.wall_color = pygame.Color(60, 60, 70)
        self.exit_color = pygame.Color(40, 200, 120)

        self.player_color = pygame.Color(80, 200, 255)
        self.guard_color = pygame.Color(255, 80, 80)

        self.shadow_color = pygame.Color(0, 0, 0, 60)

        # 🎥 Camera
        self.camera_x = 0
        self.camera_y = 0
        self.shake_time = 0

    # 🎥 الكاميرا
    def _update_camera(self, player, grid):
        ts = self.cfg.tile_size
        px, py = getattr(player, "render_pos", player.pos)

        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height() - self.cfg.hud_height

        map_w = grid.width * ts
        map_h = grid.height * ts

        target_x = px * ts - screen_w // 2
        target_y = px * ts - screen_h // 2

        self.camera_x += (target_x - self.camera_x) * 0.1
        self.camera_y += (target_y - self.camera_y) * 0.1

    #  IMPORTANT: منع الكاميرا تطلع برا الماب
        self.camera_x = max(0, min(self.camera_x, max(0, map_w - screen_w)))
        self.camera_y = max(0, min(self.camera_y, max(0, map_h - screen_h)))
    # 📦 rect بالكاميرا
    def cell_rect(self, p):
        ts = self.cfg.tile_size
        return pygame.Rect(
            int(p[0] * ts - self.camera_x),
            int(p[1] * ts - self.camera_y),
            ts,
            ts
        )

    # 🎮 draw كامل
    def draw(self, grid, player, guards, overlays):
        self.screen.fill((12, 12, 14))

        self._update_camera(player, grid)

        self._draw_grid(grid)

        self._draw_exit(grid, overlays)
        self._draw_keys(grid)

        self._draw_player(player)

        for g in guards:
            self._draw_guard_vision(g, grid)
            self._draw_guard(g)

        pygame.display.flip()
    
    def _draw_grid(self, grid: Grid):
        ts = self.cfg.tile_size

        for y in range(grid.height):
            for x in range(grid.width):
                rect = self.cell_rect((x, y))

                if grid.is_wall((x, y)):
                    pygame.draw.rect(self.screen, self.wall_color, rect, border_radius=4)
                else:
                    pygame.draw.rect(self.screen, self.floor_color, rect)

                # grid outline خفيف
                    pygame.draw.rect(self.screen, (40, 40, 50), rect, 1)
    def _draw_player(self, player: Player):
        p = getattr(player, "render_pos", player.pos)
        r = self.cell_rect((int(p[0]), int(p[1])))

    # shadow
        shadow = r.move(3, 4)
        pygame.draw.rect(self.screen, self.shadow_color, shadow.inflate(-8, -8), border_radius=8)

    # الجسم
        body = r.inflate(-10, -10)
        pygame.draw.rect(self.screen, self.player_color, body, border_radius=8)

    # الاتجاه
        cx, cy = r.center
        dx, dy = 0, 0

        if hasattr(player, "facing"):
            if player.facing == Facing.N:
                dy = -8
            elif player.facing == Facing.S:
                dy = 8
            elif player.facing == Facing.E:
                dx = 8
            elif player.facing == Facing.W:
                dx = -8

        pygame.draw.line(self.screen, (20, 20, 20), (cx, cy), (cx + dx, cy + dy), 3)
    
    def _draw_guard(self, guard: Guard):
        p = getattr(guard, "render_pos", guard.pos)
        r = self.cell_rect((int(p[0]), int(p[1])))

    # 🟫 shadow
        shadow = r.move(3, 4)
        pygame.draw.rect(self.screen, self.shadow_color, shadow.inflate(-6, -6), border_radius=8)

    # 🎨 لون العدو
        color = self.guard_color

        if guard.state == GuardState.CHASE:
            color = pygame.Color(255, 60, 60)
        elif guard.memory_timer > 0:
            color = pygame.Color(255, 200, 80)

    # 🟥 جسم العدو
        pygame.draw.rect(self.screen, color, r.inflate(-8, -8), border_radius=8)

    # 🧭 الاتجاه
        cx, cy = r.center
        dx, dy = 0, 0

        if guard.facing == Facing.N:
            dy = -10
        elif guard.facing == Facing.S:
            dy = 10
        elif guard.facing == Facing.E:
            dx = 10
        elif guard.facing == Facing.W:
            dx = -10

        pygame.draw.line(self.screen, (0, 0, 0), (cx, cy), (cx + dx, cy + dy), 3)

    # ❗❓ العلامات (بعد الرسم)
        if guard.state == GuardState.CHASE:
            text = self.font.render("!", True, (255, 50, 50))
            self.screen.blit(text, (r.centerx - 5, r.y - 18))

        elif guard.memory_timer > 0:
            text = self.font.render("?", True, (255, 255, 0))
            self.screen.blit(text, (r.centerx - 5, r.y - 18))


    def _draw_keys(self, grid):
        for p in grid.keys:
            r = self.cell_rect(p)
            pygame.draw.circle(self.screen, (255, 220, 70), r.center, 6)
    def _draw_exit(self, grid, overlays):
        r = self.cell_rect(grid.exit_pos)

        locked = overlays.get("exit_locked", True)

        color = pygame.Color(180, 60, 60) if locked else self.exit_color

        pygame.draw.rect(self.screen, color, r, border_radius=6)  
    def _can_see_player(self, g):
        px, py = self.player.pos
        gx, gy = g.pos

        return abs(px - gx) <= 5 and abs(py - gy) <= 5
    
    def _draw_guard_vision(self, guard, grid):
     vision = getattr(guard, "vision_range", 5)

     for dx in range(-vision, vision + 1):
          for dy in range(-vision, vision + 1):

               x = guard.pos[0] + dx
               y = guard.pos[1] + dy

               if not grid.in_bounds((x, y)):
                    continue

               # 👇 شرط الاتجاه (Cone بسيط)
               if guard.facing == Facing.N and dy >= 0:
                    continue
               if guard.facing == Facing.S and dy <= 0:
                    continue
               if guard.facing == Facing.E and dx <= 0:
                    continue
               if guard.facing == Facing.W and dx >= 0:
                    continue

               # 👇 يمنع الرؤية خلف الحيطان
               if not self._has_line_of_sight(guard.pos, (x, y), grid):
                    continue

               r = self.cell_rect((x, y))

               # 🎨 ألوان الحالة
               if guard.state == GuardState.CHASE:
                    color = (255, 0, 0, 60)   # 🔴
               elif guard.memory_timer > 0:
                    color = (255, 255, 0, 50) # 🟡
               else:
                    color = (50, 100, 255, 40) # 🔵

               s = pygame.Surface(r.size, pygame.SRCALPHA)
               s.fill(color)
               self.screen.blit(s, r.topleft)

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

