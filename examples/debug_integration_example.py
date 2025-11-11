"""
Example Integration of APPSIERRA Debug Subsystem

This file demonstrates best practices for integrating the advanced debug
subsystem into your application components.

Run this example to see the debug subsystem in action:
    python examples/debug_integration_example.py
"""

from pathlib import Path
import random
import sys
import time


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from core.diagnostics import DiagnosticsHub, PerformanceMarker, debug, error, info, log_event, warn
from core.error_policy import handle_error
from core.health_watchdog import HealthWatchdog, heartbeat, register_component


# ==============================================================================
# Example 1: Network Component with Health Monitoring
# ==============================================================================


class DTCConnectionManager:
    """
    Example network component with:
    - Diagnostic events
    - Health monitoring
    - Error handling with policies
    - Performance tracking
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 11099):
        self.host = host
        self.port = port
        self.connected = False
        self.message_count = 0

        # Register for health monitoring
        register_component(
            "dtc_connection", heartbeat_timeout=30.0, metadata={"component_type": "network", "host": host, "port": port}
        )

        info("network", "DTC Connection Manager initialized", context={"host": host, "port": port})

    def connect(self) -> bool:
        """Connect to DTC server with automatic retry via error policy"""

        debug("network", "Attempting connection", context={"host": self.host, "port": self.port})

        # Simulate connection with 70% success rate
        def attempt_connection():
            time.sleep(0.1)  # Simulate network delay
            if random.random() < 0.7:
                self.connected = True
                return True
            raise ConnectionError("Connection refused")

        # Use error policy for automatic retry with backoff
        with PerformanceMarker("dtc_connection", category="network"):
            success = handle_error(
                error_type="dtc_connection_drop",
                category="network",
                context={"host": self.host, "port": self.port},
                operation=attempt_connection,
            )

        if success:
            self.connected = True
            info(
                "network",
                "Connection established",
                event_type="ConnectionSuccess",
                context={"host": self.host, "port": self.port},
            )
        else:
            error("network", "Connection failed after retries", context={"host": self.host, "port": self.port})

        return success

    def receive_messages(self, duration: int = 10):
        """Simulate receiving messages with heartbeats"""
        info("network", "Starting message receiver", context={"duration_sec": duration})

        start_time = time.time()
        while time.time() - start_time < duration:
            # Send heartbeat every iteration
            heartbeat("dtc_connection", metadata={"connected": self.connected, "messages_received": self.message_count})

            # Simulate receiving messages
            if self.connected:
                self.message_count += 1

                if settings.DEBUG_DATA:
                    debug(
                        "data",
                        "Message received",
                        event_type="MessageReceived",
                        context={"message_id": self.message_count, "type": "market_data"},
                    )

                # Simulate occasional slow message processing
                if random.random() < 0.1:
                    with PerformanceMarker("slow_message_processing", category="data"):
                        time.sleep(0.2)
                        warn("perf", "Slow message processing detected", context={"processing_time_ms": 200})

            time.sleep(0.5)

        info("network", "Message receiver stopped", context={"total_messages": self.message_count})


# ==============================================================================
# Example 2: Data Processing Component
# ==============================================================================


class MarketDataProcessor:
    """
    Example data processing component with:
    - Performance markers
    - Error handling
    - Diagnostic events
    """

    def __init__(self):
        self.cache = {}
        info("data", "Market Data Processor initialized")

    def process_trade(self, symbol: str, price: float, volume: int) -> dict:
        """Process trade data with performance tracking"""

        debug("data", "Processing trade", context={"symbol": symbol, "price": price, "volume": volume})

        with PerformanceMarker("trade_processing", category="analytics"):
            # Simulate calculation
            time.sleep(0.01)

            # Calculate some metrics
            trade_value = price * volume
            impact = self._calculate_market_impact(volume)

            result = {"symbol": symbol, "price": price, "volume": volume, "value": trade_value, "impact": impact}

            # Cache result
            self.cache[symbol] = result

            info(
                "analytics",
                "Trade processed",
                event_type="TradeProcessed",
                context={"symbol": symbol, "value": trade_value},
            )

            return result

    def _calculate_market_impact(self, volume: int) -> float:
        """Simulate complex calculation"""
        with PerformanceMarker("market_impact_calculation", category="analytics"):
            time.sleep(0.005)

            # Simulate potential calculation error
            if volume > 10000:
                warn("analytics", "Large trade volume detected", context={"volume": volume, "threshold": 10000})

            return volume * 0.001


# ==============================================================================
# Example 3: Main Application Flow
# ==============================================================================


def main():
    """
    Main application demonstrating full debug subsystem integration.
    """

    print("=" * 70)
    print("APPSIERRA Debug Subsystem - Integration Example")
    print("=" * 70)
    print()

    # Initialize diagnostics hub
    hub = DiagnosticsHub.get_instance(max_events=500)
    info(
        "system",
        "Application starting",
        event_type="AppStart",
        context={"version": "1.0.0", "debug_mode": settings.DEBUG_MODE},
    )

    # Start health watchdog
    watchdog = HealthWatchdog.get_instance(check_interval=2.0)
    watchdog.start()
    info("system", "Health watchdog started")

    # Register health callback
    def on_health_update(metrics):
        if metrics.unhealthy_components > 0:
            warn(
                "system",
                "Unhealthy components detected",
                context={"unhealthy_count": metrics.unhealthy_components, "total_components": metrics.total_components},
            )

    watchdog.register_health_callback(on_health_update)

    try:
        # Example 1: Network connection
        print("\n[1] Testing network connection with retry policy...")
        print("-" * 70)
        dtc = DTCConnectionManager()
        dtc.connect()

        # Example 2: Message processing with heartbeats
        print("\n[2] Processing messages with health monitoring...")
        print("-" * 70)
        dtc.receive_messages(duration=5)

        # Example 3: Data processing with performance markers
        print("\n[3] Processing trades with performance tracking...")
        print("-" * 70)
        processor = MarketDataProcessor()

        trades = [
            ("ES", 4500.25, 100),
            ("ES", 4500.50, 250),
            ("NQ", 15000.00, 50),
            ("ES", 4501.00, 15000),  # Large volume - triggers warning
        ]

        for symbol, price, volume in trades:
            processor.process_trade(symbol, price, volume)
            time.sleep(0.1)

        # Example 4: Generate some errors for demonstration
        print("\n[4] Demonstrating error handling...")
        print("-" * 70)

        error("core", "Simulated configuration error", context={"missing_key": "API_KEY", "config_file": "config.json"})

        # Example 5: Get statistics
        print("\n[5] Diagnostic statistics:")
        print("-" * 70)
        stats = hub.get_statistics()
        print(f"  Total events: {stats['total_events']}")
        print(f"  Errors: {stats['errors_count']}")
        print("  Events by category:")
        for category, count in sorted(stats["events_by_category"].items()):
            print(f"    {category}: {count}")

        # Example 6: Export session
        print("\n[6] Exporting diagnostic session...")
        print("-" * 70)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        dump_file = f"logs/example_session_{timestamp}.json"
        hub.export_json(dump_file)
        print(f"  Session exported to: {dump_file}")

        # Example 7: Session analysis
        print("\n[7] Analyzing session...")
        print("-" * 70)

        from core.session_replay import SessionReplay

        replay = SessionReplay.from_file(dump_file)
        analysis = replay.analyze()

        print(f"  Duration: {analysis.duration_sec:.2f}s")
        print(f"  Events/sec: {analysis.events_per_second:.2f}")
        print(f"  Error rate: {analysis.error_rate:.2%}")

        if analysis.performance_stats:
            perf = analysis.performance_stats
            print("  Performance:")
            print(f"    Min: {perf['min_ms']:.2f}ms")
            print(f"    Max: {perf['max_ms']:.2f}ms")
            print(f"    Avg: {perf['avg_ms']:.2f}ms")
            print(f"    P95: {perf['p95_ms']:.2f}ms")

        # Example 8: Generate forensic report
        print("\n[8] Generating forensic report...")
        print("-" * 70)
        report_file = f"logs/example_report_{timestamp}.md"
        replay.generate_report(report_file)
        print(f"  Report saved to: {report_file}")

        # Show component health
        print("\n[9] Component health status:")
        print("-" * 70)
        for name, status in watchdog.get_all_statuses().items():
            health_str = "✓ HEALTHY" if status.is_healthy else "✗ UNHEALTHY"
            print(f"  {name}: {health_str}")
            print(f"    Last heartbeat: {time.time() - status.last_heartbeat:.1f}s ago")
            print(f"    Total failures: {status.total_failures}")

    except Exception as e:
        error("system", "Application error", context={"exception": str(e), "exception_type": type(e).__name__})
        raise

    finally:
        # Cleanup
        info("system", "Application shutting down")
        watchdog.stop()

    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Review the exported files in logs/")
    print("  2. Try enabling different DEBUG_* flags")
    print("  3. Integrate similar patterns into your components")
    print()


if __name__ == "__main__":
    main()
