# Lode Runner - Player

from math import ceil, floor

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
        self.fall_image = None
        self.fall_image_flip = None
        self.dig_cooldown = 0.0
        self._stationary_hole_ignores = set()
        # Walk animation
        self.walk_distance = 0.0
        self.walk_frame = 0
        self.walk_frames = []
        self.walk_frames_flip = []

    def reset_hole_ignores(self):
        self._stationary_hole_ignores.clear()

    def init_from_map(self, level_map):
        self.reset_hole_ignores()
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

    def _detect_states(self, level_map, holes=None):
        level_h = len(level_map)
        holes = holes or []

        # on_ground: solid tile immediately below player
        foot_y = self.y + self.height + 1
        foot_row = int(foot_y / TILE_SIZE)
        center_col = int((self.x + self.width // 2) / TILE_SIZE)
        col_left = int((self.x + 2) / TILE_SIZE)
        col_right = int((self.x + self.width - 3) / TILE_SIZE)
        self.on_ground = False
        if 0 <= foot_row < level_h:
            row_w = len(level_map[foot_row])
            if (0 <= col_left < row_w and level_map[foot_row][col_left] in SOLID_TILES) or \
               (0 <= col_right < row_w and level_map[foot_row][col_right] in SOLID_TILES):
                self.on_ground = True

        for hole in holes:
            if hole["row"] != foot_row:
                continue
            hole_key = (hole["row"], hole["col"])
            if hole_key in self._stationary_hole_ignores and hole["col"] != center_col:
                continue
            foot_overlap = self._hole_visible_foot_overlap(hole)
            if hole.get("solid_for_player") and foot_overlap >= PLAYER_HOLE_FALL_OVERLAP:
                self.on_ground = True
                continue
            if foot_overlap >= PLAYER_HOLE_FALL_OVERLAP:
                self.on_ground = False
                break

        mid_col = center_col

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

    def update(self, dt, keys, joy_x, joy_y, level_map, holes=None):
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

        if abs(move_x) > 0.0:
            self._stationary_hole_ignores.clear()

        self._detect_states(level_map, holes)

        if self.dig_cooldown > 0:
            self.dig_cooldown -= dt

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

        crossed_hole = self._crossed_hole(self.x, new_x, holes)

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

        if crossed_hole and not self.on_ladder and not self.on_handrail:
            self.x = float(crossed_hole["col"] * TILE_SIZE)
            self.on_ground = False
            if self.vel_y <= 0:
                self.vel_y = GRAVITY * dt
            new_y = self.y + self.vel_y * dt

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
                self.walk_frame = (self.walk_frame + 1) % len(self.walk_frames)
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
            has_ladder_above = (
                foot_row > 0 and
                dig_col < len(level_map[foot_row - 1]) and
                level_map[foot_row - 1][dig_col] == TILE_LADDER
            )
            if level_map[foot_row][dig_col] == TILE_BRICK and not has_ladder_above:
                self.dig_cooldown = DIG_COOLDOWN
                self._stationary_hole_ignores.add((foot_row, dig_col))
                return True, foot_row, dig_col
        return False, -1, -1

    def _crossed_hole(self, old_x, new_x, holes):
        if not holes:
            return False
        if abs(new_x - old_x) < 0.001:
            return None
        foot_row = int((self.y + self.height + 1) / TILE_SIZE)
        center_col = int((self.x + self.width // 2) / TILE_SIZE)
        for hole in holes:
            if hole["row"] != foot_row:
                continue
            hole_key = (hole["row"], hole["col"])
            if hole_key in self._stationary_hole_ignores and hole["col"] != center_col:
                continue
            if hole.get("solid_for_player"):
                continue
            if self._hole_visible_foot_overlap(hole, new_x) >= PLAYER_HOLE_FALL_OVERLAP:
                return hole
        return None

    def _hole_visible_foot_overlap(self, hole, x=None):
        image = self.get_current_image()
        if image is None:
            image = self.image
        if image is None:
            return 0

        x = self.x if x is None else x
        mask = pygame.mask.from_surface(image)
        hole_left = hole["col"] * TILE_SIZE
        hole_right = hole_left + TILE_SIZE
        local_left = max(0, floor(hole_left - x))
        local_right = min(image.get_width(), ceil(hole_right - x))
        if local_left >= local_right:
            return 0

        band_top = max(0, image.get_height() - PLAYER_HOLE_FOOT_BAND_HEIGHT)
        visible_columns = 0
        for px in range(local_left, local_right):
            for py in range(band_top, image.get_height()):
                if mask.get_at((px, py)):
                    visible_columns += 1
                    break
        return visible_columns

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

    def get_current_image(self):
        """Retorna el sprite visible en el frame actual."""
        is_falling = not self.on_ground and not self.on_ladder and not self.on_handrail and self.vel_y > 20
        if is_falling and self.fall_image:
            return self.fall_image_flip if self.facing_right else self.fall_image
        if self.on_ground and abs(self.vel_x) > 5 and self.walk_frames:
            frames = self.walk_frames_flip if self.facing_right else self.walk_frames
            return frames[self.walk_frame % len(frames)]
        if self.image:
            return self.image_flip if self.facing_right else self.image
        return None

    def draw(self, surface, cam_x=0, cam_y=0):
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        img = self.get_current_image()
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
