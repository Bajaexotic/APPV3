#!/usr/bin/env python
"""
Run main app with signal_trace_orders enabled
"""
import os
import sys

# Enable signal tracing
os.environ["DEBUG_DTC"] = "1"

# Import and attach tracer BEFORE importing main
from tools.signal_trace_orders import attach_order_trace
attach_order_trace()

print("\n" + "="*80)
print("SIGNAL TRACE ENABLED - Monitoring order flow")
print("="*80 + "\n")

# Now run main
from main import main
sys.exit(main())
