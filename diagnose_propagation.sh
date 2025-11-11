#!/bin/bash

# APPSIERRA Live-Data Propagation Diagnostic Script
# Usage: ./diagnose_propagation.sh
# Or:    bash diagnose_propagation.sh

echo "================================================================================"
echo "APPSIERRA LIVE-DATA PROPAGATION DIAGNOSTIC"
echo "================================================================================"

cd "$(dirname "$0")"

echo ""
echo "[1] Checking for Sierra connection..."
export DEBUG_NETWORK=1
timeout 5 python main.py 2>&1 | grep -i "dtc.tcp.connected\|connected" | head -1

echo ""
echo "[2] Checking if Sierra is sending heartbeats..."
timeout 5 python main.py 2>&1 | grep "Type: 3" | head -1

echo ""
echo "[3] Checking for encoding mismatch..."
timeout 5 python main.py 2>&1 | grep -i "encoding.mismatch"

if [ $? -eq 0 ]; then
    echo ""
    echo "*** FOUND ENCODING MISMATCH ***"
    echo "Sierra Chart is sending BINARY DTC, not JSON"
    echo ""
    echo "FIX: Sierra Chart Settings"
    echo "  Global Settings > Data/Trade Service Settings > DTC Protocol Server"
    echo "  Change to: JSON/Compact Encoding"
    echo ""
else
    echo "  [OK] No encoding mismatch detected"
fi

echo ""
echo "[4] Checking for Type 600 (Balance) messages..."
export DEBUG_DATA=1
timeout 10 python main.py 2>&1 | grep "Type: 600" | head -3

echo ""
echo "[5] Checking for Type 301 (Order) messages..."
timeout 10 python main.py 2>&1 | grep "Type: 301" | head -3

echo ""
echo "[6] Checking for Type 306 (Position) messages..."
timeout 10 python main.py 2>&1 | grep "Type: 306" | head -3

echo ""
echo "[7] Checking signal propagation..."
timeout 10 python main.py 2>&1 | grep -E "BALANCE.*signal|POSITION.*signal|ORDER.*signal" | head -5

echo ""
echo "================================================================================"
echo "Diagnostics complete. Check output above:"
echo ""
echo "  - If you see Type: 600/301/306 messages -> Data IS flowing"
echo "  - If you see encoding.mismatch -> Sierra in BINARY mode (change settings)"
echo "  - If you see no messages -> Sierra not sending or not connected"
echo "================================================================================"
