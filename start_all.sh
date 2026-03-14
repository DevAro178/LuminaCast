#!/bin/bash
# LuminaCast - Start All Services Script
# This script creates 5 detached screen sessions and starts the required services.

# Variables
APP_DIR="$HOME/LuminaCast"
SD_DIR="$HOME/easy-diffusion"

# Run dependency check before starting services
echo "Running dependency check..."
bash "$APP_DIR/setup_dependencies.sh"
if [ $? -ne 0 ]; then
    echo "❌ Dependency check failed. Fix the issues above and try again."
    exit 1
fi
echo ""

# 1. Start System Monitor (htop/top)
echo "Starting monitor screen..."
screen -dmS monitor top

# 2. Start Ollama
echo "Starting Ollama screen..."
screen -dmS ollama bash -c "ollama run mistral"

# 3. Start Easy Diffusion (Stable Diffusion)
echo "Starting Easy Diffusion screen..."
if [ -d "$SD_DIR" ]; then
    screen -dmS sd bash -c "cd $SD_DIR && ./start.sh"
else
    echo "Warning: Easy Diffusion directory not found at $SD_DIR"
fi

# 4. Start Kokoro TTS Server
echo "Starting Kokoro TTS screen..."
if [ -d "$APP_DIR" ]; then
    screen -dmS kokoro bash -c "cd $APP_DIR && source venv/bin/activate && python kokoro_server.py"
else
    echo "Error: LuminaCast directory not found at $APP_DIR. Cannot start TTS."
fi

# 5. Start LuminaCast Web Server (FastAPI)
echo "Starting LuminaCast Web Server screen..."
if [ -d "$APP_DIR/backend" ]; then
    screen -dmS web bash -c "cd $APP_DIR/backend && source ../venv/bin/activate && python main.py"
else
    echo "Error: LuminaCast backend directory not found. Cannot start web server."
fi

# 6. Start LuminaCast Frontend (React)
echo "Starting LuminaCast Frontend screen..."
if [ -d "$APP_DIR/frontend-v2" ]; then
    screen -dmS frontend bash -c "cd $APP_DIR/frontend-v2 && npm run dev"
else
    echo "Error: LuminaCast frontend directory not found. Cannot start frontend server."
fi

echo ""
echo "✅ All 6 screen sessions have been started!"
echo ""
echo "To view active screens, run:"
echo "  screen -ls"
echo ""
echo "To attach to a specific screen (e.g., the web server), run:"
echo "  screen -r web"
echo ""
echo "To detach from a screen and leave it running, press: Ctrl+A, then D"
