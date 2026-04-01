#!/bin/bash
# LuminaCast - Start All Services Script
# This script creates 5 detached screen sessions and starts the required services.

# Variables
APP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Detect if we are on NVMe or local
if [ -d "/mnt/nvme" ]; then
    NVME_DIR="/mnt/nvme"
    SD_DIR="$NVME_DIR/apps/easy-diffusion"
    # Ensure venv points to NVMe version if bootstrapped
    VENV_PATH="$NVME_DIR/envs/lumina_venv"
    # Export for setup_dependencies
    export VIRTUAL_ENV_BASE="$NVME_DIR/envs"
else
    SD_DIR="$HOME/easy-diffusion"
    VENV_PATH="$APP_DIR/venv"
fi

# Run dependency check before starting services
echo "Running dependency check..."
bash "$APP_DIR/setup_dependencies.sh"
if [ $? -ne 0 ]; then
    echo "❌ Dependency check failed. Fix the issues above and try again."
    exit 1
fi
echo ""

# 1. Setup Python Virtual Environment (NVMe fallback)
echo "📦 Initializing LuminaCast Studio Environment..."
BACKEND_NVME="/opt/dlami/nvme"
VENV_PATH="/opt/dlami/nvme/envs/chatterbox_venv"

if [ -d "$BACKEND_NVME" ]; then
    if [ ! -d "$VENV_PATH" ]; then
        echo "🚀 Creating primary Studio venv on NVMe..."
        mkdir -p "$BACKEND_NVME/envs"
        python3.11 -m venv "$VENV_PATH"
        
    fi
    source "$VENV_PATH/bin/activate"
    echo "🔄 Syncing dependencies (Whisper, stable-ts, chatterbox)..."
    pip install --upgrade pip --quiet
    pip install -r "$APP_DIR/backend/requirements.txt" --quiet
    pip install -r "$APP_DIR/chatterbox_requirements.txt" --quiet
else
    echo "⚠️ Warning: NVMe not found. Using local venv."
    VENV_PATH="$APP_DIR/venv"
    if [ ! -d "$VENV_PATH" ]; then
        python3 -m venv "$VENV_PATH"
    fi
    source "$VENV_PATH/bin/activate"
    pip install -r "$APP_DIR/backend/requirements.txt" --quiet
fi

# 2. Start System Monitor (htop/top)
echo "Starting monitor screen..."
screen -dmS monitor top

# 3. Start Ollama
echo "Starting Ollama screen..."
screen -dmS ollama bash -c "ollama run mistral"

# 4. Start Easy Diffusion (Stable Diffusion)
echo "Starting Easy Diffusion screen..."
if [ -d "$SD_DIR" ]; then
    screen -dmS sd bash -c "cd $SD_DIR && ./start.sh"
else
    echo "Warning: Easy Diffusion directory not found at $SD_DIR"
fi

# 5. (Deprecated) Kokoro TTS 
# We have migrated to Chatterbox for expressive voicing. 

# 6. Start LuminaCast Web Server (FastAPI)
echo "Starting LuminaCast Web Server screen..."
screen -dmS web bash -c "cd $APP_DIR/backend && source $VENV_PATH/bin/activate && python main.py"

# 7. Start LuminaCast Frontend (React)
echo "Starting LuminaCast Frontend screen..."
if [ -d "$APP_DIR/frontend-v2" ]; then
    screen -dmS frontend bash -c "cd $APP_DIR/frontend-v2 && npm run dev"
fi

# 8. Start Chatterbox TTS Server (Expressive AI)
echo "Starting Chatterbox TTS screen..."
if [ -d "$BACKEND_NVME" ]; then
    echo "Starting Chatterbox server on port 8881..."
    screen -dmS chatterbox bash -c "cd $APP_DIR && source $VENV_PATH/bin/activate && python chatterbox_server.py"
else
    echo "⚠️  Note: NVMe not found. Skipping Chatterbox auto-start."
fi

echo ""
echo "✅ All 5 screen sessions (Monitor, Ollama, SD, Web, Chatterbox) have been started!"
echo ""
echo "To view active screens, run:"
echo "  screen -ls"
echo ""
echo "To attach to a specific screen (e.g., the web server), run:"
echo "  screen -r web"
echo ""
echo "To detach from a screen and leave it running, press: Ctrl+A, then D"
