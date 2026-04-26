"""Genera sprites y tiles placeholder para Lode Runner.
Ejecutar una vez para crear los archivos PNG de prueba.
Reemplazar con arte real cuando esté listo.
"""

import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

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

def make_stick_figure(body_color, bg_alpha=True):
    s = make_surface(alpha=bg_alpha)
    c = body_color
    # Cabeza
    pygame.draw.circle(s, c, (16, 7), 5)
    # Cuello + torso
    pygame.draw.line(s, c, (16, 12), (16, 22), 2)
    # Brazos
    pygame.draw.line(s, c, (16, 15), (8, 20), 2)
    pygame.draw.line(s, c, (16, 15), (24, 20), 2)
    # Piernas
    pygame.draw.line(s, c, (16, 22), (10, 31), 2)
    pygame.draw.line(s, c, (16, 22), (22, 31), 2)
    return s


print("Generando assets...")

save(make_brick((142, 58, 34), (80, 30, 10)),  "tiles/brick.png")
save(make_brick((100, 35, 15), (50, 15, 5)),   "tiles/solid_brick.png")
save(make_ladder(),                             "tiles/ladder.png")
save(make_gold(),                               "tiles/gold.png")
save(make_handrail(),                           "tiles/handrail.png")

save(make_stick_figure((255, 255, 255)), "sprites/player.png")
save(make_stick_figure((91, 163, 160)),  "sprites/enemy.png")

print("Listo.")
pygame.quit()
