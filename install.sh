#!/bin/bash
echo "=== Lode Runner - Instalacion de dependencias (Mac) ==="
echo

python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "ERROR: No se encontro Python 3. Instala con: brew install python3"
    exit 1
fi

source venv/bin/activate

pip install pygame
pip install -e ~/workspace/evgamelib

echo
echo "Generando assets..."
python make_assets.py

echo
echo "=== Instalacion completa! Usa: source venv/bin/activate && python main.py ==="
