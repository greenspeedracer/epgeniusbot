#!/bin/bash

if ! pgrep -f "epgeniusbot.py" > /dev/null; then
    echo "He's (already) dead, Jim!"
    exit 0
fi

tmux send-keys -t epgeniusbot C-c

TIMEOUT=10
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    if ! pgrep -f "epgeniusbot.py" > /dev/null; then
        echo "He's dead, Jim!"
        exit 0
    fi
    
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

if pgrep -f "epgeniusbot.py" > /dev/null; then
    echo "failed to kill epgeniusbot"
    exit 1
fi

echo "He's dead, Jim!"
exit 0
