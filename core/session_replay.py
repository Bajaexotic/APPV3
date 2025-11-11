"""
Session Replay and Forensics for APPSIERRA Debug Subsystem

Provides tools for:
- Loading and replaying event timelines from diagnostic dumps
- Analyzing event patterns and correlations
- Filtering and searching through historical events
- Generating forensic reports

Usage:
    from core.session_replay import SessionReplay

    # Load a session from dump file
    replay = SessionReplay.from_file("logs/debug_snapshot_20250106_123045.json")

    # Playback events in real-time
    replay.playback(speed=10.0, filter_category="network")

    # Analyze patterns
    stats = replay.analyze()
    print(f"Total events: {stats['total_events']}")
    print(f"Error rate: {stats['error_rate']:.2%}")

    # Search for specific events
    results = replay.search(pattern="connection.*failed", category="network")
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from core.diagnostics import DiagnosticEvent
from utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class EventPattern:
    """Detected event pattern or correlation"""

    pattern_type: str
    description: str
    occurrences: int
    example_events: list[dict[str, Any]]
    severity: str = "info"


@dataclass
class SessionAnalysis:
    """Analysis results for a session"""

    total_events: int
    duration_sec: float
    events_per_second: float
    error_rate: float
    fatal_count: int
    categories: dict[str, int]
    levels: dict[str, int]
    patterns: list[EventPattern]
    performance_stats: dict[str, Any]
    timeline_summary: list[tuple[str, int]]  # (time_bucket, event_count)


class SessionReplay:
    """
    Replay and analyze diagnostic event sessions.

    Loads event dumps and provides playback, analysis, and forensic capabilities.
    """

    def __init__(self):
        self.events: list[DiagnosticEvent] = []
        self.metadata: dict[str, Any] = {}
        self.session_start: Optional[str] = None
        self.session_end: Optional[str] = None

    @classmethod
    def from_file(cls, filepath: str) -> "SessionReplay":
        """
        Load session from diagnostic dump file.

        Args:
            filepath: Path to JSON dump file

        Returns:
            SessionReplay instance
        """
        replay = cls()
        replay.load_from_file(filepath)
        return replay

    @classmethod
    def from_events(cls, events: list[dict[str, Any]], metadata: Optional[dict] = None) -> "SessionReplay":
        """
        Create session from event list.

        Args:
            events: List of event dictionaries
            metadata: Optional session metadata

        Returns:
            SessionReplay instance
        """
        replay = cls()
        replay.load_from_dict({"events": events, "metadata": metadata or {}})
        return replay

    def load_from_file(self, filepath: str):
        """Load session data from file"""
        try:
            path = Path(filepath)
            if not path.exists():
                raise FileNotFoundError(f"Dump file not found: {filepath}")

            with open(path) as f:
                data = json.load(f)

            self.load_from_dict(data)
            logger.info(f"Loaded session with {len(self.events)} events from {filepath}")

        except Exception as e:
            logger.error(f"Failed to load session from {filepath}: {e}")
            raise

    def load_from_dict(self, data: dict[str, Any]):
        """Load session data from dictionary"""
        # Extract metadata
        self.session_start = data.get("session_start")
        self.session_end = data.get("session_end")
        self.metadata = {"statistics": data.get("statistics", {}), "markers": data.get("markers", {})}

        # Parse events
        events_data = data.get("events", [])
        self.events = []

        for event_dict in events_data:
            try:
                event = DiagnosticEvent(**event_dict)
                self.events.append(event)
            except Exception as e:
                logger.warning(f"Failed to parse event: {e}")

        # Sort events by timestamp
        self.events.sort(key=lambda e: e.timestamp)

        logger.debug(f"Loaded {len(self.events)} events")

    def playback(
        self,
        speed: float = 1.0,
        filter_category: Optional[str] = None,
        filter_level: Optional[str] = None,
        callback: Optional[Callable[[DiagnosticEvent], None]] = None,
    ):
        """
        Playback events in timeline order.

        Args:
            speed: Playback speed multiplier (1.0 = real-time, 10.0 = 10x faster)
            filter_category: Optional category filter
            filter_level: Optional level filter
            callback: Optional callback for each event
        """
        if not self.events:
            logger.warning("No events to playback")
            return

        logger.info(f"Starting playback at {speed}x speed")
        start_time = time.time()

        # Get first event timestamp as reference
        first_timestamp = self._parse_timestamp(self.events[0].timestamp)

        for event in self.events:
            # Apply filters
            if filter_category and event.category != filter_category:
                continue
            if filter_level and event.level != filter_level:
                continue

            # Calculate delay for real-time playback
            event_timestamp = self._parse_timestamp(event.timestamp)
            elapsed_in_session = (event_timestamp - first_timestamp).total_seconds()
            target_playback_time = elapsed_in_session / speed
            actual_elapsed = time.time() - start_time

            # Sleep if we're ahead of schedule
            delay = target_playback_time - actual_elapsed
            if delay > 0:
                time.sleep(delay)

            # Execute callback
            if callback:
                callback(event)
            else:
                self._default_playback_output(event)

        logger.info("Playback complete")

    def _default_playback_output(self, event: DiagnosticEvent):
        """Default playback output"""
        print(f"[{event.timestamp}] [{event.category}:{event.level}] {event.message}")

    def analyze(self) -> SessionAnalysis:
        """
        Analyze the session and generate statistics.

        Returns:
            SessionAnalysis with comprehensive session statistics
        """
        if not self.events:
            return SessionAnalysis(
                total_events=0,
                duration_sec=0.0,
                events_per_second=0.0,
                error_rate=0.0,
                fatal_count=0,
                categories={},
                levels={},
                patterns=[],
                performance_stats={},
                timeline_summary=[],
            )

        # Basic counts
        total_events = len(self.events)
        categories = defaultdict(int)
        levels = defaultdict(int)
        error_count = 0
        fatal_count = 0

        for event in self.events:
            categories[event.category] += 1
            levels[event.level] += 1

            if event.level == "error":
                error_count += 1
            elif event.level == "fatal":
                fatal_count += 1
                error_count += 1

        # Calculate duration
        first_time = self._parse_timestamp(self.events[0].timestamp)
        last_time = self._parse_timestamp(self.events[-1].timestamp)
        duration_sec = (last_time - first_time).total_seconds()
        events_per_second = total_events / duration_sec if duration_sec > 0 else 0

        # Error rate
        error_rate = error_count / total_events if total_events > 0 else 0

        # Performance stats
        perf_stats = self._analyze_performance()

        # Detect patterns
        patterns = self._detect_patterns()

        # Timeline summary (events per minute)
        timeline = self._create_timeline_summary()

        return SessionAnalysis(
            total_events=total_events,
            duration_sec=duration_sec,
            events_per_second=events_per_second,
            error_rate=error_rate,
            fatal_count=fatal_count,
            categories=dict(categories),
            levels=dict(levels),
            patterns=patterns,
            performance_stats=perf_stats,
            timeline_summary=timeline,
        )

    def _analyze_performance(self) -> dict[str, Any]:
        """Analyze performance-related events"""
        perf_events = [e for e in self.events if e.category == "perf" or e.elapsed_ms is not None]

        if not perf_events:
            return {}

        elapsed_times = [e.elapsed_ms for e in perf_events if e.elapsed_ms is not None]

        if not elapsed_times:
            return {}

        return {
            "total_measurements": len(elapsed_times),
            "min_ms": min(elapsed_times),
            "max_ms": max(elapsed_times),
            "avg_ms": sum(elapsed_times) / len(elapsed_times),
            "p95_ms": self._percentile(elapsed_times, 95),
            "p99_ms": self._percentile(elapsed_times, 99),
        }

    def _percentile(self, data: list[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _detect_patterns(self) -> list[EventPattern]:
        """Detect common patterns in events"""
        patterns = []

        # Pattern 1: Repeated errors
        error_sequences = self._find_error_sequences()
        if error_sequences:
            patterns.append(
                EventPattern(
                    pattern_type="repeated_errors",
                    description=f"Found {len(error_sequences)} sequences of repeated errors",
                    occurrences=len(error_sequences),
                    example_events=[seq[0].to_dict() for seq in error_sequences[:3]],
                    severity="error",
                )
            )

        # Pattern 2: Retry patterns
        retry_events = [e for e in self.events if "retry" in e.message.lower() or "attempt" in e.message.lower()]
        if retry_events:
            patterns.append(
                EventPattern(
                    pattern_type="retry_attempts",
                    description=f"Detected {len(retry_events)} retry attempts",
                    occurrences=len(retry_events),
                    example_events=[e.to_dict() for e in retry_events[:3]],
                    severity="warn",
                )
            )

        # Pattern 3: Performance degradation
        perf_issues = [e for e in self.events if e.elapsed_ms and e.elapsed_ms > 1000]
        if perf_issues:
            patterns.append(
                EventPattern(
                    pattern_type="slow_operations",
                    description=f"Found {len(perf_issues)} operations exceeding 1 second",
                    occurrences=len(perf_issues),
                    example_events=[e.to_dict() for e in perf_issues[:3]],
                    severity="warn",
                )
            )

        return patterns

    def _find_error_sequences(self) -> list[list[DiagnosticEvent]]:
        """Find sequences of consecutive errors"""
        sequences = []
        current_sequence = []

        for event in self.events:
            if event.level in ["error", "fatal"]:
                current_sequence.append(event)
            else:
                if len(current_sequence) >= 3:  # Min 3 consecutive errors
                    sequences.append(current_sequence)
                current_sequence = []

        if len(current_sequence) >= 3:
            sequences.append(current_sequence)

        return sequences

    def _create_timeline_summary(self, bucket_size_sec: int = 60) -> list[tuple[str, int]]:
        """Create timeline summary with event counts per time bucket"""
        if not self.events:
            return []

        timeline = defaultdict(int)
        first_time = self._parse_timestamp(self.events[0].timestamp)

        for event in self.events:
            event_time = self._parse_timestamp(event.timestamp)
            elapsed = (event_time - first_time).total_seconds()
            bucket = int(elapsed // bucket_size_sec) * bucket_size_sec
            timeline[bucket] += 1

        return sorted([(f"{b}s", count) for b, count in timeline.items()])

    def search(
        self,
        pattern: Optional[str] = None,
        category: Optional[str] = None,
        level: Optional[str] = None,
        context_key: Optional[str] = None,
        context_value: Optional[Any] = None,
    ) -> list[DiagnosticEvent]:
        """
        Search for events matching criteria.

        Args:
            pattern: Regex pattern to match against message
            category: Category filter
            level: Level filter
            context_key: Context key to check
            context_value: Context value to match

        Returns:
            List of matching events
        """
        results = []
        pattern_re = re.compile(pattern, re.IGNORECASE) if pattern else None

        for event in self.events:
            # Category filter
            if category and event.category != category:
                continue

            # Level filter
            if level and event.level != level:
                continue

            # Pattern filter
            if pattern_re and not pattern_re.search(event.message):
                continue

            # Context filters
            if context_key is not None:
                if context_key not in event.context:
                    continue
                if context_value is not None and event.context[context_key] != context_value:
                    continue

            results.append(event)

        return results

    def generate_report(self, output_file: Optional[str] = None) -> str:
        """
        Generate a forensic report.

        Args:
            output_file: Optional file path to save report

        Returns:
            Report as markdown string
        """
        analysis = self.analyze()

        report_lines = [
            "# Session Forensic Report",
            "",
            f"**Generated:** {datetime.now().isoformat()}",
            f"**Session Start:** {self.session_start or 'Unknown'}",
            f"**Session End:** {self.session_end or 'Unknown'}",
            "",
            "## Summary",
            "",
            f"- **Total Events:** {analysis.total_events}",
            f"- **Duration:** {analysis.duration_sec:.2f} seconds",
            f"- **Events/Second:** {analysis.events_per_second:.2f}",
            f"- **Error Rate:** {analysis.error_rate:.2%}",
            f"- **Fatal Errors:** {analysis.fatal_count}",
            "",
            "## Events by Category",
            "",
        ]

        for category, count in sorted(analysis.categories.items(), key=lambda x: x[1], reverse=True):
            pct = (count / analysis.total_events) * 100
            report_lines.append(f"- **{category}:** {count} ({pct:.1f}%)")

        report_lines.extend(["", "## Events by Level", ""])

        for level, count in sorted(analysis.levels.items(), key=lambda x: x[1], reverse=True):
            pct = (count / analysis.total_events) * 100
            report_lines.append(f"- **{level}:** {count} ({pct:.1f}%)")

        if analysis.performance_stats:
            report_lines.extend(
                [
                    "",
                    "## Performance Statistics",
                    "",
                    f"- **Total Measurements:** {analysis.performance_stats.get('total_measurements', 0)}",
                    f"- **Min:** {analysis.performance_stats.get('min_ms', 0):.2f} ms",
                    f"- **Max:** {analysis.performance_stats.get('max_ms', 0):.2f} ms",
                    f"- **Average:** {analysis.performance_stats.get('avg_ms', 0):.2f} ms",
                    f"- **P95:** {analysis.performance_stats.get('p95_ms', 0):.2f} ms",
                    f"- **P99:** {analysis.performance_stats.get('p99_ms', 0):.2f} ms",
                ]
            )

        if analysis.patterns:
            report_lines.extend(["", "## Detected Patterns", ""])

            for pattern in analysis.patterns:
                report_lines.extend(
                    [
                        f"### {pattern.pattern_type.replace('_', ' ').title()}",
                        "",
                        f"**Description:** {pattern.description}",
                        f"**Severity:** {pattern.severity}",
                        "",
                    ]
                )

        report = "\n".join(report_lines)

        if output_file:
            Path(output_file).write_text(report)
            logger.info(f"Report saved to {output_file}")

        return report

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse ISO timestamp"""
        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except:
            return datetime.now()


