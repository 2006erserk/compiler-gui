#!/usr/bin/env bash
# Сборка автономного исполняемого файла для Linux с помощью PyInstaller.
# Результат: dist/go-complex-editor (один файл, Python на целевом компьютере не нужен).
set -euo pipefail
cd "$(dirname "$0")"

VENV=.venv-build

if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r requirements-build.txt

"$VENV/bin/pyinstaller" \
    --noconfirm \
    --clean \
    --onefile \
    --windowed \
    --name go-complex-editor \
    main.py

echo
echo "Готово: $(pwd)/dist/go-complex-editor"
echo "Запуск: ./dist/go-complex-editor"
