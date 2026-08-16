#!/usr/bin/env sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$PROJECT_ROOT"

if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="${PYTHON:-python3}"
fi

"$PYTHON" -c "import fastapi, uvicorn, xlrd" || {
    echo "Missing dependencies. Run: python -m pip install -r requirements.txt" >&2
    exit 2
}

exec "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
