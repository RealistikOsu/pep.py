#!/bin/bash
set -euo pipefail

echo "Starting server..."

cd /app/peppy/
python3.9 main.py
