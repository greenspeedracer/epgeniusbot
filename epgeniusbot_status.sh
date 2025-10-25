#!/bin/bash

if pgrep -f "epgeniusbot.py" > /dev/null; then
    echo "epgeniusbot is alive"
    exit 0
else
    echo "He's dead, Jim!"
    exit 0
fi