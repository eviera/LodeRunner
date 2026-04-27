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

`editor.py` todavia es placeholder.

## Estructura

- `main.py`: entry point; crea `Game`, llama `init()` y `run()`.
- `game.py`: clase principal `Game`; carga assets/niveles, loop, estados, render, HUD, digging, gold, vidas y colisiones.
- `player.py`: `Player(PhysicsEntity)`; movimiento, escalera, handrail, gravedad, colisiones y digging.
- `enemy.py`: `Enemy(PhysicsEntity)`; AI simple, movimiento, escaleras, handrails y hoyos.
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
- Player camina, sube/baja escaleras, se mueve por handrails y cae por gravedad.
- No hay salto.
- Digging solo cuando el player esta en el suelo y el tile adyacente a nivel de pies es `B`.
- Los hoyos duran `HOLE_FILL_TIME` y luego restauran `TILE_BRICK`.
- Un enemigo dentro de un hoyo que se cierra queda inactivo y suma score.
- El player dentro de un hoyo que se cierra entra en estado de muerte.
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
- `HOLE_FILL_TIME`

## Convenciones de cambios

- Mantener archivos Python separados por responsabilidad.
- Centralizar constantes nuevas en `constants.py`.
- Mantener `screens.json` como fuente de niveles; preservar ancho 32 y alto 18 cuando se edite manualmente.
- No reemplazar cambios locales existentes sin revisar `git status`; actualmente `screens.json` puede tener cambios del usuario.
- Preferir cambios chicos y directos antes que refactors grandes.
- El arte actual es placeholder; no asumir que los sprites finales tendran mas de 32x32 salvo que se cambie la logica.
- Player y enemies comparten por ahora los mismos frames `lode_*`; el espejado izquierda/derecha se hace en memoria con `pygame.transform.flip`.
- Si se modifica fisica/colisiones, revisar tanto `player.py` como `enemy.py`, porque tienen logica similar.
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
