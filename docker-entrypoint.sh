#!/bin/bash

Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

sleep 2

exec uv run main.py
