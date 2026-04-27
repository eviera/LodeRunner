"""Genera sprites y tiles placeholder para Lode Runner.
Ejecutar una vez para crear los archivos PNG de prueba.
Reemplazar con arte real cuando esté listo.
"""

import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
pygame.init()
pygame.display.set_mode((1, 1), pygame.NOFRAME)

T = 32  # TILE_SIZE

def save(surf, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pygame.image.save(surf, path)
    print(f"  {path}")


def make_surface(w=T, h=T, alpha=False):
    flags = pygame.SRCALPHA if alpha else 0
    s = pygame.Surface((w, h), flags)
    if not alpha:
        s.fill((0, 0, 0))
    return s


# ---------- TILES ----------

def make_brick(color_main, color_mortar):
    s = make_surface()
    s.fill(color_main)
    # Filas de ladrillos (mortar horizontal)
    for y in [10, 21]:
        pygame.draw.line(s, color_mortar, (0, y), (T - 1, y), 1)
    # Junta vertical escalonada
    for row, x_offset in [(0, 16), (11, 8), (22, 16)]:
        end_y = min(row + 10, T - 1)
        pygame.draw.line(s, color_mortar, (x_offset, row), (x_offset, end_y), 1)
    return s


def make_ladder():
    s = make_surface(alpha=True)
    c = (220, 220, 220)
    # Rieles verticales
    pygame.draw.rect(s, c, (8, 0, 3, T))
    pygame.draw.rect(s, c, (21, 0, 3, T))
    # Peldaños
    for y in range(3, T, 8):
        pygame.draw.rect(s, c, (8, y, 16, 2))
    return s


def make_gold():
    s = make_surface(alpha=True)
    cx, cy = T // 2, T // 2
    pygame.draw.circle(s, (255, 200, 50), (cx, cy), 9)
    pygame.draw.circle(s, (200, 140, 0), (cx, cy), 6)
    pygame.draw.circle(s, (255, 230, 100), (cx - 3, cy - 3), 3)
    return s


def make_handrail():
    s = make_surface(alpha=True)
    mid = T // 2
    pygame.draw.rect(s, (220, 220, 220), (0, mid - 2, T, 4))
    return s


# ---------- SPRITES ----------

def px(s, color, rect):
    pygame.draw.rect(s, color, rect)


def limb(s, color, start, end, width=3):
    pygame.draw.line(s, color, start, end, width)


def make_lode_sprite(pose):
    """Sprite 32x32 estilo C64, mirando a la izquierda.

    El juego espeja horizontalmente este arte para correr hacia la derecha.
    """
    s = make_surface(alpha=True)
    c = (255, 255, 255)

    def head(x, y):
        px(s, c, (x + 1, y, 4, 2))
        px(s, c, (x, y + 2, 6, 5))
        px(s, c, (x + 1, y + 7, 4, 2))

    if pose == "idle":
        head(14, 4)
        limb(s, c, (17, 12), (17, 21))      # torso
        limb(s, c, (16, 14), (11, 18), 2)
        limb(s, c, (18, 14), (23, 17), 2)
        limb(s, c, (16, 21), (12, 29), 2)
        limb(s, c, (18, 21), (23, 29), 2)

    elif pose == "run_1":
        head(14, 4)
        limb(s, c, (17, 12), (16, 21))
        limb(s, c, (16, 14), (9, 17), 2)    # brazo adelante
        limb(s, c, (18, 14), (23, 12), 2)
        limb(s, c, (16, 21), (9, 25), 2)    # pierna adelante
        limb(s, c, (17, 21), (23, 29), 2)   # pierna atras

    elif pose == "run_2":
        head(15, 3)
        limb(s, c, (18, 11), (18, 20))
        limb(s, c, (17, 13), (11, 15), 2)
        limb(s, c, (19, 13), (24, 16), 2)
        limb(s, c, (17, 20), (13, 28), 2)
        limb(s, c, (19, 20), (23, 28), 2)

    elif pose == "run_3":
        head(14, 4)
        limb(s, c, (17, 12), (18, 21))
        limb(s, c, (16, 14), (11, 12), 2)
        limb(s, c, (18, 14), (25, 17), 2)   # brazo adelante
        limb(s, c, (17, 21), (12, 29), 2)   # pierna atras
        limb(s, c, (18, 21), (25, 25), 2)   # pierna adelante

    elif pose == "fall":
        head(14, 10)
        limb(s, c, (17, 18), (17, 25))
        limb(s, c, (15, 18), (10, 12), 3)   # brazos arriba
        limb(s, c, (19, 18), (24, 12), 3)
        limb(s, c, (16, 25), (13, 30), 2)
        limb(s, c, (18, 25), (22, 30), 2)
    else:
        raise ValueError(f"Pose desconocida: {pose}")

    return s


print("Generando assets...")

save(make_brick((142, 58, 34), (80, 30, 10)),  "tiles/brick.png")
save(make_brick((100, 35, 15), (50, 15, 5)),   "tiles/solid_brick.png")
save(make_ladder(),                             "tiles/ladder.png")
save(make_gold(),                               "tiles/gold.png")
save(make_handrail(),                           "tiles/handrail.png")

idle = make_lode_sprite("idle")
save(idle, "sprites/lode_idle.png")
save(make_lode_sprite("run_1"), "sprites/lode_run_1.png")
save(make_lode_sprite("run_2"), "sprites/lode_run_2.png")
save(make_lode_sprite("run_3"), "sprites/lode_run_3.png")
save(make_lode_sprite("fall"),  "sprites/lode_fall.png")

# Compatibilidad con el loader anterior y con herramientas que esperen estos nombres.
save(idle, "sprites/player.png")
save(idle, "sprites/enemy.png")

print("Listo.")
pygame.quit()
