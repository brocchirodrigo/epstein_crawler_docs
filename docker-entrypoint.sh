#!/bin/bash

# Only start Xvfb for scraper (not for API)
if [ "$1" != "api" ]; then
    Xvfb :99 -screen 0 1920x1080x24 &
    export DISPLAY=:99
    sleep 2
fi

exec uv run main.py "$@"
