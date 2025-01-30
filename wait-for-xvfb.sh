#!/bin/sh
MAX_ATTEMPTS=10
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    xdpyinfo -display :99 >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        exit 0
    fi
    sleep 1
    ATTEMPT=$((ATTEMPT+1))
done
exit 1