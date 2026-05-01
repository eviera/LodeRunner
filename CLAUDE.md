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

Argumentos utiles:

```bash
python main.py --level=2
python main.py --level=2 --test
```

`--test` es un modo temporal de debug: si el player esta dentro de un pozo abierto, flecha arriba lo saca hacia el lado libre.

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
- No se puede cavar si justo arriba del ladrillo objetivo hay una escalera (`H`)
- El hoyo dura `HOLE_FILL_TIME_MS` milisegundos (`HOLE_FILL_TIME` en segundos para el loop)
- Hoyo se llena automáticamente → ladrillo restaurado
- Enemy que pasa sobre un hoyo cae y queda atrapado, aunque debajo del hoyo haya aire; se detecta por pies/centro sobre el tile del pozo
- La entrada al pozo se anima con gravedad; `hole_settled` indica cuando ya llegó al tile del pozo y recién ahí corre el timer de escape
- Enemy atrapado puede escapar antes del cierre despues de `ENEMY_HOLE_ESCAPE_TIME_MS`; sale a un tile lateral valido sobre piso si existe
- Enemy cayendo dentro de un pozo todavía mata al player si lo toca por máscara pixel-perfect; solo deja de matar cuando `hole_settled=True`
- Enemy en hoyo cuando se llena → suma score y reaparece aleatoriamente sobre un piso valido
- Player en hoyo cuando se llena → pierde vida
- Player atraviesa el hoyo si debajo hay aire; solo muere si sigue dentro cuando el hoyo se cierra
- Player cae al pozo solo por mascara pixel-perfect de los pixeles visibles del Lode en la zona de pies (`PLAYER_HOLE_FALL_OVERLAP` sobre `PLAYER_HOLE_FOOT_BAND_HEIGHT`); no usar overlap del rectangulo/tile completo ni columna central para decidir caida

**Enemigos:**
- Persiguen al player con pathfinding sobre la grilla del nivel
- Usan escaleras, plataformas, barras y caídas para cambiar de nivel
- Cada enemy tiene variaciones de inteligencia, velocidad, recálculo y elección de ruta
- Si enemy y player quedan en la misma columna lógica de la grilla, el enemy sigue acercándose por posición real hasta tocar los píxeles del Lode; no debe frenarse solo por estar en el mismo tile
- Si un enemy queda quieto fuera de un pozo más de `ENEMY_IDLE_UNSTUCK_TIME`, o intenta moverse pero no avanza más de `ENEMY_STUCK_TIME`, entra por `ENEMY_UNSTUCK_TIME` en un movimiento corto de desatasco
- Si un enemy sale horizontalmente de una escalera hacia aire sin soporte, cae por gravedad; solo se sostiene en escalera cuando no está saliendo horizontalmente
- Se quedan atrapados en hoyos (`in_hole=True`)
- Velocidad: 72px/s (vs player: 120px/s)

**Colisiones:**
- Player y enemies miden 1 tile, pero los sprites `lode_*` tienen alpha transparente amplio dentro de 32x32
- La muerte por enemy usa máscaras pixel-perfect de los sprites visibles
- Todas las colisiones sensibles con sprites visibles deben ser pixel-perfect; player-enemy y player-hoyos usan pixeles visibles/mascaras, no rectangulos completos del tile
- Si un enemy queda cerca sin matar al player, revisar primero la IA/quietud del enemy en `enemy.py`; no agrandar hitboxes para resolver ese caso

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
- [x] Mejoras de AI: pathfinding más inteligente
- [ ] Hand bars: mecánica de colgarse más refinada

## Notas para agentes

- `constants.py` es la fuente de verdad para resolución, física, timers de pozos y timers de desatasco de enemigos.
- Si se verifica sintaxis en sandbox, usar `PYTHONPYCACHEPREFIX=/tmp/loderunner-pycache venv/bin/python -m py_compile ...` para no escribir `.pyc` en `~/Library/Caches`.
- Antes de tocar física/colisiones, revisar `player.py`, `enemy.py` y `game.py`; la detección de estados y la resolución de colisiones están repartidas entre esos archivos.
