#!/bin/bash
# Cron wrapper script for automated morning analysis
# Add to crontab: 0 8 * * 1-5 /path/to/cron_script.sh

set -e

# Project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/cron_analysis.log"

# Create logs directory
mkdir -p "$LOG_DIR"

# Timestamp function
log_timestamp() {
    echo "$(date '+%Y-%m-%d %H:%M:%S')"
}

# Log message
log_message() {
    echo "[$(log_timestamp)] $1" >> "$LOG_FILE"
}

log_message "========================================"
log_message "Starting morning trading analysis"
log_message "========================================"

# Activate Python environment if using venv
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
    log_message "Virtual environment activated"
fi

# Change to project directory
cd "$PROJECT_DIR"

# Run analysis script
{
    log_message "Executing morning analysis..."
    python main.py --mode analysis
    log_message "Morning analysis completed successfully"
} || {
    log_message "ERROR: Morning analysis failed"
    exit 1
}

log_message "========================================"
