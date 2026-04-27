# Lode Runner — Documentación del Proyecto

## Descripción
Clon de Lode Runner (Commodore 64, 1983) en Python usando el motor evgamelib.
Motor en `~/workspace/evgamelib`. Referencia: `~/workspace/HERO`.

## Cómo correr

```bash
cd ~/workspace/LodeRunner
python -m venv venv
source venv/bin/activate
pip install pygame
pip install -e ~/workspace/evgamelib
python make_assets.py   # generar sprites placeholder (primera vez)
python main.py
```

## Estructura de archivos

| Archivo | Descripción |
|---------|-------------|
| `main.py` | Entry point |
| `game.py` | Clase `Game`: loop, estados, render, HUD |
| `player.py` | `Player(PhysicsEntity)`: movimiento, escaleras, digging |
| `enemy.py` | `Enemy(PhysicsEntity)`: AI simple, escaleras, hoyos |
| `constants.py` | Todas las constantes del juego |
| `editor.py` | Editor de niveles (pendiente) |
| `make_assets.py` | Genera sprites/tiles placeholder y frames de animación |
| `screens.json` | Datos de niveles |
| `sprites/` | lode_idle.png, lode_run_1.png, lode_run_2.png, lode_run_3.png, lode_fall.png; player.png y enemy.png quedan como compatibilidad |
| `tiles/` | brick.png, solid_brick.png, ladder.png, gold.png, handrail.png |
| `sounds/` | Efectos de sonido (pendiente) |
| `fonts/` | PressStart2P-vaV7.ttf |

## Leyenda de tiles en screens.json

| Char | Tile | Descripción |
|------|------|-------------|
| `#` | Solid Brick | Ladrillo irrompible (borde, piso sólido) |
| `B` | Brick | Ladrillo rompible (diggable) |
| `H` | Ladder | Escalera (sube/baja) |
| `-` | Handrail | Barra de mano horizontal (se cuelga) |
| `G` | Gold | Oro para recolectar |
| `P` | Player Start | Spawn del jugador |
| `E` | Enemy Start | Spawn de enemigo |
| ` ` | Air | Espacio vacío |

## Controles

| Tecla | Acción |
|-------|--------|
| ← / → | Mover izquierda / derecha |
| ↑ / ↓ | Subir / bajar por escaleras; colgarse de handrails |
| `Z` | Cavar a la izquierda |
| `X` | Cavar a la derecha |
| `F11` | Fullscreen toggle |
| `ESC` | Salir |
| `ENTER` | Reiniciar (desde Game Over) |

## Mecánicas

**Movimiento:**
- Player se mueve izq/der sobre plataformas sólidas
- Sube/baja escaleras (`H`) con ↑/↓
- Se cuelga y mueve en barras horizontales (`-`)
- Gravedad aplica cuando no está en escalera ni barra
- No puede saltar

**Digging:**
- `Z` / `X` cavan el ladrillo (`B`) a nivel de los pies del player
- El hoyo dura `HOLE_FILL_TIME` segundos (8s por defecto)
- Hoyo se llena automáticamente → ladrillo restaurado
- Enemy en hoyo cuando se llena → muere
- Player en hoyo cuando se llena → pierde vida

**Enemigos:**
- Persiguen al player horizontalmente
- Usan escaleras para cambiar de nivel
- Se quedan atrapados en hoyos (`in_hole=True`)
- Velocidad: 72px/s (vs player: 120px/s)

**Condición de victoria:**
- Recolectar todo el oro (`G`) → level complete

**Condición de derrota:**
- Contacto con enemy → pierde vida
- Quedar atrapado en hoyo que se llena → pierde vida
- Sin vidas → Game Over

## Estados del juego

| Estado | Descripción |
|--------|-------------|
| `STATE_PLAYING` | Gameplay normal |
| `STATE_DYING` | Flash del player, 1.8s |
| `STATE_LEVEL_COMPLETE` | Pausa 2s, carga siguiente nivel |
| `STATE_GAME_OVER` | Pantalla final |

## Resolución

- Game surface: 1024 × 576 px (32 × 18 tiles de 32px)
- Viewport escalado: 768 × 432 px (escala 0.75×)
- Screen con HUD: 768 × 464 px
- HUD: 32px de alto (dos barras ladrillo + texto naranja)
- Fullscreen: letterboxed aspect ratio

## TODO

- [ ] Sonidos: dig, gold collect, death, level complete, background music
- [ ] Sprites reales: player.png, enemy.png (arte pixel del usuario)
- [ ] Tiles reales: brick.png, etc.
- [ ] Intro/splash screen
- [ ] Más niveles en screens.json
- [ ] Editor de niveles (editor.py)
- [ ] High scores (evgamelib.scores)
- [ ] Animación de muerte del enemy (flash)
- [ ] Mejoras de AI: pathfinding más inteligente
- [ ] Hand bars: mecánica de colgarse más refinada
