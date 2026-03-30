#!/usr/bin/env bash
# ==============================================================================
# Dance Coaching Platform - Environment Setup (Linux / macOS / WSL)
# ==============================================================================
# Checks prerequisites, installs dependencies, and prepares the project for
# local development.  Run from the repository root:
#     bash scripts/setup.sh
# ==============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No colour

ok()   { echo -e "${GREEN}[OK]${NC}    $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
fail() { echo -e "${RED}[FAIL]${NC}  $1"; }

errors=0

echo ""
echo "====================================="
echo "  Dance Coaching Platform Setup"
echo "====================================="
echo ""

# ---------- prerequisite checks ----------

# Node.js >= 20
if command -v node &>/dev/null; then
    NODE_VER=$(node -v | sed 's/v//')
    NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
    if [ "$NODE_MAJOR" -ge 20 ]; then
        ok "Node.js $NODE_VER"
    else
        fail "Node.js $NODE_VER found, but >= 20 required"
        echo "       Install via https://nodejs.org/ or nvm: nvm install 22"
        errors=$((errors + 1))
    fi
else
    fail "Node.js not found"
    echo "       Install via https://nodejs.org/ or nvm: nvm install 22"
    errors=$((errors + 1))
fi

# Python >= 3.10
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version | awk '{print $2}')
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 10 ]; then
        ok "Python $PY_VER"
    else
        fail "Python $PY_VER found, but >= 3.10 required"
        echo "       Install via https://www.python.org/downloads/ or pyenv"
        errors=$((errors + 1))
    fi
else
    fail "Python 3 not found"
    echo "       Install via https://www.python.org/downloads/ or pyenv"
    errors=$((errors + 1))
fi

# Redis
if command -v redis-server &>/dev/null; then
    REDIS_VER=$(redis-server --version | grep -oP 'v=\K[0-9.]+' || redis-server --version | awk '{print $3}' | tr -d 'v=')
    ok "Redis $REDIS_VER"
elif command -v redis-cli &>/dev/null; then
    ok "Redis CLI found (server may be running as a service)"
else
    fail "redis-server not found"
    echo "       Ubuntu/Debian: sudo apt install redis-server"
    echo "       macOS:         brew install redis"
    echo "       WSL:           sudo apt install redis-server"
    errors=$((errors + 1))
fi

# ffmpeg
if command -v ffmpeg &>/dev/null; then
    FFMPEG_VER=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
    ok "ffmpeg $FFMPEG_VER"
else
    fail "ffmpeg not found"
    echo "       Ubuntu/Debian: sudo apt install ffmpeg"
    echo "       macOS:         brew install ffmpeg"
    errors=$((errors + 1))
fi

# Bail out if any prerequisite is missing
if [ "$errors" -gt 0 ]; then
    echo ""
    fail "$errors prerequisite(s) missing.  Fix the issues above and re-run."
    exit 1
fi

echo ""
echo "All prerequisites satisfied."
echo ""

# ---------- server dependencies ----------

echo "--- Installing server dependencies ---"
cd "$ROOT_DIR/server"
npm install
ok "Server npm packages installed"

# ---------- worker dependencies ----------

echo ""
echo "--- Setting up worker Python environment ---"
cd "$ROOT_DIR/worker"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    ok "Virtual environment created at worker/.venv"
else
    warn "Virtual environment already exists, skipping creation"
fi

.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt --quiet
ok "Worker Python packages installed"

# Install dev dependencies too
.venv/bin/pip install pytest pytest-asyncio pytest-cov --quiet
ok "Worker dev dependencies installed"

# ---------- storage directories ----------

echo ""
echo "--- Ensuring storage directories exist ---"
cd "$ROOT_DIR"
mkdir -p storage/uploads storage/outputs storage/temp
touch storage/uploads/.gitkeep storage/outputs/.gitkeep storage/temp/.gitkeep
ok "Storage directories ready"

# ---------- .env file ----------

if [ ! -f "$ROOT_DIR/.env" ]; then
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    ok "Created .env from .env.example"
    warn "Edit .env to add your API keys before running the platform"
else
    warn ".env already exists, not overwriting"
fi

# ---------- done ----------

echo ""
echo "====================================="
echo -e "  ${GREEN}Setup complete!${NC}"
echo "====================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your configuration (KLING_API_KEY, etc.)"
echo "  2. Start Redis:       redis-server"
echo "  3. Start the server:  cd server && npm run dev"
echo "  4. Start the worker:  cd worker && .venv/bin/python -m src.main"
echo ""
echo "For GPU setup (MimicMotion), run:"
echo "  bash scripts/setup-mimicmotion.sh"
echo ""
