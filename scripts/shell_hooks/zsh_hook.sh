#!/bin/bash
# LWO Shell Hook for Zsh

# Socket path
LWO_SOCKET="$HOME/.local/share/lwo/shell.sock"

# Variables to track command execution
_lwo_cmd_start_time=0
_lwo_last_cmd=""

# preexec: Called before command execution
preexec() {
    _lwo_cmd_start_time=$EPOCHSECONDS
    _lwo_last_cmd="$1"
}

# precmd: Called after command execution, before next prompt
precmd() {
    local exit_code=$?
    
    # Only send data if we have a command to report
    if [[ -n "$_lwo_last_cmd" ]]; then
        local duration=$(( $EPOCHSECONDS - $_lwo_cmd_start_time ))
        
        # Escape special characters in command and pwd
        local cmd_escaped=$(echo "$_lwo_last_cmd" | sed 's/\\/\\\\/g;s/"/\\"/g')
        local pwd_escaped=$(echo "$PWD" | sed 's/\\/\\\\/g;s/"/\\"/g')
        
        # Build JSON data
        local json_data="{\"command\":\"$cmd_escaped\",\"pwd\":\"$pwd_escaped\",\"ts\":$_lwo_cmd_start_time,\"duration\":$duration,\"exit_code\":$exit_code}"
        
        # Send to Unix socket (silently ignore errors if daemon is not running)
        echo "$json_data" | nc -U -w 1 "$LWO_SOCKET" 2>/dev/null || true
        
        # Clear the command for next iteration
        _lwo_last_cmd=""
    fi
}
