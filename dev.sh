#!/bin/bash
# LWO Development Environment Helper
# Usage: source ./dev.sh

echo "=== LWO Development Environment ==="

# Export config path to use project directory config
export LWO_CONFIG="$(pwd)/lwo.toml"
echo "✓ Config file: $LWO_CONFIG"

# Setup Shell Hook for current session only (not persistent)
echo "✓ Loading Shell Hook for current session..."

# Detect shell type
if [ -n "$ZSH_VERSION" ]; then
    # Zsh
    source "$(pwd)/scripts/shell_hooks/zsh_hook.sh"
    echo "✓ Zsh hook loaded"
elif [ -n "$BASH_VERSION" ]; then
    # Bash
    source "$(pwd)/scripts/shell_hooks/bash_hook.sh"
    echo "✓ Bash hook loaded"
else
    echo "✗ Unsupported shell"
    return 1
fi

# Helper functions
alias lwo-start='uv run main.py start'
alias lwo-stop='uv run main.py stop'
alias lwo-report='uv run main.py report'
alias lwo-daily='uv run main.py daily'
alias lwo-log='tail -f ~/.local/share/lwo/lwo.log'
alias lwo-db='psql -h localhost -U postgres -d lwo'

echo
echo "Available commands:"
echo "  lwo-start   - Start daemon"
echo "  lwo-stop    - Stop daemon"
echo "  lwo-report  - View current report"
echo "  lwo-daily   - Generate daily report"
echo "  lwo-log     - Tail daemon log"
echo "  lwo-db      - Connect to database"
echo
echo "Shell Hook is active for this session only."
echo "Your ~/.zshrc or ~/.bashrc will NOT be modified."
echo
