# Lode Runner - Enemy

import pygame
from constants import *
from evgamelib.entity import PhysicsEntity


class Enemy(PhysicsEntity):
    def __init__(self, x, y):
        super().__init__(float(x), float(y), TILE_SIZE, TILE_SIZE)
        self.direction = 1
        self.on_ground = False
        self.on_ladder = False
        self.on_handrail = False
        self.in_hole = False
        self.image = None
        self.image_flip = None
        # Walk animation
        self.walk_distance = 0.0
        self.walk_frame = 0
        self.walk_frames = []
        self.walk_frames_flip = []

    def _detect_states(self, level_map):
        level_h = len(level_map)

        foot_y = self.y + self.height + 1
        foot_row = int(foot_y / TILE_SIZE)
        col_left = int((self.x + 2) / TILE_SIZE)
        col_right = int((self.x + self.width - 3) / TILE_SIZE)
        self.on_ground = False
        if 0 <= foot_row < level_h:
            row_w = len(level_map[foot_row])
            if (0 <= col_left < row_w and level_map[foot_row][col_left] in SOLID_TILES) or \
               (0 <= col_right < row_w and level_map[foot_row][col_right] in SOLID_TILES):
                self.on_ground = True

        mid_col = int((self.x + self.width // 2) / TILE_SIZE)
        self.on_ladder = False
        for r in [int(self.y / TILE_SIZE), int((self.y + self.height - 1) / TILE_SIZE)]:
            if 0 <= r < level_h and 0 <= mid_col < len(level_map[r]):
                if level_map[r][mid_col] == TILE_LADDER:
                    self.on_ladder = True
                    break

        mid_row = int((self.y + self.height // 2) / TILE_SIZE)
        self.on_handrail = False
        if 0 <= mid_row < level_h and 0 <= mid_col < len(level_map[mid_row]):
            if level_map[mid_row][mid_col] == TILE_HANDRAIL:
                self.on_handrail = True

    def _check_in_hole(self, holes):
        enemy_row = int(self.y / TILE_SIZE)
        enemy_col = int((self.x + self.width // 2) / TILE_SIZE)
        for hole in holes:
            if hole["row"] == enemy_row and hole["col"] == enemy_col:
                return True
        return False

    def update(self, dt, level_map, player_x, player_y, holes):
        self._detect_states(level_map)
        self.in_hole = self._check_in_hole(holes)

        if self.in_hole:
            self._update_in_hole(level_map)
        else:
            self._update_ai(player_x, player_y, level_map)

        self._apply_physics(dt, level_map)
        self._update_animation(dt)

    def _update_in_hole(self, level_map):
        """Atrapado en un hoyo: solo puede escalar si hay escalera."""
        self.vel_x = 0.0
        if self.on_ladder:
            self.vel_y = -ENEMY_SPEED
        else:
            self.vel_y = 0.0

    def _update_ai(self, player_x, player_y, level_map):
        """AI simple: perseguir al player horizontalmente, usar escaleras verticalmente."""
        level_h = len(level_map)
        mid_col = int((self.x + self.width // 2) / TILE_SIZE)
        player_col = int((player_x + TILE_SIZE // 2) / TILE_SIZE)
        player_row = int((player_y + TILE_SIZE // 2) / TILE_SIZE)
        my_row = int((self.y + self.height // 2) / TILE_SIZE)

        if self.on_ladder:
            # En escalera: moverse verticalmente hacia el player
            if player_row < my_row:
                self.vel_y = -ENEMY_SPEED
            elif player_row > my_row:
                self.vel_y = ENEMY_SPEED
            else:
                self.vel_y = 0.0
            # Salir de la escalera si ya está en la misma fila
            if player_row == my_row:
                self.vel_x = (1 if player_col > mid_col else -1) * ENEMY_SPEED
            else:
                self.vel_x = 0.0
        elif self.on_handrail:
            self.vel_y = 0.0
            self.vel_x = (1 if player_col > mid_col else -1) * ENEMY_SPEED
        else:
            # Horizontal pursuit
            if player_x + TILE_SIZE // 2 < self.x + self.width // 2:
                self.direction = -1
            elif player_x + TILE_SIZE // 2 > self.x + self.width // 2:
                self.direction = 1
            self.vel_x = self.direction * ENEMY_SPEED

            # Buscar escalera si el player está en otra fila
            if self.on_ground and abs(player_row - my_row) > 0:
                for dc in [-1, 0, 1]:
                    check_col = mid_col + dc
                    if 0 <= my_row < level_h and 0 <= check_col < len(level_map[my_row]):
                        if level_map[my_row][check_col] == TILE_LADDER:
                            # Mover hacia la escalera
                            if check_col < mid_col:
                                self.vel_x = -ENEMY_SPEED
                            elif check_col > mid_col:
                                self.vel_x = ENEMY_SPEED
                            break

    def _apply_physics(self, dt, level_map):
        if not self.on_ladder and not self.on_handrail:
            self.vel_y += GRAVITY * dt
            if self.vel_y > MAX_FALL_SPEED:
                self.vel_y = MAX_FALL_SPEED

        new_x = self.x + self.vel_x * dt
        new_y = self.y + self.vel_y * dt

        # Horizontal
        if not self._check_collision(new_x, self.y, level_map):
            self.x = new_x
        else:
            self.direction = -self.direction
            valid, invalid = self.x, new_x
            for _ in range(10):
                mid = (valid + invalid) * 0.5
                if self._check_collision(mid, self.y, level_map):
                    invalid = mid
                else:
                    valid = mid
            self.x = valid
            self.vel_x = 0.0

        # Vertical
        if not self._check_collision(self.x, new_y, level_map):
            self.y = new_y
        else:
            valid, invalid = self.y, new_y
            for _ in range(10):
                mid = (valid + invalid) * 0.5
                if self._check_collision(self.x, mid, level_map):
                    invalid = mid
                else:
                    valid = mid
            self.y = valid
            self.vel_y = 0.0

        self.x = max(0.0, min(self.x, float(GAME_WIDTH - self.width)))
        self.y = max(0.0, min(self.y, float(GAME_VIEWPORT_HEIGHT - self.height)))

    def _update_animation(self, dt):
        if abs(self.vel_x) > 5:
            self.walk_distance += abs(self.vel_x) * dt
            if self.walk_distance >= 16:
                self.walk_distance = 0.0
                self.walk_frame = 1 - self.walk_frame
            self.facing_right = self.vel_x > 0
        elif self.on_ladder or self.on_handrail:
            self.walk_distance += abs(self.vel_y) * dt
            if self.walk_distance >= 16:
                self.walk_distance = 0.0
                self.walk_frame = 1 - self.walk_frame

    def _check_collision(self, x, y, level_map):
        level_h = len(level_map)
        corners = [
            (x + 2, y + 2),
            (x + self.width - 3, y + 2),
            (x + 2, y + self.height - 3),
            (x + self.width - 3, y + self.height - 3),
        ]
        for cx, cy in corners:
            tx = int(cx / TILE_SIZE)
            ty = int(cy / TILE_SIZE)
            if ty < 0 or ty >= level_h:
                return True
            if tx < 0 or tx >= len(level_map[ty]):
                return True
            if level_map[ty][tx] in SOLID_TILES:
                return True
        return False

    def draw(self, surface, cam_x=0, cam_y=0):
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        img = None
        if self.walk_frames:
            frames = self.walk_frames_flip if self.vel_x > 0 else self.walk_frames
            img = frames[self.walk_frame % len(frames)]
        elif self.image:
            img = self.image_flip if self.vel_x > 0 else self.image

        if img:
            surface.blit(img, (sx, sy))
        else:
            self._draw_placeholder(surface, sx, sy)

    def _draw_placeholder(self, surface, sx, sy):
        c = COLOR_ENEMY
        pygame.draw.rect(surface, c, (sx + 12, sy + 10, 8, 12))
        pygame.draw.circle(surface, c, (sx + 16, sy + 7), 5)
        pygame.draw.line(surface, c, (sx + 14, sy + 22), (sx + 10, sy + 30), 2)
        pygame.draw.line(surface, c, (sx + 18, sy + 22), (sx + 22, sy + 30), 2)
        pygame.draw.line(surface, c, (sx + 12, sy + 13), (sx + 6, sy + 18), 2)
        pygame.draw.line(surface, c, (sx + 20, sy + 13), (sx + 26, sy + 18), 2)
