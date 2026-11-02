#!/usr/bin/env bash
# Epic Estimation System - levanta backend (FastAPI) y frontend (Next.js)
# en local con una sola instrucción.
#
# Uso:
#   ./start.sh          -> instala dependencias si faltan, entrena modelos
#                           si no existen, y levanta ambos servicios.
#   ./start.sh stop     -> detiene los servicios levantados por este script.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUN_DIR="$ROOT_DIR/.run"
PORTS_FILE="$RUN_DIR/ports.env"
BACKEND_LOG="$RUN_DIR/backend.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"

mkdir -p "$RUN_DIR"

is_port_free() {
  ! lsof -iTCP:"$1" -sTCP:LISTEN -n -P >/dev/null 2>&1
}

find_free_port() {
  local port=$1
  while ! is_port_free "$port"; do
    port=$((port + 1))
  done
  echo "$port"
}

# Solo procesos que corren dentro de este repositorio: el mismo puerto puede
# estar ocupado por Docker (docker compose) u otro proyecto
owned_by_repo() {
  local cwd
  cwd=$(lsof -a -p "$1" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
  case "$cwd" in
    "$ROOT_DIR" | "$ROOT_DIR"/*) return 0 ;;
    *) return 1 ;;
  esac
}

kill_port() {
  local port=$1
  local pids
  pids=$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true)
  for pid in $pids; do
    if owned_by_repo "$pid"; then
      echo "  -> deteniendo PID $pid en puerto $port ($(ps -p "$pid" -o comm= 2>/dev/null))"
      kill "$pid" 2>/dev/null || true
    else
      echo "  -> se omite PID $pid en puerto $port ($(ps -p "$pid" -o comm= 2>/dev/null)): no fue lanzado desde este repositorio"
    fi
  done
}

stop_services() {
  if [ -f "$PORTS_FILE" ]; then
    # shellcheck disable=SC1090
    source "$PORTS_FILE"
    echo "Deteniendo backend (puerto ${BACKEND_PORT:-8000})..."
    kill_port "${BACKEND_PORT:-8000}"
    echo "Deteniendo frontend (puerto ${FRONTEND_PORT:-3000})..."
    kill_port "${FRONTEND_PORT:-3000}"
    rm -f "$PORTS_FILE"
  else
    echo "No hay registro de servicios levantados por start.sh (nada que detener)."
  fi
}

if [ "${1:-}" = "stop" ]; then
  stop_services
  exit 0
fi

echo "=== Epic Estimation System - levantando entorno local ==="

# --- Backend: entorno virtual y dependencias ---
cd "$BACKEND_DIR"
if [ ! -d venv ]; then
  echo "[backend] Creando entorno virtual..."
  python3 -m venv venv
fi
echo "[backend] Instalando dependencias..."
./venv/bin/pip install -q -r requirements.txt

# --- Backend: entrenar modelos si no existen ---
if [ ! -f trained_models/models.pkl ]; then
  if [ -f "$ROOT_DIR/Jira (3).csv" ]; then
    echo "[backend] No hay modelos entrenados. Entrenando con 'Jira (3).csv'..."
    ./venv/bin/python -c "
from pathlib import Path
from app.main import train_models_from_csv
train_models_from_csv(Path('../Jira (3).csv'))
"
  else
    echo "[backend] AVISO: no hay modelos entrenados ni 'Jira (3).csv' en la raíz para entrenarlos."
    echo "[backend]        El backend arrancará, pero /estimate/* fallará hasta entrenar (ver /train)."
  fi
fi

# --- Elegir puertos libres (evita choques con otros proyectos corriendo) ---
BACKEND_PORT=$(find_free_port "${BACKEND_PORT:-8000}")
FRONTEND_PORT=$(find_free_port "${FRONTEND_PORT:-3000}")
echo "BACKEND_PORT=$BACKEND_PORT" > "$PORTS_FILE"
echo "FRONTEND_PORT=$FRONTEND_PORT" >> "$PORTS_FILE"

# --- Levantar backend ---
echo "[backend] Iniciando en puerto $BACKEND_PORT..."
nohup ./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload \
  > "$BACKEND_LOG" 2>&1 &
disown

for _ in $(seq 1 30); do
  if curl -sf "http://localhost:$BACKEND_PORT/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! curl -sf "http://localhost:$BACKEND_PORT/health" >/dev/null 2>&1; then
  echo "[backend] ERROR: no respondió a tiempo. Revisa $BACKEND_LOG"
  exit 1
fi
echo "[backend] Listo -> http://localhost:$BACKEND_PORT"

# --- Frontend: dependencias ---
cd "$FRONTEND_DIR"
if [ ! -d node_modules ]; then
  echo "[frontend] Instalando dependencias npm..."
  npm install
fi

# --- Levantar frontend, apuntando al backend recién levantado ---
echo "[frontend] Iniciando en puerto $FRONTEND_PORT..."
NEXT_PUBLIC_API_URL="http://localhost:$BACKEND_PORT" \
  nohup npm run dev -- -p "$FRONTEND_PORT" > "$FRONTEND_LOG" 2>&1 &
disown

for _ in $(seq 1 30); do
  if curl -sf "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! curl -sf "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
  echo "[frontend] ERROR: no respondió a tiempo. Revisa $FRONTEND_LOG"
  exit 1
fi

echo ""
echo "========================================"
echo "  Backend:  http://localhost:$BACKEND_PORT  (docs: /docs)"
echo "  Frontend: http://localhost:$FRONTEND_PORT"
echo "========================================"
echo "Logs:  $BACKEND_LOG"
echo "       $FRONTEND_LOG"
echo "Para detener: ./start.sh stop"
