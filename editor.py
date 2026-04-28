# Lode Runner - Editor de niveles
# Editor de pantallas fijas 32x18 para el juego Lode Runner.

import json
import os

import pygame

# Asegurar que el cwd sea el directorio del script (necesario en Mac cuando
# se ejecuta desde Finder).
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from constants import *  # noqa: E402,F403


COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (140, 140, 140)
COLOR_DARK_GRAY = (40, 40, 40)
COLOR_YELLOW = (255, 220, 50)
COLOR_GREEN = (80, 230, 80)
COLOR_RED = (230, 70, 70)
COLOR_BLUE = (70, 120, 240)

EDITOR_HUD_HEIGHT = 126
EDITOR_SCALE = 1

TILE_TYPES = [
    (TILE_AIR, "Aire", (18, 18, 18)),
    (TILE_SOLID, "Solido", COLOR_SOLID),
    (TILE_BRICK, "Ladrillo", COLOR_BRICK),
    (TILE_LADDER, "Escalera", COLOR_LADDER),
    (TILE_HANDRAIL, "Barra", COLOR_HANDRAIL),
    (TILE_GOLD, "Oro", COLOR_GOLD),
    (TILE_PLAYER, "Player", COLOR_PLAYER),
    (TILE_ENEMY, "Enemigo", COLOR_ENEMY),
]

KEY_LABELS = "12345678"


def load_screens():
    """Cargar pantallas desde archivo JSON."""
    if os.path.exists(SCREENS_FILE):
        try:
            with open(SCREENS_FILE, "r", encoding="utf-8") as f:
                screens = json.load(f)
            if isinstance(screens, list):
                return screens
        except Exception as e:
            print(f"Error cargando screens: {e}")
    return []


