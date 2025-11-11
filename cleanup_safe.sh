#!/bin/bash
# ============================================================================
# Safe Cleanup Script for APPSIERRA (Linux/Mac)
# Removes only CONFIRMED unused/redundant files
# ============================================================================

echo ""
echo "============================================================================"
echo " APPSIERRA - Safe Cleanup Script"
echo "============================================================================"
echo ""
echo "This script will remove:"
echo "  - Unused DTC client (dtc_json_client.py)"
echo "  - Unused services (dtc_ledger, dtc_report_cli, market_joiner)"
echo "  - Unused trade_metrics"
echo "  - Temporary files (.tmp)"
echo "  - Build artifacts"
echo ""
echo "Files will be DELETED (but recoverable via Git)"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

cd "$(dirname "$0")"

echo ""
echo "[1/5] Deleting unused DTC client..."
if [ -f services/dtc_json_client.py ]; then
    rm services/dtc_json_client.py
    echo "  DELETED: services/dtc_json_client.py"
else
    echo "  SKIP: File not found"
fi

echo ""
echo "[2/5] Deleting unused services..."
rm -f services/dtc_ledger.py && echo "  DELETED: services/dtc_ledger.py"
rm -f services/dtc_report_cli.py && echo "  DELETED: services/dtc_report_cli.py"
rm -f services/market_joiner.py && echo "  DELETED: services/market_joiner.py"
rm -f services/trade_metrics.py && echo "  DELETED: services/trade_metrics.py"

echo ""
echo "[3/5] Deleting temporary files..."
rm -f panels/panel1.py.tmp && echo "  DELETED: panels/panel1.py.tmp"

echo ""
echo "[4/5] Deleting build artifacts..."
rm -rf main.build/ && echo "  DELETED: main.build/"
rm -rf main.onefile-build/ && echo "  DELETED: main.onefile-build/"
rm -rf main.dist/ && echo "  DELETED: main.dist/"

echo ""
echo "[5/5] Cleaning Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null
echo "  DELETED: Python cache directories"

echo ""
echo "============================================================================"
echo " Cleanup Complete!"
echo "============================================================================"
echo ""
echo "Summary:"
echo "  - Removed unused DTC client (~30KB)"
echo "  - Removed unused services (~21KB)"
echo "  - Removed temp files"
echo "  - Removed build artifacts (~10-100MB)"
echo "  - Cleaned Python caches"
echo ""
echo "Next steps:"
echo "  1. Run: python main.py  (to verify app still works)"
echo "  2. Run: git status      (to see what was deleted)"
echo "  3. Run: git add -A      (to stage changes)"
echo "  4. Run: git commit -m 'chore: cleanup unused code'"
echo ""
