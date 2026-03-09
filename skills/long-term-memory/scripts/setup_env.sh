#!/bin/bash
# Setup script for long-term-memory skill.
# Creates venv, installs deps, downloads model, initializes database.
# Idempotent — safe to re-run.
#
# Usage: bash setup_env.sh [light|standard]
#   light    — bge-small-zh-v1.5 (512d, ~300MB total)
#   standard — bge-m3 (1024d, ~4GB total)

set -euo pipefail

PROFILE="${1:-light}"
BASE_DIR="$HOME/.agents/long-term-memory"
VENV_DIR="$BASE_DIR/.venv"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_SCRIPTS="$BASE_DIR/scripts"

json_msg() {
    printf '{"status": "%s", "message": "%s"}\n' "$1" "$2"
}

# Already set up?
if [ -f "$BASE_DIR/.setup_complete" ]; then
    json_msg "ready" "Setup already complete. Profile: $(cat "$BASE_DIR/.profile" 2>/dev/null || echo unknown)"
    exit 0
fi

# Recover from interrupted setup
if [ -f "$BASE_DIR/.setup_in_progress" ]; then
    json_msg "recovering" "Previous setup was interrupted. Cleaning up..." >&2
    rm -rf "$VENV_DIR" "$RUNTIME_SCRIPTS"
fi

# Validate profile
if [ "$PROFILE" != "light" ] && [ "$PROFILE" != "standard" ]; then
    json_msg "error" "Unknown profile: $PROFILE. Use 'light' or 'standard'."
    exit 1
fi

# Check Python3
if ! command -v python3 &>/dev/null; then
    json_msg "error" "Python3 not found. Install Python 3.9+ first."
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]); then
    json_msg "error" "Python 3.9+ required, found $PY_VERSION."
    exit 1
fi

json_msg "progress" "Found Python $PY_VERSION" >&2

# Start setup
mkdir -p "$BASE_DIR"
touch "$BASE_DIR/.setup_in_progress"

cleanup_on_error() {
    json_msg "error" "Setup failed. Check errors above." >&2
    rm -f "$BASE_DIR/.setup_in_progress"
    exit 1
}
trap cleanup_on_error ERR

# Create venv
json_msg "progress" "Creating virtual environment..." >&2
python3 -m venv "$VENV_DIR"
PIP="$VENV_DIR/bin/pip"
PYTHON="$VENV_DIR/bin/python"

# Upgrade pip
"$PIP" install --upgrade pip -q 2>&1 | tail -1 >&2

# Install dependencies
json_msg "progress" "Installing dependencies (profile: $PROFILE)..." >&2

if [ "$PROFILE" = "light" ]; then
    MODEL_NAME="BAAI/bge-small-zh-v1.5"
    EMBEDDING_DIM=512
    "$PIP" install -q sqlite-vec sentence-transformers 2>&1 | tail -3 >&2
elif [ "$PROFILE" = "standard" ]; then
    MODEL_NAME="BAAI/bge-m3"
    EMBEDDING_DIM=1024
    "$PIP" install -q sqlite-vec FlagEmbedding 2>&1 | tail -3 >&2
fi

# Copy scripts to runtime location (fixed path, survives skill dir changes)
json_msg "progress" "Installing scripts..." >&2
mkdir -p "$RUNTIME_SCRIPTS"
cp "$SCRIPT_DIR"/*.py "$RUNTIME_SCRIPTS/"

# Write config
cat > "$BASE_DIR/config.json" <<CONF
{
  "profile": "$PROFILE",
  "model_name": "$MODEL_NAME",
  "embedding_dim": $EMBEDDING_DIM,
  "base_dir": "$BASE_DIR",
  "db_path": "$BASE_DIR/memory.db",
  "venv_python": "$PYTHON",
  "scripts_dir": "$RUNTIME_SCRIPTS",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
CONF

# Pre-download embedding model
json_msg "progress" "Downloading embedding model ($MODEL_NAME)..." >&2
"$PYTHON" -c "
import sys
sys.path.insert(0, '$RUNTIME_SCRIPTS')
from embed import embed_text
result = embed_text('initialization test')
print(f'Model OK. dim={len(result)}', file=sys.stderr)
"

# Initialize database
json_msg "progress" "Initializing database..." >&2
"$PYTHON" "$RUNTIME_SCRIPTS/db_init.py"

# Create wrapper script
printf '#!/bin/bash\nexec "%s" "%s/$1.py" "${@:2}"\n' "$PYTHON" "$RUNTIME_SCRIPTS" > "$BASE_DIR/ltm"
chmod +x "$BASE_DIR/ltm"

# Record profile
echo "$PROFILE" > "$BASE_DIR/.profile"

# Mark complete
rm "$BASE_DIR/.setup_in_progress"
touch "$BASE_DIR/.setup_complete"

json_msg "ok" "Setup complete. Profile=$PROFILE Model=$MODEL_NAME Dim=$EMBEDDING_DIM DB=$BASE_DIR/memory.db"
