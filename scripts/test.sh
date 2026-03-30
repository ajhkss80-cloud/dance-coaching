#!/usr/bin/env bash
# ==============================================================================
# Dance Coaching Platform - Run All Tests (Linux / macOS / WSL)
# ==============================================================================
# Runs server (vitest) and worker (pytest) test suites.
# Run from the repository root:  bash scripts/test.sh
# ==============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

server_ok=true
worker_ok=true

echo ""
echo "====================================="
echo "  Running All Tests"
echo "====================================="

# ---------- server tests ----------

echo ""
echo -e "${YELLOW}--- Server Tests (vitest) ---${NC}"
cd "$ROOT_DIR/server"

if npm test 2>&1; then
    echo -e "${GREEN}Server tests passed.${NC}"
else
    echo -e "${RED}Server tests failed.${NC}"
    server_ok=false
fi

# ---------- worker tests ----------

echo ""
echo -e "${YELLOW}--- Worker Tests (pytest) ---${NC}"
cd "$ROOT_DIR/worker"

PYTHON_CMD=".venv/bin/python"
if [ ! -f "$PYTHON_CMD" ]; then
    echo -e "${RED}Worker virtual environment not found.${NC}"
    echo "Run setup first:  bash scripts/setup.sh"
    worker_ok=false
else
    if $PYTHON_CMD -m pytest tests/ -v 2>&1; then
        echo -e "${GREEN}Worker tests passed.${NC}"
    else
        echo -e "${RED}Worker tests failed.${NC}"
        worker_ok=false
    fi
fi

# ---------- summary ----------

echo ""
echo "====================================="
echo "  Test Summary"
echo "====================================="

if $server_ok; then
    echo -e "  Server:  ${GREEN}PASSED${NC}"
else
    echo -e "  Server:  ${RED}FAILED${NC}"
fi

if $worker_ok; then
    echo -e "  Worker:  ${GREEN}PASSED${NC}"
else
    echo -e "  Worker:  ${RED}FAILED${NC}"
fi

echo ""

if $server_ok && $worker_ok; then
    echo -e "${GREEN}All tests passed.${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
