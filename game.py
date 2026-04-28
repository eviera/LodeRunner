# Lode Runner - Clase principal del juego

import pygame
import json
import os
import random

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(_BASE_DIR)

from constants import *
from player import Player
from enemy import Enemy
from evgamelib.rendering import RenderPipeline
from evgamelib.input_manager import InputManager
from evgamelib.sound_manager import SoundManager
from evgamelib.text import draw_text_with_outline


class Game:
    def __init__(self):
        self.pipeline = None
        self.input = InputManager(DEAD_ZONE)
        self.sound = SoundManager()
        self.font_hud = None
        self.font_msg = None

        self.state = STATE_PLAYING
        self.score = 0
        self.lives = INITIAL_LIVES
        self.current_level = 0

        self.levels = []
        self.level_map = []   # List[List[str]] mutable

        self.player = Player()
        self.enemies = []
        self.holes = []       # [{"row": r, "col": c, "timer": t}]
        self.gold_count = 0

        self.tile_images = {}
        self._enemy_img = None
        self._enemy_img_flip = None
        self._enemy_fall_img = None
        self._enemy_fall_img_flip = None
        self._enemy_walk_frames = []
        self._enemy_walk_frames_flip = []

        self.dying_timer = 0.0
        self.level_complete_timer = 0.0
        self.dying_flash = False   # toggling for flash effect

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def init(self):
        pygame.init()
        pygame.mixer.init()
        self.input.init_controllers()

        self.pipeline = RenderPipeline(
            GAME_WIDTH, GAME_VIEWPORT_HEIGHT,
            RENDER_SCALE, HUD_HEIGHT,
            SCREEN_WIDTH, SCREEN_HEIGHT,
        )
        self.pipeline.init_display(fullscreen=True)
        pygame.display.set_caption("Lode Runner")

        font_path = os.path.join(_BASE_DIR, FONT_FILE)
        if os.path.exists(font_path):
            self.font_hud = pygame.font.Font(font_path, FONT_SIZE_HUD)
            self.font_msg = pygame.font.Font(font_path, FONT_SIZE_MSG)
        else:
            self.font_hud = pygame.font.SysFont(None, FONT_SIZE_HUD * 2)
            self.font_msg = pygame.font.SysFont(None, FONT_SIZE_MSG * 2)

        self._load_assets()
        self._load_levels()
        self._start_level(0)

    def _load_image(self, path):
        """Carga una imagen PNG. Retorna None si no existe."""
        full = os.path.join(_BASE_DIR, path)
        if os.path.exists(full):
            try:
                return pygame.image.load(full).convert_alpha()
            except Exception:
                pass
        return None

    def _load_frames(self, paths):
        frames = []
        for path in paths:
            img = self._load_image(path)
            if img is not None:
                frames.append(img)
        return frames

    def _tint_image(self, img, color):
        if img is None:
            return None
        tinted = img.copy()
        tinted.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
        return tinted

    def _tint_frames(self, frames, color):
        return [self._tint_image(img, color) for img in frames]

    def _mask_overlap(self, image_a, pos_a, image_b, pos_b):
        if image_a is None or image_b is None:
            return False
        rect_a = image_a.get_rect(topleft=pos_a)
        rect_b = image_b.get_rect(topleft=pos_b)
        if not rect_a.colliderect(rect_b):
            return False

        mask_a = pygame.mask.from_surface(image_a)
        mask_b = pygame.mask.from_surface(image_b)
        offset = (rect_b.x - rect_a.x, rect_b.y - rect_a.y)
        return mask_a.overlap(mask_b, offset) is not None

    def _load_assets(self):
        # Tiles sólidos (fallback: superficie coloreada)
        for key, path, color in [
            (TILE_SOLID,    'tiles/solid_brick.png', COLOR_SOLID),
            (TILE_BRICK,    'tiles/brick.png',       COLOR_BRICK),
        ]:
            img = self._load_image(path)
            if img is None:
                img = pygame.Surface((TILE_SIZE, TILE_SIZE))
                img.fill(color)
            self.tile_images[key] = img

        # Tiles con alpha (ladder, gold, handrail) — sin fallback en tile_images,
        # se dibujan con métodos _draw_*_fallback si no hay PNG
        for key, path in [
            (TILE_LADDER,   'tiles/ladder.png'),
            (TILE_GOLD,     'tiles/gold.png'),
            (TILE_HANDRAIL, 'tiles/handrail.png'),
        ]:
            img = self._load_image(path)
            if img is not None:
                self.tile_images[key] = img

        # Sprites de Lode. Los PNG base miran a la izquierda; se espejan en memoria.
        player_img = self._load_image('sprites/lode_idle.png') or self._load_image('sprites/player.png')
        if player_img:
            self.player.image = player_img
            self.player.image_flip = pygame.transform.flip(player_img, True, False)

        fall_img = self._load_image('sprites/lode_fall.png')
        if fall_img:
            self.player.fall_image = fall_img
            self.player.fall_image_flip = pygame.transform.flip(fall_img, True, False)

        walk_frames = self._load_frames([
            'sprites/lode_run_1.png',
            'sprites/lode_run_2.png',
            'sprites/lode_run_3.png',
            'sprites/lode_run_2.png',
        ])
        if walk_frames:
            self.player.walk_frames = walk_frames
            self.player.walk_frames_flip = [
                pygame.transform.flip(img, True, False) for img in walk_frames
            ]

        # Por ahora enemies usan el mismo set visual que Lode, tintado a celeste en runtime.
        self._enemy_img = self._tint_image(self.player.image, COLOR_ENEMY)
        self._enemy_img_flip = pygame.transform.flip(self._enemy_img, True, False) if self._enemy_img else None
        self._enemy_fall_img = self._tint_image(self.player.fall_image, COLOR_ENEMY)
        self._enemy_fall_img_flip = pygame.transform.flip(self._enemy_fall_img, True, False) if self._enemy_fall_img else None
        self._enemy_walk_frames = self._tint_frames(self.player.walk_frames, COLOR_ENEMY)
        self._enemy_walk_frames_flip = [
            pygame.transform.flip(img, True, False) for img in self._enemy_walk_frames
        ]

    def _load_levels(self):
        path = os.path.join(_BASE_DIR, SCREENS_FILE)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                screens = json.load(f)
            for s in screens:
                raw = s.get("map", [])
                normalized = self._normalize_map(raw)
                self.levels.append(normalized)
        if not self.levels:
            self.levels.append(self._default_level())

    def _normalize_map(self, raw):
        result = []
        for row in raw[:VIEWPORT_ROWS]:
            row = str(row)
            if len(row) < VIEWPORT_COLS:
                row = row + ' ' * (VIEWPORT_COLS - len(row))
            result.append(row[:VIEWPORT_COLS])
        while len(result) < VIEWPORT_ROWS:
            result.append('#' * VIEWPORT_COLS)
        return result

    def _default_level(self):
        return [
            "################",
            "#P G  H  H  G E#",
            "#BBBB H  H BBBB#",
            "#H    H  H    H#",
            "#H G--H  H--G H#",
            "#HBBBBHBBHBBBHB#",
            "#H    H  H    H#",
            "################",
        ]

    def _start_level(self, level_index):
        if level_index >= len(self.levels):
            level_index = 0
        self.current_level = level_index

        # Copiar el mapa como lista mutable de listas de chars
        self.level_map = [list(row) for row in self.levels[level_index]]

        self.enemies = []
        self.holes = []
        self.gold_count = 0

        for row_i, row in enumerate(self.level_map):
            for col_i, tile in enumerate(row):
                if tile == TILE_PLAYER:
                    self.player.x = float(col_i * TILE_SIZE)
                    self.player.y = float(row_i * TILE_SIZE)
                    self.player.vel_x = 0.0
                    self.player.vel_y = 0.0
                    self.level_map[row_i][col_i] = TILE_AIR
                elif tile == TILE_ENEMY:
                    e = Enemy(col_i * TILE_SIZE, row_i * TILE_SIZE)
                    e.image = self._enemy_img
                    e.image_flip = self._enemy_img_flip
                    e.fall_image = self._enemy_fall_img
                    e.fall_image_flip = self._enemy_fall_img_flip
                    e.walk_frames = self._enemy_walk_frames
                    e.walk_frames_flip = self._enemy_walk_frames_flip
                    self.enemies.append(e)
                    self.level_map[row_i][col_i] = TILE_AIR
                elif tile == TILE_GOLD:
                    self.gold_count += 1

        self.state = STATE_PLAYING
        self.dying_timer = 0.0
        self.level_complete_timer = 0.0
        self.dying_flash = False

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        clock = pygame.time.Clock()
        running = True

        while running:
            dt = min(clock.tick(FPS) / 1000.0, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_F11:
                        self.pipeline.toggle_fullscreen()
                    elif event.key in (pygame.K_RETURN, pygame.K_r):
                        if self.state == STATE_GAME_OVER:
                            self.score = 0
                            self.lives = INITIAL_LIVES
                            self._start_level(0)

            self.input.poll()
            self._update(dt)
            self._render()

        pygame.quit()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _update(self, dt):
        if self.state == STATE_PLAYING:
            self._update_playing(dt)
        elif self.state == STATE_DYING:
            self._update_dying(dt)
        elif self.state == STATE_LEVEL_COMPLETE:
            self._update_level_complete(dt)

    def _update_playing(self, dt):
        keys = self.input.keys
        joy_x = self.input.joy_axis_x
        joy_y = self.input.joy_axis_y

        self.player.update(dt, keys, joy_x, joy_y, self.level_map, self.holes)

        # Digging: Z=izquierda, X=derecha
        if keys[pygame.K_z]:
            ok, row, col = self.player.try_dig(-1, self.level_map)
            if ok:
                self.level_map[row][col] = TILE_AIR
                self.holes.append({"row": row, "col": col, "timer": HOLE_FILL_TIME})
        if keys[pygame.K_x]:
            ok, row, col = self.player.try_dig(1, self.level_map)
            if ok:
                self.level_map[row][col] = TILE_AIR
                self.holes.append({"row": row, "col": col, "timer": HOLE_FILL_TIME})

        for enemy in self.enemies:
            enemy.update(dt, self.level_map, self.player.x, self.player.y, self.holes)

        self._update_holes(dt)
        self._collect_gold()
        self._check_enemy_collision()

        if self.gold_count <= 0 and self.state == STATE_PLAYING:
            self.state = STATE_LEVEL_COMPLETE
            self.level_complete_timer = LEVEL_COMPLETE_DELAY
            self.score += SCORE_LEVEL_COMPLETE

    def _collect_gold(self):
        player_img = self.player.get_current_image()
        player_pos = (int(self.player.x), int(self.player.y))
        gold_img = self.tile_images.get(TILE_GOLD)
        if player_img is None or gold_img is None:
            return

        level_h = len(self.level_map)
        px_center_col = int((self.player.x + self.player.width // 2) / TILE_SIZE)
        py_center_row = int((self.player.y + self.player.height // 2) / TILE_SIZE)

        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                r = py_center_row + dr
                c = px_center_col + dc
                if 0 <= r < level_h and 0 <= c < len(self.level_map[r]):
                    if self.level_map[r][c] == TILE_GOLD:
                        gold_pos = (c * TILE_SIZE, r * TILE_SIZE)
                        if self._mask_overlap(player_img, player_pos, gold_img, gold_pos):
                            self.level_map[r][c] = TILE_AIR
                            self.gold_count -= 1
                            self.score += SCORE_GOLD

    def _check_enemy_collision(self):
        if self.state != STATE_PLAYING:
            return
        player_img = self.player.get_current_image()
        player_pos = (int(self.player.x), int(self.player.y))
        if player_img is None:
            return

        for enemy in self.enemies:
            enemy_img = enemy.get_current_image()
            enemy_pos = (int(enemy.x), int(enemy.y))
            enemy_is_trapped = enemy.in_hole and enemy.hole_settled
            if not enemy_is_trapped and self._mask_overlap(player_img, player_pos, enemy_img, enemy_pos):
                self.state = STATE_DYING
                self.dying_timer = DYING_FLASH_TIME
                return

    def _update_holes(self, dt):
        to_remove = []
        level_h = len(self.level_map)
        for hole in self.holes:
            hole["timer"] -= dt
            if hole["timer"] <= 0:
                r, c = hole["row"], hole["col"]
                if 0 <= r < level_h and 0 <= c < len(self.level_map[r]):
                    self.level_map[r][c] = TILE_BRICK

                    hole_rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)

                    # Kill and respawn enemy inside hole
                    for enemy in self.enemies:
                        if self._enemy_is_in_hole(enemy, r, c, hole_rect):
                            self.score += SCORE_ENEMY_KILL
                            self._respawn_enemy(enemy)

                    # Kill player if inside hole
                    if self.player.get_rect().colliderect(hole_rect):
                        self.state = STATE_DYING
                        self.dying_timer = DYING_FLASH_TIME

                to_remove.append(hole)

        for hole in to_remove:
            self.holes.remove(hole)

    def _enemy_is_in_hole(self, enemy, row, col, hole_rect):
        return (
            enemy.active and
            (
                (enemy.in_hole and enemy.current_hole == (row, col)) or
                enemy.get_rect().colliderect(hole_rect)
            )
        )

    def _respawn_enemy(self, enemy):
        spawn = self._random_enemy_spawn()
        enemy.x = float(spawn[1] * TILE_SIZE)
        enemy.y = float(spawn[0] * TILE_SIZE)
        enemy.vel_x = 0.0
        enemy.vel_y = 0.0
        enemy.in_hole = False
        enemy.current_hole = None
        enemy.hole_settled = False
        enemy.hole_escape_timer = 0.0
        enemy.path = []
        enemy.path_target = None
        enemy.repath_timer = 0.0
        enemy.stuck_timer = 0.0
        enemy.idle_timer = 0.0
        enemy.unstuck_timer = 0.0
        enemy.walk_distance = 0.0
        enemy.walk_frame = 0

    def _random_enemy_spawn(self):
        candidates = []
        open_holes = {(hole["row"], hole["col"]) for hole in self.holes}
        player_rect = self.player.get_rect()
        level_h = len(self.level_map)

        for row in range(max(0, level_h - 1)):
            for col in range(len(self.level_map[row])):
                if (row, col) in open_holes:
                    continue
                if self.level_map[row][col] in SOLID_TILES:
                    continue
                if row + 1 >= level_h or col >= len(self.level_map[row + 1]):
                    continue
                if self.level_map[row + 1][col] not in SOLID_TILES:
                    continue

                rect = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if rect.colliderect(player_rect.inflate(TILE_SIZE * 2, TILE_SIZE * 2)):
                    continue
                candidates.append((row, col))

        if not candidates:
            return (1, 1)
        return random.choice(candidates)

    def _update_dying(self, dt):
        self.dying_timer -= dt
        self.dying_flash = int(self.dying_timer * 8) % 2 == 0
        if self.dying_timer <= 0:
            self.lives -= 1
            if self.lives <= 0:
                self.state = STATE_GAME_OVER
            else:
                self._start_level(self.current_level)

    def _update_level_complete(self, dt):
        self.level_complete_timer -= dt
        if self.level_complete_timer <= 0:
            self._start_level(self.current_level + 1)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def _render(self):
        gs = self.pipeline.game_surface
        gs.fill(COLOR_BG)
        self._render_level(gs)
        self._render_entities(gs)
        self.pipeline.scale_game_to_screen()
        self._render_hud()
        self._render_overlays()
        self.pipeline.present()

    def _render_level(self, surf):
        for row_i, row in enumerate(self.level_map):
            for col_i, tile in enumerate(row):
                if tile == TILE_AIR:
                    continue
                x = col_i * TILE_SIZE
                y = row_i * TILE_SIZE

                if tile in self.tile_images:
                    img = self.tile_images[tile]
                    surf.blit(img, (x, y))
                    # Si la imagen no tiene transparencia (placeholder sólido), no sobrescribir
                elif tile == TILE_LADDER:
                    self._draw_ladder_fallback(surf, x, y)
                elif tile == TILE_HANDRAIL:
                    self._draw_handrail_fallback(surf, x, y)
                elif tile == TILE_GOLD:
                    self._draw_gold_fallback(surf, x, y)

        # Hoyos activos (oscuros)
        for hole in self.holes:
            x = hole["col"] * TILE_SIZE
            y = hole["row"] * TILE_SIZE
            pygame.draw.rect(surf, COLOR_HOLE, (x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4))

    def _draw_ladder_fallback(self, surf, x, y):
        c = COLOR_LADDER
        pygame.draw.line(surf, c, (x + 8, y), (x + 8, y + TILE_SIZE - 1), 2)
        pygame.draw.line(surf, c, (x + 22, y), (x + 22, y + TILE_SIZE - 1), 2)
        for ry in range(y + 4, y + TILE_SIZE, 8):
            pygame.draw.line(surf, c, (x + 8, ry), (x + 22, ry), 2)

    def _draw_handrail_fallback(self, surf, x, y):
        mid_y = y + TILE_SIZE // 2
        pygame.draw.line(surf, COLOR_HANDRAIL, (x, mid_y), (x + TILE_SIZE, mid_y), 3)

    def _draw_gold_fallback(self, surf, x, y):
        cx, cy = x + TILE_SIZE // 2, y + TILE_SIZE // 2
        pygame.draw.circle(surf, COLOR_GOLD, (cx, cy), 7)
        pygame.draw.circle(surf, (200, 150, 0), (cx, cy), 5)

    def _render_entities(self, surf):
        if self.state == STATE_DYING and not self.dying_flash:
            pass  # Parpadeo: no dibujar player
        else:
            self.player.draw(surf)

        for enemy in self.enemies:
            enemy.draw(surf)

    def _render_hud(self):
        screen = self.pipeline.screen
        vp_h = self.pipeline.viewport_h
        hw = self.pipeline.screen_w

        # Fondo negro del área HUD
        screen.fill(HUD_BG_COLOR, (0, vp_h, hw, HUD_HEIGHT))

        # Barra superior (ladrillo)
        screen.fill(HUD_BAR_COLOR, (0, vp_h, hw, HUD_BAR_HEIGHT))

        # Barra inferior (ladrillo)
        screen.fill(HUD_BAR_COLOR, (0, vp_h + HUD_HEIGHT - HUD_BAR_HEIGHT, hw, HUD_BAR_HEIGHT))

        # Texto centrado
        center_y = vp_h + HUD_HEIGHT // 2
        score_str = f"SCORE {self.score:06d}   MEN {self.lives:02d}   LEVEL {self.current_level + 1:02d}"
        text_surf = self.font_hud.render(score_str, True, HUD_TEXT_COLOR)
        text_rect = text_surf.get_rect(center=(hw // 2, center_y))
        screen.blit(text_surf, text_rect)

    def _render_overlays(self):
        screen = self.pipeline.screen
        vp_h = self.pipeline.viewport_h
        hw = self.pipeline.screen_w
        cx = hw // 2
        cy = vp_h // 2

        if self.state == STATE_LEVEL_COMPLETE:
            surf = self.font_msg.render("LEVEL COMPLETE!", True, (255, 220, 50))
            screen.blit(surf, surf.get_rect(center=(cx, cy)))

        elif self.state == STATE_GAME_OVER:
            surf = self.font_msg.render("GAME OVER", True, (220, 50, 50))
            screen.blit(surf, surf.get_rect(center=(cx, cy - 20)))
            surf2 = self.font_hud.render("PRESS ENTER TO RETRY", True, COLOR_LADDER)
            screen.blit(surf2, surf2.get_rect(center=(cx, cy + 20)))
