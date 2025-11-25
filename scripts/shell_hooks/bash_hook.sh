#!/bin/bash
# LWO Shell Hook for Bash

# Socket path
LWO_SOCKET="$HOME/.local/share/lwo/shell.sock"

# Variables to track command execution
_lwo_cmd_start_time=0
_lwo_last_cmd=""

# DEBUG trap: Called before command execution
_lwo_preexec() {
    _lwo_cmd_start_time=$SECONDS
    _lwo_last_cmd="$BASH_COMMAND"
}

# PROMPT_COMMAND: Called after command execution
_lwo_precmd() {
    local exit_code=$?
    
    # Only send data if we have a command to report
    if [[ -n "$_lwo_last_cmd" ]]; then
        local duration=$(( $SECONDS - $_lwo_cmd_start_time ))
        
        # Escape special characters
        local cmd_escaped=$(echo "$_lwo_last_cmd" | sed 's/\\/\\\\/g;s/"/\\"/g')
        local pwd_escaped=$(echo "$PWD" | sed 's/\\/\\\\/g;s/"/\\"/g')
        
        # Build JSON data
        local json_data="{\"command\":\"$cmd_escaped\",\"pwd\":\"$pwd_escaped\",\"ts\":$(date +%s),\"duration\":$duration,\"exit_code\":$exit_code}"
        
        # Send to Unix socket
        echo "$json_data" | nc -U -w 1 "$LWO_SOCKET" 2>/dev/null || true
        
        _lwo_last_cmd=""
    fi
}

# Set up traps
trap '_lwo_preexec' DEBUG
PROMPT_COMMAND="_lwo_precmd${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
