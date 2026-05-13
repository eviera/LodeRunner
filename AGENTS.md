# Lode Runner - Guia para agentes

## Contexto

Este repo es un clon inicial de Lode Runner estilo Commodore 64, escrito en Python con Pygame y el motor local `evgamelib`.

- Motor local: `~/workspace/evgamelib`
- Proyecto de referencia del mismo autor/motor: `~/workspace/HERO`
- Documentacion historica del trabajo con Claude: `CLAUDE.md`
- Pendientes de producto/prompts: `todo.txt`

El objetivo actual es mantener el juego simple y modular, con una pantalla fija por nivel, sin scroll entre viewports.

## Como correr

```bash
cd ~/workspace/LodeRunner
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e ~/workspace/evgamelib
python make_assets.py
python main.py
```

Tambien existen wrappers:

```bash
./lode.sh
./editor.sh
```

Argumentos utiles:

```bash
./lode.sh --level=2
./lode.sh --level=2 --test
```

`--test` es un modo temporal de debug: si el player esta dentro de un pozo abierto, flecha arriba lo saca hacia el lado libre.

`editor.py` todavia es placeholder.

## Estructura

- `main.py`: entry point; crea `Game`, llama `init()` y `run()`.
- `game.py`: clase principal `Game`; carga assets/niveles, loop, estados, render, HUD, digging, gold, vidas y colisiones.
- `player.py`: `Player(PhysicsEntity)`; movimiento, escalera, handrail, gravedad, colisiones y digging.
- `enemy.py`: `Enemy(PhysicsEntity)`; pathfinding sobre grilla, movimiento, escaleras, handrails y hoyos.
- `constants.py`: constantes de resolucion, fisica, tiles, colores, scoring y archivos.
- `make_assets.py`: genera assets placeholder PNG de 32x32, incluyendo frames pixel de Lode.
- `screens.json`: niveles.
- `sprites/`: frames nuevos `lode_idle.png`, `lode_run_1.png`, `lode_run_2.png`, `lode_run_3.png`, `lode_fall.png`; `player.png` y `enemy.png` quedan como compatibilidad.
- `tiles/`: `brick.png`, `solid_brick.png`, `ladder.png`, `gold.png`, `handrail.png`.
- `fonts/`: fuente pixel `PressStart2P-vaV7.ttf`.

## Estado real del juego

El codigo actual usa tiles de 32 px y niveles de 32 columnas x 18 filas:

- `TILE_SIZE = 32`
- `VIEWPORT_COLS = 32`
- `VIEWPORT_ROWS = 18`
- `GAME_WIDTH = 1024`
- `GAME_VIEWPORT_HEIGHT = 576`
- `RENDER_SCALE = 0.75`
- pantalla final: `768 x 464`, incluyendo `HUD_HEIGHT = 32`

Nota: `CLAUDE.md` menciona una resolucion anterior de 16x8 / 512x256. Para cambios nuevos, priorizar `constants.py` como fuente de verdad.

## Formato de niveles

`screens.json` contiene una lista de pantallas. Cada pantalla usa un campo `map` con filas de texto. `Game._normalize_map()` recorta o completa a 32x18.

Leyenda:

- `#`: ladrillo solido irrompible
- `B`: ladrillo rompible/cavable
- `H`: escalera
- `-`: handrail/barra horizontal
- `G`: oro
- `P`: spawn del player
- `E`: spawn de enemigo
- espacio: aire

Al iniciar nivel, `P` y `E` se reemplazan por aire y se crean entidades.

## Dependencias y motor

El proyecto depende de:

- `pygame>=2.5.0`
- `evgamelib`, instalado editable desde `~/workspace/evgamelib`

Imports relevantes de `evgamelib`:

- `evgamelib.rendering.RenderPipeline`
- `evgamelib.input_manager.InputManager`
- `evgamelib.sound_manager.SoundManager`
- `evgamelib.text.draw_text_with_outline`
- `evgamelib.entity.PhysicsEntity`
- estados y defaults desde `evgamelib.constants`

Si hace falta entender patrones de editor, fullscreen o pipeline, revisar primero `~/workspace/HERO`.

## Controles

- Flechas izquierda/derecha: mover.
- Flechas arriba/abajo: escaleras y handrails.
- `Z`: cavar izquierda.
- `X`: cavar derecha.
- `F11`: toggle fullscreen.
- `ESC`: salir.
- `ENTER` o `R`: reiniciar desde Game Over.

## Mecanicas implementadas

