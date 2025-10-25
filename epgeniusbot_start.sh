#!/bin/bash

if pgrep -f "epgeniusbot.py" > /dev/null; then
    echo "epgeniusbot is already running"
    exit 0
fi

if ! tmux has-session -t epgeniusbot 2>/dev/null; then
    tmux new-session -d -s epgeniusbot
fi

tmux send-keys -t epgeniusbot "cd /home/ubuntu/epgeniusbot && python3 /home/ubuntu/epgeniusbot/epgeniusbot.py" Enter

TIMEOUT=30
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    if tmux capture-pane -t epgeniusbot -p | grep -q "epgeniusbot#3611 is fully ready!"; then
        echo "epgeniusbot has started"
        exit 0
    fi
    
    if ! pgrep -f "epgeniusbot.py" > /dev/null; then
        echo "epgeniusbot failed to start (process died)"
        exit 1
    fi
    
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

echo "epgeniusbot started but ready message not detected within ${TIMEOUT}s"
exit 1
