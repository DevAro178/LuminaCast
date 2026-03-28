#!/bin/bash
# LuminaCast — Infrastructure Bootstrap
# This script formats the ephemeral NVMe, sets up tools, and prepares the environment.
# Run as root: sudo ./bootstrap.sh

set -e

DEVICE="/dev/nvme1n1"
MOUNT_POINT="/mnt/nvme"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: Please run as root (use sudo ./bootstrap.sh)"
  exit 1
fi

echo "=== 🚀 Starting Full Infrastructure Bootstrapping ==="

# ----------------------------
# 1. Cleanup & Preparation
# ----------------------------
echo "🧹 Cleaning up root volume..."
apt-get clean
rm -rf /tmp/* || true

# ----------------------------
# 2. Setup NVMe Storage
# ----------------------------
if [ -b "$DEVICE" ]; then
    if mount | grep -q "$DEVICE"; then
        echo "💾 $DEVICE is already mounted. Skipping format."
    else
        echo "💾 Formatting NVMe device $DEVICE..."
        mkfs.ext4 -F $DEVICE

        echo "📂 Mounting NVMe to $MOUNT_POINT..."
        mkdir -p $MOUNT_POINT
        mount $DEVICE $MOUNT_POINT
    fi
    chmod 777 $MOUNT_POINT
else
    echo "⚠️  NVMe device $DEVICE not found. Defaulting to system root."
    MOUNT_POINT="/opt/lumina"
    mkdir -p $MOUNT_POINT
    chmod 777 $MOUNT_POINT
fi

# Create directory structure
mkdir -p $MOUNT_POINT/{models,ollama,envs,apps,tmp,pip_cache}

# !!! CRITICAL: Redirect all temporary files to NVMe to avoid "No space left on device" !!!
export TMPDIR="$MOUNT_POINT/tmp"
export TEMP="$MOUNT_POINT/tmp"
export TMP="$MOUNT_POINT/tmp"
export PIP_CACHE_DIR="$MOUNT_POINT/pip_cache"
export HOME_CACHE="$MOUNT_POINT/tmp/home_cache"
mkdir -p $HOME_CACHE

# ----------------------------
# 3. Install System Dependencies
# ----------------------------
echo "📦 Installing core system packages..."
apt-get update
# Install python3-venv specifically for the current python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
apt-get install -y curl git ffmpeg python3 python3-pip python3-venv python${PYTHON_VERSION}-venv unzip fonts-montserrat sqlite3

# ----------------------------
# 4. Install & Configure Ollama
# ----------------------------
echo "🦙 Installing Ollama..."
if ! command -v ollama &>/dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
    # Give systemd a moment to recognize the new service
    if command -v systemctl &>/dev/null; then
        systemctl daemon-reload
        sleep 2
    fi
fi

if command -v systemctl &>/dev/null; then
    systemctl stop ollama || true
fi

OLLAMA_DIR="/root/.ollama"
mkdir -p $MOUNT_POINT/ollama

if [ -d "$OLLAMA_DIR" ] && [ ! -L "$OLLAMA_DIR" ]; then
    mv $OLLAMA_DIR/* $MOUNT_POINT/ollama/ || true
    rm -rf $OLLAMA_DIR
fi

if [ ! -L "$OLLAMA_DIR" ]; then
    ln -s $MOUNT_POINT/ollama $OLLAMA_DIR
fi

if command -v systemctl &>/dev/null; then
    systemctl start ollama || true
    echo "⌛ Waiting for Ollama service to heat up..."
    sleep 5
else
    echo "⚠️  systemctl not found. Starting ollama manually in background..."
    nohup ollama serve > /var/log/ollama.log 2>&1 &
    sleep 5
fi

echo "🧠 Pulling Mistral model (Ollama)..."
ollama pull mistral || echo "⚠️ Failed to pull mistral. Will retry later."

# ----------------------------
# 5. Install Easy Diffusion
# ----------------------------
echo "🎨 Installing Easy Diffusion..."
ED_DIR="$MOUNT_POINT/apps/easy-diffusion"

if [ ! -d "$ED_DIR" ]; then
    cd $MOUNT_POINT/apps
    curl -L https://github.com/cmdr2/stable-diffusion-ui/releases/latest/download/easy-diffusion-linux.zip -o easy-diffusion.zip
    unzip easy-diffusion.zip
    rm easy-diffusion.zip
fi

cd "$ED_DIR"
chmod +x start.sh

# Run Easy Diffusion in the background to trigger initial dependency installation
echo "🔄 Starting Easy Diffusion (Initial Setup)..."
# Pass TMPDIR and other exports to the child process
export TMPDIR="$MOUNT_POINT/tmp"
./start.sh --listen &

# ----------------------------
# 6. Global Symlinks
# ----------------------------
echo "🔗 Creating convenience symlinks..."
ln -sfn $MOUNT_POINT/apps /root/apps
ln -sfn $MOUNT_POINT/models /root/models

# ----------------------------
# 7. Run App Dependencies
# ----------------------------
echo "🐍 Setting up LuminaCast Python environment..."
# Define NVMe path for virtualenv so it can be picked up by setup_dependencies.sh
export VIRTUAL_ENV_BASE="$MOUNT_POINT/envs"

# Correctly point to the setup script relative to THIS script's location
bash "$SCRIPT_DIR/setup_dependencies.sh"

echo "=== ✅ Bootstrapping Complete! ==="
echo "Easy Diffusion: Port 9000"
echo "Ollama: Pulling Mistral in background"
df -h $MOUNT_POINT