def save_screens(screens):
    """Guardar pantallas a archivo JSON."""
    try:
        with open(SCREENS_FILE, "w", encoding="utf-8") as f:
            json.dump(screens, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error guardando screens: {e}")
        return False


def normalize_map(level_map):
    """Normalizar mapa a una pantalla fija de VIEWPORT_COLS x VIEWPORT_ROWS."""
    result = []
    rows = level_map if isinstance(level_map, list) else []
    for row in rows[:VIEWPORT_ROWS]:
        row = str(row)
        if len(row) < VIEWPORT_COLS:
            row += TILE_AIR * (VIEWPORT_COLS - len(row))
        result.append(row[:VIEWPORT_COLS])

    while len(result) < VIEWPORT_ROWS:
        result.append(TILE_AIR * VIEWPORT_COLS)

    return result


class Editor:
    def __init__(self):
        pygame.init()
        self.editor_w = GAME_WIDTH
        self.editor_viewport_h = GAME_VIEWPORT_HEIGHT
        self.editor_h = self.editor_viewport_h + EDITOR_HUD_HEIGHT
        self.screen = pygame.Surface((self.editor_w, self.editor_h))
        self.display = pygame.display.set_mode(
            (self.editor_w * EDITOR_SCALE, self.editor_h * EDITOR_SCALE)
        )
        pygame.display.set_caption("Lode Runner Level Editor")
        try:
            pygame.scrap.init()
        except Exception:
            pass

        try:
            icon = pygame.image.load("sprites/lode_idle.png").convert_alpha()
            pygame.display.set_icon(icon)
        except Exception:
            pass

        self.clock = pygame.time.Clock()

        try:
            self.font = pygame.font.Font("fonts/PressStart2P-vaV7.ttf", 10)
            self.small_font = pygame.font.Font("fonts/PressStart2P-vaV7.ttf", 8)
        except Exception:
            self.font = pygame.font.Font(None, 16)
            self.small_font = pygame.font.Font(None, 12)
        self.hint_font = pygame.font.SysFont("consolas", 14)

        self.tiles = {}
        self.sprites = {}
        self._load_assets()

        self.screens = load_screens()
        for i, screen in enumerate(self.screens):
            if not isinstance(screen, dict):
                self.screens[i] = {"name": f"Level {i + 1}", "map": []}
            self.screens[i]["name"] = self.screens[i].get("name", f"Level {i + 1}")
            self.screens[i]["map"] = normalize_map(self.screens[i].get("map", []))

        self.current_level = 0
        self.cursor_row = 0
        self.cursor_col = 0
        self.selected_tile = 2
        self.saved_indicator = 0.0
        self.dirty = False
        self.confirm_exit = False
        self.confirm_delete_level = False

        if not self.screens:
            self.new_level()

    def _load_image(self, path):
        try:
            if os.path.exists(path):
                return pygame.image.load(path).convert_alpha()
        except Exception:
            pass
        return None

    def _load_assets(self):
        for key, path, color in [
            (TILE_SOLID, "tiles/solid_brick.png", COLOR_SOLID),
            (TILE_BRICK, "tiles/brick.png", COLOR_BRICK),
            (TILE_LADDER, "tiles/ladder.png", COLOR_LADDER),
            (TILE_GOLD, "tiles/gold.png", COLOR_GOLD),
            (TILE_HANDRAIL, "tiles/handrail.png", COLOR_HANDRAIL),
        ]:
            img = self._load_image(path)
            if img is None:
                img = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                img.fill((*color, 255))
            self.tiles[key] = img

        player = self._load_image("sprites/lode_idle.png") or self._load_image("sprites/player.png")
        enemy = self._load_image("sprites/enemy.png") or player
        if player is not None:
            self.sprites[TILE_PLAYER] = player
        if enemy is not None:
            if enemy == player:
                enemy = self._tint_image(enemy, COLOR_ENEMY)
            self.sprites[TILE_ENEMY] = enemy

    def _tint_image(self, img, color):
        tinted = img.copy()
        tinted.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
        return tinted

    def new_level(self):
        empty_map = []
        for r in range(VIEWPORT_ROWS):
            if r in (0, VIEWPORT_ROWS - 1):
                empty_map.append(TILE_SOLID * VIEWPORT_COLS)
            else:
                empty_map.append(TILE_SOLID + TILE_AIR * (VIEWPORT_COLS - 2) + TILE_SOLID)

        self.screens.append({
            "name": f"Level {len(self.screens) + 1}",
            "map": empty_map,
        })
        self.current_level = len(self.screens) - 1
        self.cursor_row = 1
        self.cursor_col = 1
        self.dirty = True

    def get_current_screen(self):
        return self.screens[self.current_level]

    def get_current_map(self):
        return self.get_current_screen()["map"]

    def set_tile(self, row, col, char):
        if not (0 <= row < VIEWPORT_ROWS and 0 <= col < VIEWPORT_COLS):
            return
        level_map = self.get_current_map()
        row_str = level_map[row]
        if row_str[col] != char:
            level_map[row] = row_str[:col] + char + row_str[col + 1:]
            self.dirty = True

    def fill_current_level(self, char):
        self.get_current_screen()["map"] = [char * VIEWPORT_COLS for _ in range(VIEWPORT_ROWS)]
        self.cursor_row = 0
        self.cursor_col = 0
        self.dirty = True

    def validate_screens(self):
        for i, screen in enumerate(self.screens):
            flat = "".join(screen["map"])
            player_count = flat.count(TILE_PLAYER)
            if player_count != 1:
                print(f"ADVERTENCIA: Nivel {i + 1} debe tener exactamente 1 tile P (tiene {player_count})")

    def save(self):
        self.validate_screens()
        if save_screens(self.screens):
            self.saved_indicator = 2.0
            self.dirty = False
            print(f"Pantallas guardadas en {SCREENS_FILE}")

    def copy_map_to_clipboard(self):
        try:
            text = "\n".join(self.get_current_map())
            pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
            self.saved_indicator = 0.5
        except Exception as e:
            print(f"No se pudo copiar al clipboard: {e}")

    def paste_map_from_clipboard(self):
        try:
            clip = pygame.scrap.get(pygame.SCRAP_TEXT)
            if not clip:
                return
            text = clip.decode("utf-8").strip("\x00")
            rows = text.splitlines()
            if rows:
                self.get_current_screen()["map"] = normalize_map(rows)
                self.cursor_row = 0
                self.cursor_col = 0
                self.dirty = True
        except Exception as e:
            print(f"No se pudo pegar desde clipboard: {e}")

    def change_level(self, delta):
        next_level = self.current_level + delta
        if 0 <= next_level < len(self.screens):
            self.current_level = next_level
            self.cursor_row = 0
            self.cursor_col = 0

    def delete_current_level(self):
        if len(self.screens) <= 1:
            return
        self.screens.pop(self.current_level)
        if self.current_level >= len(self.screens):
            self.current_level = len(self.screens) - 1
        self.cursor_row = 0
        self.cursor_col = 0
        self.dirty = True

    def selected_char(self):
        return TILE_TYPES[self.selected_tile][0]

    def current_char(self):
        return self.get_current_map()[self.cursor_row][self.cursor_col]

    def current_tile_name(self):
        current = self.current_char()
        return next((name for char, name, _color in TILE_TYPES if char == current), "?")

    def draw_tile(self, surf, tile, x, y):
        if tile == TILE_AIR:
            pygame.draw.rect(surf, (8, 8, 8), (x, y, TILE_SIZE, TILE_SIZE))
        elif tile in self.tiles:
            surf.blit(self.tiles[tile], (x, y))
        elif tile in self.sprites:
            pygame.draw.rect(surf, (8, 8, 8), (x, y, TILE_SIZE, TILE_SIZE))
            surf.blit(self.sprites[tile], (x, y))
        else:
            pygame.draw.rect(surf, (8, 8, 8), (x, y, TILE_SIZE, TILE_SIZE))
            text = self.font.render(tile, True, COLOR_WHITE)
            tx = x + (TILE_SIZE - text.get_width()) // 2
            ty = y + (TILE_SIZE - text.get_height()) // 2
            surf.blit(text, (tx, ty))

        if tile in (TILE_PLAYER, TILE_ENEMY):
            label_color = COLOR_BLUE if tile == TILE_PLAYER else COLOR_RED
            label = self.small_font.render(tile, True, label_color)
            pygame.draw.rect(surf, (0, 0, 0), (x + 1, y + 1, label.get_width() + 4, label.get_height() + 3))
            surf.blit(label, (x + 3, y + 2))

    def render_grid(self):
        level_map = self.get_current_map()
        self.screen.fill(COLOR_BG, (0, 0, self.editor_w, self.editor_viewport_h))

        for row_index, row in enumerate(level_map):
            for col_index, tile in enumerate(row):
                x = col_index * TILE_SIZE
                y = row_index * TILE_SIZE
                self.draw_tile(self.screen, tile, x, y)
                pygame.draw.rect(self.screen, COLOR_DARK_GRAY, (x, y, TILE_SIZE, TILE_SIZE), 1)

        cx = self.cursor_col * TILE_SIZE
        cy = self.cursor_row * TILE_SIZE
        pygame.draw.rect(self.screen, COLOR_YELLOW, (cx, cy, TILE_SIZE, TILE_SIZE), 3)

    def render_hud(self):
        hud_y = self.editor_viewport_h
        pygame.draw.rect(self.screen, (18, 18, 36), (0, hud_y, self.editor_w, EDITOR_HUD_HEIGHT))
        pygame.draw.line(self.screen, (70, 70, 100), (0, hud_y), (self.editor_w, hud_y), 2)

        dirty_mark = "*" if self.dirty else ""
        title = f"{self.get_current_screen().get('name', 'Level')} {dirty_mark}"
        level_text = self.font.render(
            f"Nivel {self.current_level + 1}/{len(self.screens)}  {VIEWPORT_COLS}x{VIEWPORT_ROWS}",
            True,
            COLOR_WHITE,
        )
        self.screen.blit(level_text, (8, hud_y + 6))

        title_text = self.font.render(title[:44], True, COLOR_GRAY)
        self.screen.blit(title_text, (360, hud_y + 6))

        pos_str = f"F:{self.cursor_row:02d} C:{self.cursor_col:02d}  "
        pos_text = self.font.render(pos_str, True, COLOR_WHITE)
        self.screen.blit(pos_text, (8, hud_y + 24))
        cursor_text = self.font.render(f"[{self.current_char()}] {self.current_tile_name()}", True, COLOR_GREEN)
        self.screen.blit(cursor_text, (8 + pos_text.get_width(), hud_y + 24))

        selected = TILE_TYPES[self.selected_tile]
        selected_text = self.font.render(f"Seleccionado [{selected[0]}] {selected[1]}", True, COLOR_YELLOW)
        self.screen.blit(selected_text, (360, hud_y + 24))

        palette_y = hud_y + 48
        preview_size = 24
        tile_spacing = 66
        for i, (char, name, color) in enumerate(TILE_TYPES):
            px = 18 + i * tile_spacing
            py = palette_y
            preview = pygame.Surface((preview_size, preview_size), pygame.SRCALPHA)
            if char in self.tiles:
                preview.blit(pygame.transform.scale(self.tiles[char], (preview_size, preview_size)), (0, 0))
            elif char in self.sprites:
                preview.fill((12, 12, 12))
                preview.blit(pygame.transform.scale(self.sprites[char], (preview_size, preview_size)), (0, 0))
            else:
                preview.fill(color)
            self.screen.blit(preview, (px, py))

            if i == self.selected_tile:
                pygame.draw.rect(self.screen, COLOR_YELLOW, (px - 2, py - 2, preview_size + 4, preview_size + 4), 2)
            else:
                pygame.draw.rect(self.screen, (75, 75, 90), (px - 1, py - 1, preview_size + 2, preview_size + 2), 1)

            key = self.small_font.render(KEY_LABELS[i], True, COLOR_YELLOW if i == self.selected_tile else COLOR_GRAY)
            self.screen.blit(key, (px + (preview_size - key.get_width()) // 2, py + preview_size + 4))

            label = self.hint_font.render(name[:8], True, COLOR_GRAY)
            self.screen.blit(label, (px - 10, py + preview_size + 18))

        hints = [
            "Flechas: mover  Shift/Espacio+mover: pintar  Espacio/Enter: poner  Tab: tile",
            "Ctrl+S: guardar  Ctrl+N: nuevo  Ctrl+Del: borrar nivel  PgUp/PgDn: nivel",
            "Ctrl+C/Ctrl+V: copiar/pegar mapa  Ctrl+B: vaciar  Esc: salir",
        ]
        for i, hint in enumerate(hints):
            text = self.hint_font.render(hint, True, COLOR_GRAY)
            self.screen.blit(text, (8, hud_y + 94 + i * 11))

        if self.saved_indicator > 0:
            save_text = self.font.render("Guardado!", True, COLOR_GREEN)
            self.screen.blit(save_text, (self.editor_w - save_text.get_width() - 8, hud_y + 94))

        if self.confirm_exit:
            self.render_dialog("Guardar cambios antes de salir?", "Y: guardar  N: salir  Esc: cancelar")
        elif self.confirm_delete_level:
            self.render_dialog("Eliminar nivel actual?", "Y: eliminar  N/Esc: cancelar")

    def render_dialog(self, message, hint):
        overlay = pygame.Surface((self.editor_w, self.editor_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        msg_text = self.font.render(message, True, COLOR_YELLOW)
        hint_text = self.small_font.render(hint, True, COLOR_WHITE)
        msg_rect = msg_text.get_rect(center=(self.editor_w // 2, self.editor_h // 2 - 16))
        hint_rect = hint_text.get_rect(center=(self.editor_w // 2, self.editor_h // 2 + 16))
        self.screen.blit(msg_text, msg_rect)
        self.screen.blit(hint_text, hint_rect)

    def render(self):
        self.render_grid()
        self.render_hud()
        if EDITOR_SCALE == 1:
            self.display.blit(self.screen, (0, 0))
        else:
            pygame.transform.scale(self.screen, self.display.get_size(), self.display)
        pygame.display.flip()

    def handle_keydown(self, event):
        mods = pygame.key.get_mods()
        shift = mods & pygame.KMOD_SHIFT
        ctrl = mods & pygame.KMOD_CTRL
        keys = pygame.key.get_pressed()

        if self.confirm_exit:
            if event.key == pygame.K_y:
                self.save()
                return False
            if event.key == pygame.K_n:
                return False
            if event.key == pygame.K_ESCAPE:
                self.confirm_exit = False
            return True

        if self.confirm_delete_level:
            if event.key == pygame.K_y:
                self.delete_current_level()
            self.confirm_delete_level = False
            return True

        if event.key == pygame.K_ESCAPE:
            if self.dirty:
                self.confirm_exit = True
            else:
                return False

        elif event.key == pygame.K_s and ctrl:
            self.save()

        elif event.key == pygame.K_n and ctrl:
            self.new_level()

        elif event.key == pygame.K_DELETE and ctrl:
            if len(self.screens) > 1:
                self.confirm_delete_level = True

        elif event.key == pygame.K_c and ctrl:
            self.copy_map_to_clipboard()

        elif event.key == pygame.K_v and ctrl:
            self.paste_map_from_clipboard()

        elif event.key == pygame.K_b and ctrl:
            self.fill_current_level(TILE_AIR)

        elif event.key == pygame.K_PAGEUP:
            self.change_level(-1)

        elif event.key == pygame.K_PAGEDOWN:
            self.change_level(1)

        elif event.key == pygame.K_TAB:
            if shift:
                self.selected_tile = (self.selected_tile - 1) % len(TILE_TYPES)
            else:
                self.selected_tile = (self.selected_tile + 1) % len(TILE_TYPES)

        elif pygame.K_1 <= event.key <= pygame.K_8:
            self.selected_tile = event.key - pygame.K_1

        elif event.key == pygame.K_UP:
            self.cursor_row = max(0, self.cursor_row - 1)
            if shift or keys[pygame.K_SPACE]:
                self.set_tile(self.cursor_row, self.cursor_col, self.selected_char())

        elif event.key == pygame.K_DOWN:
            self.cursor_row = min(VIEWPORT_ROWS - 1, self.cursor_row + 1)
            if shift or keys[pygame.K_SPACE]:
                self.set_tile(self.cursor_row, self.cursor_col, self.selected_char())

        elif event.key == pygame.K_LEFT:
            self.cursor_col = max(0, self.cursor_col - 1)
            if shift or keys[pygame.K_SPACE]:
                self.set_tile(self.cursor_row, self.cursor_col, self.selected_char())

        elif event.key == pygame.K_RIGHT:
            self.cursor_col = min(VIEWPORT_COLS - 1, self.cursor_col + 1)
            if shift or keys[pygame.K_SPACE]:
                self.set_tile(self.cursor_row, self.cursor_col, self.selected_char())

        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.set_tile(self.cursor_row, self.cursor_col, self.selected_char())

        return True

    def run(self):
        running = True
        pygame.key.set_repeat(180, 60)

        while running:
            dt = self.clock.tick(FPS) / 1000.0
            if self.saved_indicator > 0:
                self.saved_indicator -= dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.dirty:
                        self.confirm_exit = True
                    else:
                        running = False
                elif event.type == pygame.KEYDOWN:
                    running = self.handle_keydown(event)

            self.render()

        pygame.quit()


if __name__ == "__main__":
    editor = Editor()
    editor.run()
