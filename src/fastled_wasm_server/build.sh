#!/bin/bash

# Use NO_PLATFORMIO environment variable if set, otherwise default to --no-platformio
if [ "${NO_PLATFORMIO:-0}" = "1" ]; then
    python compile.py --no-platformio
else
    python compile.py
fi