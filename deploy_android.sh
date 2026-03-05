#!/bin/bash

# Ensure adb is connected
if ! command -v adb &> /dev/null; then
    echo "Error: adb is not installed or not in PATH."
    exit 1
fi

DEVICE_ID=$1

if [ -z "$DEVICE_ID" ]; then
    echo "No device ID specified. Using default/first available device."
    ADB_CMD="adb"
else
    echo "Using device: $DEVICE_ID"
    ADB_CMD="adb -s $DEVICE_ID"
fi

echo "Pushing binary and frontend to Android device..."
$ADB_CMD push webterm-android-arm64 /data/local/tmp/webterm
$ADB_CMD push index.html /data/local/tmp/index.html

echo "Setting permissions..."
$ADB_CMD shell chmod 755 /data/local/tmp/webterm

echo "Stopping any existing webterm process..."
$ADB_CMD shell pkill webterm || true

echo "Starting webterm on the device (Port 8000)..."
$ADB_CMD shell "cd /data/local/tmp && nohup ./webterm 8000 >/data/local/tmp/webterm.log 2>&1 &"

echo "Port forwarding device port 8000 to local port 8000..."
$ADB_CMD reverse tcp:8000 tcp:8000

echo "Deployment complete! Open your browser at http://localhost:8000"
