# Lode Runner - Player

import pygame
from constants import *
from evgamelib.entity import PhysicsEntity


class Player(PhysicsEntity):
    def __init__(self):
        super().__init__(0, 0, TILE_SIZE, TILE_SIZE)
        self.facing_right = True
        self.on_ground = False
        self.on_ladder = False
        self.on_handrail = False
        self.image = None
        self.image_flip = None
        self.dig_cooldown = 0.0
        # Walk animation
        self.walk_distance = 0.0
        self.walk_frame = 0
        self.walk_frames = []
        self.walk_frames_flip = []

    def init_from_map(self, level_map):
        for row_i, row in enumerate(level_map):
            for col_i, tile in enumerate(row):
                if tile == TILE_PLAYER:
                    self.x = float(col_i * TILE_SIZE)
                    self.y = float(row_i * TILE_SIZE)
                    self.vel_x = 0.0
                    self.vel_y = 0.0
                    return
        self.x = float(TILE_SIZE)
        self.y = float(TILE_SIZE)

    def _detect_states(self, level_map):
        level_h = len(level_map)

        # on_ground: solid tile immediately below player
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

        # on_ladder: ladder tile overlaps player's center column
        self.on_ladder = False
        for r in [int(self.y / TILE_SIZE), int((self.y + self.height - 1) / TILE_SIZE)]:
            if 0 <= r < level_h and 0 <= mid_col < len(level_map[r]):
                if level_map[r][mid_col] == TILE_LADDER:
                    self.on_ladder = True
                    break

        # on_handrail: handrail tile at player's vertical center
        mid_row = int((self.y + self.height // 2) / TILE_SIZE)
        self.on_handrail = False
        if 0 <= mid_row < level_h and 0 <= mid_col < len(level_map[mid_row]):
            if level_map[mid_row][mid_col] == TILE_HANDRAIL:
                self.on_handrail = True

    def update(self, dt, keys, joy_x, joy_y, level_map):
        self._detect_states(level_map)

        if self.dig_cooldown > 0:
            self.dig_cooldown -= dt

        # Input
        move_x = 0.0
        move_y = 0.0

        if keys[pygame.K_LEFT]:
            move_x = -1.0
            self.facing_right = False
        elif keys[pygame.K_RIGHT]:
            move_x = 1.0
            self.facing_right = True

        if abs(joy_x) > DEAD_ZONE:
            move_x = joy_x
            self.facing_right = joy_x > 0

        if keys[pygame.K_UP]:
            move_y = -1.0
        elif keys[pygame.K_DOWN]:
            move_y = 1.0

        if abs(joy_y) > DEAD_ZONE:
            move_y = 1.0 if joy_y > 0 else -1.0

        # Physics based on state
        if self.on_ladder:
            self.vel_y = move_y * LADDER_SPEED
            self.vel_x = move_x * PLAYER_SPEED
        elif self.on_handrail:
            self.vel_y = 0.0
            self.vel_x = move_x * HANDRAIL_SPEED
        else:
            self.vel_y += GRAVITY * dt
            if self.vel_y > MAX_FALL_SPEED:
                self.vel_y = MAX_FALL_SPEED
            if self.on_ground:
                self.vel_y = min(self.vel_y, 0.0) if self.vel_y < 0 else 0.0
            self.vel_x = move_x * PLAYER_SPEED

        new_x = self.x + self.vel_x * dt
        new_y = self.y + self.vel_y * dt

        # Horizontal collision
        if not self._check_collision(new_x, self.y, level_map):
            self.x = new_x
        else:
            valid, invalid = self.x, new_x
            for _ in range(10):
                mid = (valid + invalid) * 0.5
                if self._check_collision(mid, self.y, level_map):
                    invalid = mid
                else:
                    valid = mid
            self.x = valid
            self.vel_x = 0.0

        # Vertical collision
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

        # Bounds
        self.x = max(0.0, min(self.x, float(GAME_WIDTH - self.width)))
        self.y = max(0.0, min(self.y, float(GAME_VIEWPORT_HEIGHT - self.height)))

        # Walk animation
        if self.on_ground and abs(self.vel_x) > 5 and self.walk_frames:
            self.walk_distance += abs(self.vel_x) * dt
            if self.walk_distance >= 16:
                self.walk_distance = 0.0
                self.walk_frame = 1 - self.walk_frame
        else:
            self.walk_distance = 0.0
            self.walk_frame = 0

    def try_dig(self, direction, level_map):
        """Intenta cavar un ladrillo adyacente. Retorna (ok, row, col)."""
        if not self.on_ground or self.dig_cooldown > 0:
            return False, -1, -1
        foot_row = int((self.y + self.height) / TILE_SIZE)
        player_col = int((self.x + self.width // 2) / TILE_SIZE)
        dig_col = player_col + direction
        level_h = len(level_map)
        if 0 <= foot_row < level_h and 0 <= dig_col < len(level_map[foot_row]):
            if level_map[foot_row][dig_col] == TILE_BRICK:
                self.dig_cooldown = DIG_COOLDOWN
                return True, foot_row, dig_col
        return False, -1, -1

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
        if self.on_ground and abs(self.vel_x) > 5 and self.walk_frames:
            frames = self.walk_frames_flip if self.facing_right else self.walk_frames
            img = frames[self.walk_frame % len(frames)]
        elif self.image:
            img = self.image_flip if self.facing_right else self.image

        if img:
            surface.blit(img, (sx, sy))
        else:
            self._draw_placeholder(surface, sx, sy)

    def _draw_placeholder(self, surface, sx, sy):
        c = COLOR_PLAYER
        # Cuerpo
        pygame.draw.rect(surface, c, (sx + 12, sy + 10, 8, 12))
        # Cabeza
        pygame.draw.circle(surface, c, (sx + 16, sy + 7), 5)
        # Piernas
        pygame.draw.line(surface, c, (sx + 14, sy + 22), (sx + 10, sy + 30), 2)
        pygame.draw.line(surface, c, (sx + 18, sy + 22), (sx + 22, sy + 30), 2)
        # Brazos
        pygame.draw.line(surface, c, (sx + 12, sy + 13), (sx + 6, sy + 18), 2)
        pygame.draw.line(surface, c, (sx + 20, sy + 13), (sx + 26, sy + 18), 2)
