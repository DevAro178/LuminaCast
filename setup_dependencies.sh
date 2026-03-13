#!/bin/bash
# LuminaCast - Dependency Setup Script
# Checks and installs required system dependencies.
# Called automatically by start_all.sh before booting services.

set -e

echo "🔍 LuminaCast — Checking dependencies..."

# --- System Packages ---
install_if_missing() {
    local pkg="$1"
    if ! dpkg -l "$pkg" &>/dev/null; then
        echo "📦 Installing $pkg..."
        sudo apt-get install -y "$pkg"
    else
        echo "✅ $pkg already installed"
    fi
}

# FFmpeg (required for video assembly)
if ! command -v ffmpeg &>/dev/null; then
    echo "📦 Installing ffmpeg..."
    sudo apt-get update
    sudo apt-get install -y ffmpeg
else
    echo "✅ ffmpeg already installed"
fi

# Montserrat font (required for caption styling)
install_if_missing "fonts-montserrat"

# Refresh font cache after installing fonts
if fc-list | grep -qi "montserrat"; then
    echo "✅ Montserrat font available"
else
    echo "🔄 Refreshing font cache..."
    fc-cache -fv
    if fc-list | grep -qi "montserrat"; then
        echo "✅ Montserrat font now available"
    else
        echo "⚠️  Warning: Montserrat font not detected. Captions will fall back to Arial."
    fi
fi

# --- Python Virtual Environment ---
APP_DIR="$HOME/LuminaCast"
VENV_DIR="$APP_DIR/venv"

if [ -d "$VENV_DIR" ]; then
    echo "✅ Python venv exists at $VENV_DIR"
else
    echo "📦 Creating Python venv..."
    python3 -m venv "$VENV_DIR"
fi

# Install/upgrade Python dependencies
echo "📦 Checking Python dependencies..."
source "$VENV_DIR/bin/activate"

pip install --quiet --upgrade pip
pip install --quiet -r "$APP_DIR/backend/requirements.txt"
pip install --quiet -r "$APP_DIR/kokoro_requirements.txt"

deactivate

echo ""
echo "✅ All dependencies verified!"
echo ""
