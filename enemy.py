# Lode Runner - Enemy

from collections import deque
import random

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
        self.facing_right = True
        self.image = None
        self.image_flip = None
        self.fall_image = None
        self.fall_image_flip = None
        # Walk animation
        self.walk_distance = 0.0
        self.walk_frame = 0
        self.walk_frames = []
        self.walk_frames_flip = []

        rng = random.Random(int(x) * 1009 + int(y) * 9173)
        self.intelligence = rng.uniform(0.65, 1.0)
        self.repath_interval = rng.uniform(0.12, 0.36) + (1.0 - self.intelligence) * 0.30
        self.repath_timer = 0.0
        self.path = []
        self.path_target = None
        self.prefer_vertical = rng.random() < self.intelligence
        self.lookahead_steps = 2 if self.intelligence > 0.85 else 1

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
            self._update_ai(dt, player_x, player_y, level_map)

        self._apply_physics(dt, level_map)
        self._update_animation(dt)

    def _update_in_hole(self, level_map):
        """Atrapado en un hoyo: solo puede escalar si hay escalera."""
        self.vel_x = 0.0
        if self.on_ladder:
            self.vel_y = -ENEMY_SPEED
        else:
            self.vel_y = 0.0

    def _update_ai(self, dt, player_x, player_y, level_map):
        """Persigue al player con pathfinding simple sobre la grilla del nivel."""
        start = self._entity_tile(self.x, self.y)
        target = self._entity_tile(player_x, player_y)

        self.repath_timer -= dt
        if self.repath_timer <= 0 or target != self.path_target or not self.path:
            self.path = self._find_path(start, target, level_map)
            self.path_target = target
            self.repath_timer = self.repath_interval

        if not self.path:
            self._fallback_chase(player_x, player_y)
            return

        self._follow_path(start, player_x, player_y, level_map)

    def _entity_tile(self, x, y):
        col = int((x + self.width // 2) / TILE_SIZE)
        row = int((y + self.height // 2) / TILE_SIZE)
        return row, col

    def _in_bounds(self, row, col, level_map):
        return 0 <= row < len(level_map) and 0 <= col < len(level_map[row])

    def _tile_at(self, row, col, level_map):
        if self._in_bounds(row, col, level_map):
            return level_map[row][col]
        return TILE_SOLID

    def _is_passable(self, row, col, level_map):
        return self._in_bounds(row, col, level_map) and self._tile_at(row, col, level_map) not in SOLID_TILES

    def _has_support(self, row, col, level_map):
        tile = self._tile_at(row, col, level_map)
        below = self._tile_at(row + 1, col, level_map)
        return tile in (TILE_LADDER, TILE_HANDRAIL) or below in SOLID_TILES

    def _target_candidates(self, target, level_map):
        target_row, target_col = target
        candidates = []
        for radius in range(0, 4):
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    if abs(dr) + abs(dc) != radius:
                        continue
                    row = target_row + dr
                    col = target_col + dc
                    if self._is_passable(row, col, level_map):
                        candidates.append((row, col))
            if candidates:
                return set(candidates)
        return {target}

    def _neighbors(self, node, target, level_map):
        row, col = node
        tile = self._tile_at(row, col, level_map)
        below = self._tile_at(row + 1, col, level_map)
        supported = self._has_support(row, col, level_map)

        if not supported and self._is_passable(row + 1, col, level_map):
            return [(row + 1, col)]

        horizontal = [(row, col - 1), (row, col + 1)]
        vertical = []

        if tile == TILE_LADDER and self._is_passable(row - 1, col, level_map):
            vertical.append((row - 1, col))
        if (tile == TILE_LADDER or below == TILE_LADDER) and self._is_passable(row + 1, col, level_map):
            vertical.append((row + 1, col))

        if self.prefer_vertical and target[0] != row:
            candidates = vertical + horizontal
        else:
            candidates = horizontal + vertical

        result = []
        for next_row, next_col in candidates:
            if self._is_passable(next_row, next_col, level_map):
                result.append((next_row, next_col))

        if self.intelligence > 0.78:
            result.sort(key=lambda n: abs(n[0] - target[0]) + abs(n[1] - target[1]))
        return result

    def _find_path(self, start, target, level_map):
        if not self._is_passable(start[0], start[1], level_map):
            return []

        targets = self._target_candidates(target, level_map)
        queue = deque([start])
        came_from = {start: None}
        found = None

        while queue:
            node = queue.popleft()
            if node in targets:
                found = node
                break
            for neighbor in self._neighbors(node, target, level_map):
                if neighbor not in came_from:
                    came_from[neighbor] = node
                    queue.append(neighbor)

        if found is None:
            return []

        path = []
        node = found
        while node is not None:
            path.append(node)
            node = came_from[node]
        path.reverse()
        return path

    def _follow_path(self, current, player_x, player_y, level_map):
        while len(self.path) > 1 and self.path[0] == current:
            self.path.pop(0)

        if not self.path:
            self._fallback_chase(player_x, player_y)
            return

        step_index = min(self.lookahead_steps - 1, len(self.path) - 1)
        next_row, next_col = self.path[step_index]
        current_row, current_col = current

        target_x = next_col * TILE_SIZE
        dx = target_x - self.x
        align_tolerance = 3.0 + (1.0 - self.intelligence) * 5.0
        speed = ENEMY_SPEED * (0.92 + self.intelligence * 0.12)

        self.vel_x = 0.0
        self.vel_y = 0.0

        if next_col != current_col:
            self.direction = 1 if dx > 0 else -1
            self.vel_x = self.direction * speed
            return

        if abs(dx) > align_tolerance:
            self.direction = 1 if dx > 0 else -1
            self.vel_x = self.direction * speed
            return

        self.x = target_x
        if next_row < current_row:
            self.vel_y = -speed if self.on_ladder else 0.0
        elif next_row > current_row:
            if self.on_ladder or self._tile_at(current_row + 1, current_col, level_map) == TILE_LADDER:
                self.vel_y = speed
            elif not self.on_ground:
                self.vel_y = max(self.vel_y, speed)

    def _fallback_chase(self, player_x, player_y):
        player_center_x = player_x + TILE_SIZE // 2
        my_center_x = self.x + self.width // 2
        if abs(player_center_x - my_center_x) > 2:
            self.direction = 1 if player_center_x > my_center_x else -1
            self.vel_x = self.direction * ENEMY_SPEED
        else:
            self.vel_x = 0.0
        self.vel_y = 0.0

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
                self.walk_frame = (self.walk_frame + 1) % max(1, len(self.walk_frames))
            self.facing_right = self.vel_x > 0
        elif self.on_ladder or self.on_handrail:
            self.walk_distance += abs(self.vel_y) * dt
            if self.walk_distance >= 16:
                self.walk_distance = 0.0
                self.walk_frame = (self.walk_frame + 1) % max(1, len(self.walk_frames))
        else:
            self.walk_distance = 0.0
            self.walk_frame = 0

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
        if self.walk_frames:
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
        c = COLOR_ENEMY
        pygame.draw.rect(surface, c, (sx + 12, sy + 10, 8, 12))
        pygame.draw.circle(surface, c, (sx + 16, sy + 7), 5)
        pygame.draw.line(surface, c, (sx + 14, sy + 22), (sx + 10, sy + 30), 2)
        pygame.draw.line(surface, c, (sx + 18, sy + 22), (sx + 22, sy + 30), 2)
        pygame.draw.line(surface, c, (sx + 12, sy + 13), (sx + 6, sy + 18), 2)
        pygame.draw.line(surface, c, (sx + 20, sy + 13), (sx + 26, sy + 18), 2)