if __name__ == "__main__":
    # Test session replay
    print("Testing Session Replay")
    print("=" * 50)

    # Create sample session data
    sample_events = [
        {
            "timestamp": "2025-01-06T12:00:00.000Z",
            "category": "system",
            "level": "info",
            "module": "core.app",
            "event_type": "AppStart",
            "message": "Application started",
            "context": {},
        },
        {
            "timestamp": "2025-01-06T12:00:05.000Z",
            "category": "network",
            "level": "error",
            "module": "services.dtc",
            "event_type": "ConnectionFailed",
            "message": "Connection failed",
            "context": {"host": "127.0.0.1"},
            "elapsed_ms": 5000.0,
        },
        {
            "timestamp": "2025-01-06T12:00:10.000Z",
            "category": "network",
            "level": "info",
            "module": "services.dtc",
            "event_type": "ConnectionSuccess",
            "message": "Connection established",
            "context": {"host": "127.0.0.1"},
            "elapsed_ms": 1500.0,
        },
    ]

    # Load session
    replay = SessionReplay.from_events(sample_events)

    # Analyze
    analysis = replay.analyze()
    print(f"\nTotal events: {analysis.total_events}")
    print(f"Duration: {analysis.duration_sec:.2f}s")
    print(f"Error rate: {analysis.error_rate:.2%}")
    print(f"\nCategories: {analysis.categories}")
    print(f"Levels: {analysis.levels}")

    # Generate report
    print("\n" + "=" * 50)
    print("Forensic Report:")
    print("=" * 50)
    report = replay.generate_report()
    print(report)
