#!/bin/bash
# LuminaCast — Multi-Screen Monitor
# Shows the last N lines of output from all running LuminaCast screen sessions.
# Usage: ./monitor.sh [lines]   (default: 30 lines per session)

LINES=${1:-30}
SCREENS=("ollama" "sd" "kokoro" "web")

BOLD="\033[1m"
CYAN="\033[36m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
RESET="\033[0m"
DIVIDER="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

COLORS=("$CYAN" "$GREEN" "$YELLOW" "$RED")

clear
echo -e "${BOLD}🖥  LuminaCast — Service Monitor${RESET}"
echo -e "${BOLD}${DIVIDER}${RESET}"
echo ""

# Check which screens are running
RUNNING=$(screen -ls 2>/dev/null)
if [ -z "$RUNNING" ]; then
    echo -e "${RED}No screen sessions found. Run ./start_all.sh first.${RESET}"
    exit 1
fi

i=0
for SESSION in "${SCREENS[@]}"; do
    COLOR="${COLORS[$((i % ${#COLORS[@]}))]}"
    i=$((i + 1))

    # Check if this screen session exists
    if echo "$RUNNING" | grep -q "\.$SESSION"; then
        echo -e "${BOLD}${COLOR}┌─ [$SESSION] ─────────────────────────────────────────┐${RESET}"

        # Capture the screen's hardcopy (scrollback buffer) to a temp file
        TMPFILE=$(mktemp)
        screen -S "$SESSION" -X hardcopy -h "$TMPFILE" 2>/dev/null

        if [ -f "$TMPFILE" ] && [ -s "$TMPFILE" ]; then
            # Show last N non-empty lines
            grep -v '^$' "$TMPFILE" | tail -n "$LINES" | while IFS= read -r line; do
                echo -e "  ${COLOR}│${RESET} $line"
            done
        else
            echo -e "  ${COLOR}│${RESET} (no output captured yet)"
        fi

        rm -f "$TMPFILE"
        echo -e "${BOLD}${COLOR}└──────────────────────────────────────────────────────┘${RESET}"
    else
        echo -e "${BOLD}${RED}┌─ [$SESSION] ── NOT RUNNING ──┐${RESET}"
        echo -e "${BOLD}${RED}└──────────────────────────────┘${RESET}"
    fi
    echo ""
done

echo -e "${BOLD}${DIVIDER}${RESET}"
echo -e "Showing last ${BOLD}$LINES${RESET} lines per session. Usage: ${BOLD}./monitor.sh [lines]${RESET}"
echo -e "Auto-refresh: ${BOLD}watch -n 5 ./monitor.sh${RESET}"