- Player y enemigos miden 1 tile.
- El contacto player-enemy debe ser pixel-perfect con máscaras de los sprites visibles; si no muere, el problema esperado suele estar en la IA/enemigo quieto, no en agrandar la colisión.
- Player camina, sube/baja escaleras, se mueve por handrails y cae por gravedad.
- Enemigos persiguen al player con pathfinding sobre tiles y tienen variaciones de inteligencia/velocidad por instancia.
- Cuando enemy y player caen en la misma columna lógica de grilla, el enemy debe seguir acercándose por posición real hasta tocar los píxeles del Lode; no debe frenar solo porque ambos centros estén en el mismo tile.
- Si un enemy queda quieto fuera de un pozo más de `ENEMY_IDLE_UNSTUCK_TIME`, o intenta moverse pero no avanza más de `ENEMY_STUCK_TIME`, entra en un modo corto de desatasco (`ENEMY_UNSTUCK_TIME`) con movimiento alternativo/aleatorio.
- No hay salto.
- Digging con `Z`/`X` cava izquierda/derecha solo cuando el player esta en el suelo y el tile adyacente a nivel de pies es `B`.
- No se puede cavar un ladrillo si justo arriba de ese ladrillo hay una escalera (`H`).
- Los hoyos duran `HOLE_FILL_TIME_MS` milisegundos (`HOLE_FILL_TIME` en segundos para el loop) y luego restauran `TILE_BRICK`.
- Si los pies/centro de un enemy pasan sobre un hoyo, cae y queda atrapado aunque debajo del hoyo haya aire; no esperar a que todo el sprite entre en el tile del pozo.
- La entrada del enemy al pozo debe verse como caída: `in_hole=True` puede empezar antes de quedar asentado, pero no debe teletransportar `x/y`; usar `hole_settled` para iniciar el timer de escape solo al llegar al tile del pozo.
- Si un enemy sale horizontalmente de una escalera hacia aire sin soporte, debe dejar de sostenerse por la escalera y caer por gravedad.
- Un enemy atrapado puede escapar antes del cierre despues de `ENEMY_HOLE_ESCAPE_TIME_MS`; intenta salir a un tile lateral valido sobre piso.
- Un enemy que esta cayendo dentro de un pozo todavia mata al player por máscara pixel-perfect si lo toca; solo deja de matar cuando ya esta asentado (`hole_settled=True`) y atrapado.
- Un pozo con enemy ya asentado (`hole_settled=True`) funciona como soporte para el player: Lode puede pasar por arriba sin caer, lo que permite escapar.
- Un enemigo dentro de un hoyo que se cierra suma score y reaparece aleatoriamente sobre un piso valido.
- El player dentro de un hoyo que se cierra entra en estado de muerte.
- Si debajo del hoyo hay aire, el player atraviesa el hoyo y sigue cayendo; solo muere si sigue dentro cuando el hoyo se cierra.
- El player cae al pozo solo por mascara pixel-perfect de los pixeles visibles del Lode en la zona de pies (`PLAYER_HOLE_FALL_OVERLAP` sobre `PLAYER_HOLE_FOOT_BAND_HEIGHT`); no usar overlap del rectangulo/tile completo ni columna central para decidir caida.
- Contacto con enemigo fuera de hoyo causa muerte.
- Al recolectar todo el oro, se completa el nivel y se avanza al siguiente.
- Cuando se termina la lista de niveles, vuelve al nivel 0.

## Estados

Estados importados desde `evgamelib.constants`:

- `STATE_PLAYING`
- `STATE_DYING`
- `STATE_LEVEL_COMPLETE`
- `STATE_GAME_OVER`

Timers locales:

- `DYING_FLASH_TIME`
- `LEVEL_COMPLETE_DELAY`
- `HOLE_FILL_TIME_MS` / `HOLE_FILL_TIME`
- `ENEMY_HOLE_ESCAPE_TIME_MS` / `ENEMY_HOLE_ESCAPE_TIME`

## Convenciones de cambios

- Mantener archivos Python separados por responsabilidad.
- Centralizar constantes nuevas en `constants.py`.
- Mantener `screens.json` como fuente de niveles; preservar ancho 32 y alto 18 cuando se edite manualmente.
- No reemplazar cambios locales existentes sin revisar `git status`; actualmente `screens.json` puede tener cambios del usuario.
- Preferir cambios chicos y directos antes que refactors grandes.
- El arte actual es placeholder; no asumir que los sprites finales tendran mas de 32x32 salvo que se cambie la logica.
- Player y enemies comparten por ahora los mismos frames `lode_*`; el espejado izquierda/derecha se hace en memoria con `pygame.transform.flip`.
- Todas las colisiones sensibles con sprites visibles deben ser pixel-perfect. Para player-enemy y player-hoyos, mantener mascaras/pixeles visibles; no agrandar hitboxes ni usar el rectangulo completo del tile como sustituto.
- Si se modifica fisica/colisiones, revisar tanto `player.py` como `enemy.py`, porque tienen logica similar.
- Si se corre `py_compile` en sandbox, usar `PYTHONPYCACHEPREFIX=/tmp/loderunner-pycache` para evitar writes a `~/Library/Caches`.
- Si se agrega CLI o configuracion de arranque, hacerlo desde `main.py` y pasar opciones a `Game` sin mezclar parseo de argumentos dentro del loop.

## Pendientes conocidos

Segun `todo.txt` y `CLAUDE.md`, pendientes inmediatos:

- Agregar prompt/pantalla inicial.
- Poder arrancar en cualquier nivel con `--level=N`.
- Sonidos: cavar, oro, muerte, completar nivel y musica.
- Sprites y tiles finales.
- Intro/splash screen.
- Mas niveles en `screens.json`.
- Implementar `editor.py`.
- High scores con `evgamelib.scores`.
- Animacion de muerte de enemigo.
- Mejorar AI/pathfinding.
- Refinar mecanica de handrails.
