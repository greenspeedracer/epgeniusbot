#!/bin/bash

exec 1> >(stdbuf -o0 cat)

if pgrep -f "epgeniusbot.py" > /dev/null; then
    echo "killing epgeniusbot"
    
    tmux send-keys -t epgeniusbot C-c
    
    STOP_TIMEOUT=10
    ELAPSED=0
    
    while [ $ELAPSED -lt $STOP_TIMEOUT ]; do
        if ! pgrep -f "epgeniusbot.py" > /dev/null; then
            break
        fi
        sleep 1
        ELAPSED=$((ELAPSED + 1))
    done
    
    if pgrep -f "epgeniusbot.py" > /dev/null; then
        echo "failed to kill epgeniusbot"
        exit 1
    fi
else
    echo "epgeniusbot already killed. starting epgeniusbot"
fi

if ! tmux has-session -t epgeniusbot 2>/dev/null; then
    tmux new-session -d -s epgeniusbot
fi

tmux send-keys -t epgeniusbot C-l
tmux clear-history -t epgeniusbot

tmux send-keys -t epgeniusbot "cd /home/ubuntu/epgeniusbot && python3 /home/ubuntu/epgeniusbot/epgeniusbot.py" Enter

sleep 2

TIMEOUT=30
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    RECENT_OUTPUT=$(tmux capture-pane -t epgeniusbot -p -S -50)
    
    if echo "$RECENT_OUTPUT" | grep -q "epgeniusbot#3611 is fully ready"; then
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
