"""
Advanced Diagnostics and Debug Subsystem for APPSIERRA

This module implements a distributed nervous system for observability, structured
diagnostics, and adaptive verbosity. It provides:

- Structured event logging with rich context
- Ring buffer for in-memory event storage
- Event routing to multiple targets (console, file, UI, telemetry)
- Snapshot and export capabilities
- Session replay support
- Health monitoring and forensics

Usage:
    from core.diagnostics import log_event, DiagnosticsHub

    # Log an event
    log_event(
        category="network",
        level="info",
        message="Socket connected",
        context={"host": "127.0.0.1", "port": 11099}
    )

    # Get diagnostics snapshot
    hub = DiagnosticsHub.get_instance()
    snapshot = hub.snapshot(max_events=500)
    hub.export_json("logs/debug_session.json")
"""

from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
import inspect
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback
from typing import Any, Dict, List, Optional, Set

# Import existing logger for fallback
from utils.logger import get_logger


logger = get_logger(__name__)

# Import settings for TRADING_MODE check
try:
    from config import settings

    _SETTINGS_AVAILABLE = True
except ImportError:
    _SETTINGS_AVAILABLE = False
    settings = None


class EventLevel(Enum):
    """Event severity levels"""

    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    FATAL = "fatal"


class EventCategory(Enum):
    """Event categories for routing and filtering"""

    CORE = "core"  # app_manager, state_manager
    UI = "ui"  # UI render events, signals, widgets
    DATA = "data"  # DTC, JSON payloads, schema, cache
    NETWORK = "network"  # Socket connectivity, heartbeats
    ANALYTICS = "analytics"  # Metrics, performance calculations
    PERF = "perf"  # Latency, CPU, memory measurements
    SYSTEM = "system"  # General system events
    UNKNOWN = "unknown"  # Uncategorized


@dataclass
class DiagnosticEvent:
    """
    Structured event schema for all diagnostic events.

    Answers the three key questions:
    - Where did this happen? (file, module, line, thread)
    - Why did it happen? (event_type, context)
    - What should be done? (level, category for routing)
    """

    timestamp: str
    category: str
    level: str
    module: str
    event_type: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)

    # Metadata for forensics
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    thread_id: Optional[int] = None
    thread_name: Optional[str] = None

    # Performance metadata
    elapsed_ms: Optional[float] = None

    # Unique event ID for correlation
    event_id: Optional[str] = None

    # Stack trace for errors
    stack_trace: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class EventRouter:
    """
    Routes diagnostic events to appropriate targets based on category and level.

    Targets can be:
    - Console (stdout/stderr)
    - File logger
    - UI widget (live debug console)
    - Telemetry service
    """

    def __init__(self):
        self.handlers: list[Callable[[DiagnosticEvent], None]] = []
        self._lock = threading.Lock()

    def register_handler(self, handler: Callable[[DiagnosticEvent], None]):
        """Register a new event handler"""
        with self._lock:
            if handler not in self.handlers:
                self.handlers.append(handler)

    def unregister_handler(self, handler: Callable[[DiagnosticEvent], None]):
        """Unregister an event handler"""
        with self._lock:
            if handler in self.handlers:
                self.handlers.remove(handler)

    def route(self, event: DiagnosticEvent):
        """Route event to all registered handlers"""
        with self._lock:
            handlers = self.handlers.copy()

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # Avoid recursive logging - print directly
                print(f"[DIAGNOSTICS] Handler error: {e}", file=sys.stderr)


