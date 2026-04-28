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

        self.rng = random.Random(int(x) * 1009 + int(y) * 9173)
        self.intelligence = self.rng.uniform(0.65, 1.0)
        self.speed_factor = self.rng.uniform(1.0 - ENEMY_SPEED_VARIATION, 1.0 + ENEMY_SPEED_VARIATION)
        self.repath_interval = self.rng.uniform(0.12, 0.36) + (1.0 - self.intelligence) * 0.30
        self.repath_timer = 0.0
        self.path = []
        self.path_target = None
        self.prefer_vertical = self.rng.random() < self.intelligence
        self.lookahead_steps = 2 if self.intelligence > 0.85 else 1
        self.stuck_timer = 0.0
        self.idle_timer = 0.0
        self.unstuck_timer = 0.0
        self.unstuck_dir = 1
        self.hole_escape_timer = 0.0
        self.current_hole = None
        self.hole_settled = False
        self._last_x = self.x
        self._last_y = self.y

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

    def _hole_at_position(self, holes):
        center_row = int((self.y + self.height // 2) / TILE_SIZE)
        foot_row = int((self.y + self.height + 1) / TILE_SIZE)
        enemy_col = int((self.x + self.width // 2) / TILE_SIZE)
        for hole in holes:
            if hole["col"] == enemy_col and hole["row"] in (center_row, foot_row):
                return hole
        return None

    def update(self, dt, level_map, player_x, player_y, holes):
        old_x = self.x
        old_y = self.y
        self._detect_states(level_map)
        hole = self._hole_at_position(holes)
        was_in_hole = self.in_hole
        self.in_hole = hole is not None

        if self.in_hole and (not was_in_hole or self.current_hole != (hole["row"], hole["col"])):
            self.hole_escape_timer = ENEMY_HOLE_ESCAPE_TIME
            self.current_hole = (hole["row"], hole["col"])
            self.hole_settled = False

        if self.in_hole:
            self.stuck_timer = 0.0
            self.idle_timer = 0.0
            self.unstuck_timer = 0.0
            self._update_in_hole(dt, level_map, hole)
        elif self.unstuck_timer > 0:
            self.current_hole = None
            self._update_unstuck(dt, player_x, player_y, level_map)
        else:
            self.current_hole = None
            self._update_ai(dt, player_x, player_y, level_map)

        intended_movement = abs(self.vel_x) > 5 or abs(self.vel_y) > 5
        self._apply_physics(dt, level_map)
        if self.in_hole:
            self._settle_in_hole_if_ready(hole)
        if not self.in_hole:
            self._update_stuck_state(dt, old_x, old_y, intended_movement)
        self._update_animation(dt)

    def _update_in_hole(self, dt, level_map, hole):
        """Atrapado en un hoyo temporal; puede escaparse antes de que cierre."""
        target_x = float(hole["col"] * TILE_SIZE)
        target_y = float(hole["row"] * TILE_SIZE)

        if not self.hole_settled:
            dx = target_x - self.x
            if abs(dx) <= 2:
                self.x = target_x
                self.vel_x = 0.0
            else:
                self.vel_x = self._speed() if dx > 0 else -self._speed()

            if self.y >= target_y:
                self._settle_in_hole(hole)
            return

        self.vel_x = 0.0
        self.vel_y = 0.0
        if self.hole_escape_timer > 0:
            self.hole_escape_timer -= dt
            if self.hole_escape_timer > 0:
                return

        self._escape_hole(level_map, hole)

    def _settle_in_hole_if_ready(self, hole):
        if not self.hole_settled and self.y >= hole["row"] * TILE_SIZE:
            self._settle_in_hole(hole)

    def _settle_in_hole(self, hole):
        self.x = float(hole["col"] * TILE_SIZE)
        self.y = float(hole["row"] * TILE_SIZE)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.hole_settled = True

    def _escape_hole(self, level_map, hole):
        row = hole["row"]
        col = hole["col"]
        directions = [-1, 1]
        if self.rng.random() < 0.5:
            directions.reverse()

        for direction in directions:
            exit_col = col + direction
            exit_row = row - 1
            if self._has_support(exit_row, exit_col, level_map) and self._is_passable(exit_row, exit_col, level_map):
                self.x = float(exit_col * TILE_SIZE)
                self.y = float(exit_row * TILE_SIZE)
                self.direction = direction
                self.vel_x = 0.0
                self.vel_y = 0.0
                self.in_hole = False
                self.current_hole = None
                self.hole_settled = False
                self.hole_escape_timer = 0.0
                return

        self.vel_y = -self._speed()

    def _speed(self):
        return ENEMY_SPEED * self.speed_factor * (0.92 + self.intelligence * 0.12)

    def _update_ai(self, dt, player_x, player_y, level_map):
        """Persigue al player con pathfinding simple sobre la grilla del nivel."""
        start = self._entity_tile(self.x, self.y)
        target = self._entity_tile(player_x, player_y)

        if self._try_direct_same_row_chase(start, target, player_x, level_map):
            self.path = []
            return

        self.repath_timer -= dt
        if self.repath_timer <= 0 or target != self.path_target or not self.path:
            self.path = self._find_path(start, target, level_map)
            self.path_target = target
            self.repath_timer = self.repath_interval

        if not self.path:
            self._fallback_chase(player_x, player_y, level_map)
            return

        self._follow_path(start, player_x, player_y, level_map)

    def _try_direct_same_row_chase(self, start, target, player_x, level_map):
        row, col = start
        target_row, target_col = target
        if row != target_row:
            return False
        if not self._has_support(row, col, level_map):
            return False

        if target_col == col:
            speed = self._speed()
            player_center_x = player_x + TILE_SIZE // 2
            my_center_x = self.x + self.width // 2
            dx = player_center_x - my_center_x
            if abs(dx) > 2:
                self.direction = 1 if dx > 0 else -1
                self.vel_x = self.direction * speed
                self.vel_y = 0.0
            else:
                self.vel_x = 0.0
                self.vel_y = 0.0
            return True

        step = 1 if target_col > col else -1
        for check_col in range(col + step, target_col + step, step):
            if not self._is_passable(row, check_col, level_map):
                return False
            if not self._has_support(row, check_col, level_map):
                return False

        speed = self._speed()

        if self._align_y_for_horizontal_exit(row, col, speed, level_map):
            return True

        self.direction = step
        self.vel_x = step * speed
        self.vel_y = 0.0
        return True

    def _align_y_for_horizontal_exit(self, row, col, speed, level_map):
        if not self._has_support(row, col, level_map):
            return False

        target_y = row * TILE_SIZE
        dy = target_y - self.y
        if abs(dy) <= TILE_SIZE * 0.5:
            self.y = target_y
            return False

        self.vel_x = 0.0
        self.vel_y = speed if dy > 0 else -speed
        return True

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
        if current in self.path:
            current_index = self.path.index(current)
            self.path = self.path[current_index:]

        while len(self.path) > 1 and self.path[0] == current:
            self.path.pop(0)

        if not self.path:
            self._fallback_chase(player_x, player_y, level_map)
            return

        current_row, current_col = current
        on_ladder_tile = self._tile_at(current_row, current_col, level_map) == TILE_LADDER
        next_is_vertical = len(self.path) > 0 and self.path[0][1] == current_col and self.path[0][0] != current_row
        step_index = 0 if on_ladder_tile or next_is_vertical else min(self.lookahead_steps - 1, len(self.path) - 1)
        next_row, next_col = self.path[step_index]

        target_x = next_col * TILE_SIZE
        dx = target_x - self.x
        target_y = current_row * TILE_SIZE
        dy = target_y - self.y
        align_tolerance = 3.0 + (1.0 - self.intelligence) * 5.0
        speed = self._speed()

        self.vel_x = 0.0
        self.vel_y = 0.0

        if on_ladder_tile:
            ladder_x = current_col * TILE_SIZE
            ladder_dx = ladder_x - self.x
            if abs(ladder_dx) > align_tolerance:
                self.direction = 1 if ladder_dx > 0 else -1
                self.vel_x = self.direction * speed
                return
            self.x = ladder_x

            if next_col != current_col:
                if abs(dy) > align_tolerance:
                    self.vel_y = speed if dy > 0 else -speed
                    return
                self.y = target_y
            elif next_row < current_row:
                self.vel_y = -speed
                return
            elif next_row > current_row:
                self.vel_y = speed
                return

        if next_col != current_col:
            if self._align_y_for_horizontal_exit(current_row, current_col, speed, level_map):
                return
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

    def _fallback_chase(self, player_x, player_y, level_map=None):
        player_center_x = player_x + TILE_SIZE // 2
        my_center_x = self.x + self.width // 2
        if abs(player_center_x - my_center_x) > 2:
            self.direction = 1 if player_center_x > my_center_x else -1
            if level_map is not None:
                row, col = self._entity_tile(self.x, self.y)
                if self._align_y_for_horizontal_exit(row, col, self._speed(), level_map):
                    return
            self.vel_x = self.direction * self._speed()
        else:
            self.vel_x = 0.0
        self.vel_y = 0.0

    def _update_stuck_state(self, dt, old_x, old_y, intended_movement):
        moved = abs(self.x - old_x) + abs(self.y - old_y)
        if intended_movement and moved < 0.2:
            self.stuck_timer += dt
        else:
            self.stuck_timer = max(0.0, self.stuck_timer - dt * 2)

        if not intended_movement and moved < 0.2:
            self.idle_timer += dt
        else:
            self.idle_timer = 0.0

        if self.stuck_timer > ENEMY_STUCK_TIME or self.idle_timer > ENEMY_IDLE_UNSTUCK_TIME:
            self._start_unstuck()

    def _start_unstuck(self):
        self.path = []
        self.repath_timer = 0.0
        self.stuck_timer = 0.0
        self.idle_timer = 0.0
        self.unstuck_timer = ENEMY_UNSTUCK_TIME
        self.unstuck_dir = -self.direction if self.rng.random() < 0.5 else self.direction
        if self.unstuck_dir == 0:
            self.unstuck_dir = 1 if self.rng.random() < 0.5 else -1

    def _update_unstuck(self, dt, player_x, player_y, level_map):
        self.unstuck_timer = max(0.0, self.unstuck_timer - dt)
        speed = self._speed()
        row, col = self._entity_tile(self.x, self.y)

        self.vel_x = 0.0
        self.vel_y = 0.0

        if self.on_ladder and self.rng.random() < 0.35:
            player_center_y = player_y + TILE_SIZE // 2
            my_center_y = self.y + self.height // 2
            if abs(player_center_y - my_center_y) > 2:
                self.vel_y = speed if player_center_y > my_center_y else -speed
                return

        if self._align_y_for_horizontal_exit(row, col, speed, level_map):
            return

        for direction in (self.unstuck_dir, -self.unstuck_dir):
            next_x = self.x + direction * speed * max(dt, 1 / FPS)
            if not self._check_collision(next_x, self.y, level_map):
                self.direction = direction
                self.vel_x = direction * speed
                return

        if self.on_ladder:
            self.vel_y = -speed if self.rng.random() < 0.5 else speed
        elif not self.on_ground:
            self.vel_y = speed

        if self.unstuck_timer <= 0:
            self.path = []
            self.repath_timer = 0.0

    def _apply_physics(self, dt, level_map):
        ladder_holding = self.on_ladder and abs(self.vel_x) < 5
        if not ladder_holding and not self.on_handrail and (not self.in_hole or not self.hole_settled):
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
