#!/bin/bash
# LuminaCast - Shutdown All Services Script
# Kills all screen sessions started by start_all.sh.

echo "🛑 LuminaCast — Shutting down all services..."

SCREENS=("monitor" "ollama" "sd" "kokoro" "web")

for name in "${SCREENS[@]}"; do
    if screen -list | grep -q "$name"; then
        screen -S "$name" -X quit
        echo "  ✗ Stopped: $name"
    else
        echo "  - Not running: $name"
    fi
done

echo ""
echo "✅ All services stopped."
echo ""