class DiagnosticsHub:
    """
    Singleton hub for managing diagnostic events.

    Features:
    - Ring buffer for last N events (default 1000)
    - Automatic state dumps on fatal errors
    - Export to JSON for post-mortem analysis
    - Session replay support
    - Thread-safe operations
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, max_events: int = 1000):
        if DiagnosticsHub._instance is not None:
            raise RuntimeError("DiagnosticsHub is a singleton. Use get_instance().")

        self.max_events = max_events
        self.events: deque[DiagnosticEvent] = deque(maxlen=max_events)
        self.router = EventRouter()
        self._event_lock = threading.Lock()
        self._event_counter = 0
        from datetime import UTC

        self._session_start = datetime.now(UTC).isoformat()

        # Statistics
        self.stats = {
            "total_events": 0,
            "events_by_category": {},
            "events_by_level": {},
            "errors_count": 0,
            "fatal_count": 0,
        }

        # Performance markers
        self.markers: dict[str, float] = {}

        # Register default console handler
        self.router.register_handler(self._console_handler)

        logger.info(f"DiagnosticsHub initialized (buffer size: {max_events})")

    @classmethod
    def get_instance(cls, max_events: int = 1000) -> "DiagnosticsHub":
        """Get singleton instance (thread-safe)"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(max_events)
        return cls._instance

    def emit_event(self, event: DiagnosticEvent):
        """
        Emit a diagnostic event.

        The event is:
        1. Added to ring buffer
        2. Routed to all handlers
        3. Statistics updated
        """
        with self._event_lock:
            # Generate event ID
            self._event_counter += 1
            event.event_id = f"evt_{self._event_counter:06d}"

            # Add to buffer
            self.events.append(event)

            # Update statistics
            self.stats["total_events"] += 1
            self.stats["events_by_category"][event.category] = (
                self.stats["events_by_category"].get(event.category, 0) + 1
            )
            self.stats["events_by_level"][event.level] = self.stats["events_by_level"].get(event.level, 0) + 1

            if event.level == EventLevel.ERROR.value:
                self.stats["errors_count"] += 1
            elif event.level == EventLevel.FATAL.value:
                self.stats["fatal_count"] += 1
                # Auto-dump on fatal errors
                self._auto_dump_on_fatal(event)

        # Route to handlers (outside lock to avoid deadlock)
        self.router.route(event)

    def snapshot(self, max_events: Optional[int] = None) -> list[dict[str, Any]]:
        """
        Get snapshot of recent events.

        Args:
            max_events: Maximum number of events to return (None = all)

        Returns:
            List of event dictionaries
        """
        with self._event_lock:
            events = list(self.events)

        if max_events is not None:
            events = events[-max_events:]

        return [event.to_dict() for event in events]

    def export_json(self, path: str):
        """
        Export diagnostic session to JSON file.

        Includes:
        - Session metadata
        - All buffered events
        - Statistics
        - Performance markers
        """
        snapshot_data = {
            "session_start": self._session_start,
            "session_end": datetime.now(UTC).isoformat(),
            "statistics": self.stats,
            "markers": self.markers,
            "events": self.snapshot(),
        }

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(snapshot_data, f, indent=2)

        logger.info(f"Diagnostics exported to {path}")
        return path

    def clear(self):
        """Clear all buffered events"""
        with self._event_lock:
            self.events.clear()
        logger.debug("Diagnostics buffer cleared")

    def mark_performance(self, marker_name: str, timestamp: Optional[float] = None):
        """
        Add a performance marker for timing critical paths.

        Args:
            marker_name: Name of the marker
            timestamp: Optional timestamp (default: current time)
        """
        if timestamp is None:
            timestamp = time.time()
        self.markers[marker_name] = timestamp

    def measure_elapsed(self, start_marker: str, end_marker: str) -> Optional[float]:
        """
        Measure elapsed time between two markers.

        Returns:
            Elapsed time in milliseconds, or None if markers don't exist
        """
        if start_marker in self.markers and end_marker in self.markers:
            elapsed = (self.markers[end_marker] - self.markers[start_marker]) * 1000
            return elapsed
        return None

    def _console_handler(self, event: DiagnosticEvent):
        """
        Console output handler.

        Only outputs to terminal when TRADING_MODE == "DEBUG".
        In LIVE/SIM modes, terminal is kept clean and quiet.
        Events are still logged to file and UI console in all modes.
        """
        # Check if we should output to console
        if _SETTINGS_AVAILABLE and settings and getattr(settings, "TRADING_MODE", "DEBUG") != "DEBUG":
            # Only print to console in DEBUG mode
            return

        # In DEBUG mode or if settings unavailable (fallback to console output)

        # Color codes for terminal output
        colors = {
            "debug": "\033[36m",  # Cyan
            "info": "\033[32m",  # Green
            "warn": "\033[33m",  # Yellow
            "error": "\033[31m",  # Red
            "fatal": "\033[35m",  # Magenta
            "reset": "\033[0m",
        }

        color = colors.get(event.level, colors["reset"])
        reset = colors["reset"]

        # Format: [CATEGORY] LEVEL: message (context)
        context_str = ""
        if event.context:
            context_str = f" {json.dumps(event.context)}"

        location = f"{event.module}"
        if event.function_name:
            location += f".{event.function_name}"
        if event.line_number:
            location += f":{event.line_number}"

        output = (
            f"{color}[{event.category.upper()}] {event.level.upper()}{reset}: {event.message} ({location}){context_str}"
        )

        # Use stderr for warnings and errors
        stream = sys.stderr if event.level in ["warn", "error", "fatal"] else sys.stdout
        print(output, file=stream)

    def _auto_dump_on_fatal(self, event: DiagnosticEvent):
        """Automatically dump diagnostics on fatal errors"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dump_path = f"logs/crash_dump_{timestamp}.json"
            self.export_json(dump_path)

            # Only print to console in DEBUG mode (fatal errors always logged to file)
            if _SETTINGS_AVAILABLE and settings:
                if getattr(settings, "TRADING_MODE", "DEBUG") == "DEBUG":
                    print(f"[DIAGNOSTICS] Fatal error dump saved to {dump_path}", file=sys.stderr)
            else:
                print(f"[DIAGNOSTICS] Fatal error dump saved to {dump_path}", file=sys.stderr)
        except Exception as e:
            # Fatal dump errors always printed (critical system failure)
            print(f"[DIAGNOSTICS] Failed to create crash dump: {e}", file=sys.stderr)

    def get_statistics(self) -> dict[str, Any]:
        """Get current statistics"""
        with self._event_lock:
            return self.stats.copy()


def log_event(
    category: str,
    level: str,
    message: str,
    event_type: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
    elapsed_ms: Optional[float] = None,
    include_stack: bool = False,
):
    """
    Primary API for logging diagnostic events.

    This function automatically captures caller information (file, line, function)
    and routes the event through the DiagnosticsHub.

    Args:
        category: Event category (core, ui, data, network, analytics, perf)
        level: Event level (debug, info, warn, error, fatal)
        message: Human-readable message
        event_type: Optional event type (e.g., "SocketConnect", "TradeUpdate")
        context: Optional dictionary with additional context
        elapsed_ms: Optional elapsed time in milliseconds
        include_stack: Whether to include stack trace (for errors)

    Example:
        log_event(
            category="network",
            level="info",
            message="DTC connection established",
            event_type="ConnectionSuccess",
            context={"host": "127.0.0.1", "port": 11099}
        )
    """
    # Capture caller information
    frame = inspect.currentframe()
    caller_frame = frame.f_back if frame else None

    file_path = None
    line_number = None
    function_name = None
    module = "unknown"

    if caller_frame:
        file_path = caller_frame.f_code.co_filename
        line_number = caller_frame.f_lineno
        function_name = caller_frame.f_code.co_name

        # Extract module name from file path
        try:
            rel_path = os.path.relpath(file_path, os.getcwd())
            module = rel_path.replace(os.sep, ".").replace(".py", "")
        except ValueError:
            module = os.path.basename(file_path).replace(".py", "")

    # Get thread information
    thread = threading.current_thread()
    thread_id = thread.ident
    thread_name = thread.name

    # Capture stack trace for errors if requested
    stack_trace = None
    if include_stack or level in ["error", "fatal"]:
        stack_trace = traceback.format_stack()
        stack_trace = "".join(stack_trace[:-1])  # Exclude this function

    # Create event
    from datetime import UTC

    event = DiagnosticEvent(
        timestamp=datetime.now(UTC).isoformat(),
        category=category,
        level=level,
        module=module,
        event_type=event_type or "Event",
        message=message,
        context=context or {},
        file_path=file_path,
        line_number=line_number,
        function_name=function_name,
        thread_id=thread_id,
        thread_name=thread_name,
        elapsed_ms=elapsed_ms,
        stack_trace=stack_trace,
    )

    # Emit through hub
    hub = DiagnosticsHub.get_instance()
    hub.emit_event(event)


# Convenience functions for common levels
def debug(category: str, message: str, **kwargs):
    """Log debug event"""
    log_event(category=category, level="debug", message=message, **kwargs)


def info(category: str, message: str, **kwargs):
    """Log info event"""
    log_event(category=category, level="info", message=message, **kwargs)


def warn(category: str, message: str, **kwargs):
    """Log warning event"""
    log_event(category=category, level="warn", message=message, **kwargs)


def error(category: str, message: str, **kwargs):
    """Log error event"""
    log_event(category=category, level="error", message=message, include_stack=True, **kwargs)


def fatal(category: str, message: str, **kwargs):
    """Log fatal event"""
    log_event(category=category, level="fatal", message=message, include_stack=True, **kwargs)


# Performance measurement context manager
class PerformanceMarker:
    """
    Context manager for measuring performance of code blocks.

    Example:
        with PerformanceMarker("database_query", category="data"):
            result = db.execute(query)
    """

    def __init__(self, name: str, category: str = "perf", log_result: bool = True):
        self.name = name
        self.category = category
        self.log_result = log_result
        self.start_time = None
        self.hub = DiagnosticsHub.get_instance()

    def __enter__(self):
        self.start_time = time.time()
        self.hub.mark_performance(f"{self.name}_start", self.start_time)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        self.hub.mark_performance(f"{self.name}_end", end_time)

        elapsed_ms = (end_time - self.start_time) * 1000

        if self.log_result:
            log_event(
                category=self.category,
                level="debug",
                message=f"Performance: {self.name}",
                event_type="PerformanceMeasurement",
                context={"operation": self.name},
                elapsed_ms=elapsed_ms,
            )

        return False  # Don't suppress exceptions


if __name__ == "__main__":
    # Test the diagnostics system
    print("Testing APPSIERRA Diagnostics Subsystem")
    print("=" * 50)

    hub = DiagnosticsHub.get_instance()

    # Test various event types
    info("system", "Diagnostics subsystem initialized", event_type="Init")

    debug("network", "Attempting connection", context={"host": "127.0.0.1", "port": 11099})

    info("data", "Received market data", context={"symbol": "ES", "price": 4500.25})

    warn("ui", "Slow render detected", context={"frame_time_ms": 33.5})

    with PerformanceMarker("test_operation", category="perf"):
        time.sleep(0.1)

    error("core", "Configuration error", context={"missing_key": "API_KEY"})

    # Print statistics
    print("\n" + "=" * 50)
    print("Statistics:")
    print(json.dumps(hub.get_statistics(), indent=2))

    # Export snapshot
    print("\n" + "=" * 50)
    print("Exporting snapshot...")
    hub.export_json("logs/test_diagnostics.json")
    print("Done!")
