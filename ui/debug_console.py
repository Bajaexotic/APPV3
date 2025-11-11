"""
Debug Console UI for APPSIERRA

A dockable developer console that provides:
- Live event stream with color-coding
- Category and level filtering
- System statistics (CPU, memory, network)
- Debug flag toggles
- Export and snapshot controls

Accessible via Ctrl+Shift+D hotkey.

Usage:
    from ui.debug_console import DebugConsole

    # In main window initialization
    console = DebugConsole(parent=self)
    self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, console)

    # Connect hotkey
    shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
    shortcut.activated.connect(console.toggle_visibility)
"""

from datetime import datetime
import json
import os
import platform
import time
from typing import Optional, Set

import psutil
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QFont, QKeySequence, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.diagnostics import DiagnosticEvent, DiagnosticsHub, EventCategory, EventLevel
from utils.logger import get_logger


logger = get_logger(__name__)


class SystemMonitor(QThread):
    """
    Background thread for monitoring system metrics.

    Emits signals with current CPU%, memory usage, and other metrics.
    """

    stats_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.running = False
        self.update_interval = 1.0  # seconds
        self.process = psutil.Process()

    def run(self):
        """Monitor loop"""
        self.running = True
        while self.running:
            try:
                stats = {
                    "cpu_percent": self.process.cpu_percent(interval=0.1),
                    "memory_mb": self.process.memory_info().rss / (1024 * 1024),
                    "memory_percent": self.process.memory_percent(),
                    "threads": self.process.num_threads(),
                    "timestamp": datetime.now().isoformat(),
                }

                # System-wide stats
                stats["system_cpu"] = psutil.cpu_percent(interval=0)
                stats["system_memory"] = psutil.virtual_memory().percent

                self.stats_updated.emit(stats)

            except Exception as e:
                logger.error(f"System monitor error: {e}")

            time.sleep(self.update_interval)

    def stop(self):
        """Stop monitoring"""
        self.running = False
        self.wait()


class EventStreamHandler:
    """
    Handler for routing diagnostic events to the UI console.
    """

    def __init__(self, console: "DebugConsole"):
        self.console = console

    def __call__(self, event: DiagnosticEvent):
        """Handle incoming event"""
        # This runs in the event emitter's thread
        # Use Qt signal to update UI in main thread
        self.console.event_received.emit(event)


class DebugConsole(QDockWidget):
    """
    Main debug console widget.

    Features:
    - Live event log with filtering
    - System statistics display
    - Debug flag toggles
    - Export and clear controls
    """

    # Signals
    event_received = pyqtSignal(DiagnosticEvent)

    # Color scheme
    LEVEL_COLORS = {
        "debug": QColor(100, 200, 255),  # Light blue
        "info": QColor(100, 255, 100),  # Light green
        "warn": QColor(255, 200, 100),  # Yellow
        "error": QColor(255, 100, 100),  # Light red
        "fatal": QColor(255, 100, 255),  # Magenta
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Debug Console", parent)

        self.hub = DiagnosticsHub.get_instance()
        self.handler = EventStreamHandler(self)

        # Filter state
        self.enabled_categories: set[str] = {cat.value for cat in EventCategory}
        self.enabled_levels: set[str] = {level.value for level in EventLevel}
        self.max_events = 500
        self.event_count = 0

        # System monitor
        self.system_monitor = SystemMonitor()

        # Build UI
        self._build_ui()

        # Connect signals
        self.event_received.connect(self._on_event_received)
        self.system_monitor.stats_updated.connect(self._on_stats_updated)

        # Register with diagnostics hub
        self.hub.router.register_handler(self.handler)

        # Start system monitoring
        self.system_monitor.start()

        logger.info("Debug Console initialized")

    def _build_ui(self):
        """Build the UI layout"""
        # Main widget
        main_widget = QWidget()
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        self.setWidget(main_widget)

        # Top controls
        controls_layout = self._build_controls()
        layout.addLayout(controls_layout)

        # Stats display
        self.stats_group = self._build_stats_group()
        layout.addWidget(self.stats_group)

        # Event log
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 9))
        self.log_display.setStyleSheet(
            """
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
            }
        """
        )
        layout.addWidget(self.log_display, stretch=1)

        # Set window properties
        self.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
            | Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.setMinimumHeight(200)

    def _build_controls(self) -> QHBoxLayout:
        """Build control buttons and filters"""
        layout = QHBoxLayout()

        # Clear button
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear_log)
        layout.addWidget(clear_btn)

        # Export button
        export_btn = QPushButton("Export Snapshot")
        export_btn.clicked.connect(self.export_snapshot)
        layout.addWidget(export_btn)

        # Pause/Resume button
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.clicked.connect(self._on_pause_toggled)
        layout.addWidget(self.pause_btn)

        # Level filter
        level_label = QLabel("Level:")
        layout.addWidget(level_label)

        self.level_combo = QComboBox()
        self.level_combo.addItem("ALL")
        for level in EventLevel:
            self.level_combo.addItem(level.value.upper())
        self.level_combo.currentTextChanged.connect(self._on_level_filter_changed)
        layout.addWidget(self.level_combo)

        # Category filter
        category_label = QLabel("Category:")
        layout.addWidget(category_label)

        self.category_combo = QComboBox()
        self.category_combo.addItem("ALL")
        for category in EventCategory:
            self.category_combo.addItem(category.value)
        self.category_combo.currentTextChanged.connect(self._on_category_filter_changed)
        layout.addWidget(self.category_combo)

        # Max events spinner
        max_label = QLabel("Max Events:")
        layout.addWidget(max_label)

        self.max_events_spin = QSpinBox()
        self.max_events_spin.setRange(100, 10000)
        self.max_events_spin.setValue(self.max_events)
        self.max_events_spin.setSingleStep(100)
        self.max_events_spin.valueChanged.connect(self._on_max_events_changed)
        layout.addWidget(self.max_events_spin)

        layout.addStretch()

        return layout

    def _build_stats_group(self) -> QGroupBox:
        """Build statistics display group"""
        group = QGroupBox("System Statistics")
        layout = QHBoxLayout()
        group.setLayout(layout)

        # Labels for stats
        self.cpu_label = QLabel("CPU: --")
        self.memory_label = QLabel("Memory: --")
        self.events_label = QLabel("Events: 0")
        self.errors_label = QLabel("Errors: 0")

        layout.addWidget(self.cpu_label)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.memory_label)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.events_label)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.errors_label)
        layout.addStretch()

        return group

    def _on_event_received(self, event: DiagnosticEvent):
        """Handle incoming event (called in main thread)"""
        # Check if paused
        if self.pause_btn.isChecked():
            return

        # Apply filters
        if event.category not in self.enabled_categories:
            return
        if event.level not in self.enabled_levels:
            return

        # Increment counter
        self.event_count += 1

        # Format and display event
        self._append_event(event)

        # Limit buffer size
        if self.event_count > self.max_events:
            self._trim_log()

        # Update event count
        stats = self.hub.get_statistics()
        self.events_label.setText(f"Events: {stats['total_events']}")
        self.errors_label.setText(f"Errors: {stats['errors_count']}")

    def _append_event(self, event: DiagnosticEvent):
        """Append event to log display"""
        # Format timestamp
        try:
            dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
            timestamp = dt.strftime("%H:%M:%S.%f")[:-3]
        except:
            timestamp = event.timestamp[:12]

        # Get color for level
        color = self.LEVEL_COLORS.get(event.level, QColor(255, 255, 255))

        # Format message
        location = f"{event.module}"
        if event.function_name:
            location += f".{event.function_name}"
        if event.line_number:
            location += f":{event.line_number}"

        context_str = ""
        if event.context:
            # Compact JSON representation
            context_str = json.dumps(event.context, separators=(",", ":"))
            if len(context_str) > 100:
                context_str = context_str[:97] + "..."

        # Build HTML formatted message
        html = f"""
        <div style="font-family: Consolas, monospace; font-size: 9pt;">
            <span style="color: #808080;">[{timestamp}]</span>
            <span style="color: #{color.red():02x}{color.green():02x}{color.blue():02x}; font-weight: bold;">
                [{event.category.upper()}:{event.level.upper()}]
            </span>
            <span style="color: #d4d4d4;">{event.message}</span>
            <span style="color: #808080;">({location})</span>
            {f'<span style="color: #569cd6;"> {context_str}</span>' if context_str else ''}
        </div>
        """

        # Append to display
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_display.setTextCursor(cursor)
        self.log_display.insertHtml(html)

        # Auto-scroll to bottom
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _trim_log(self):
        """Trim log to max_events size"""
        # Simple approach: clear when 2x limit reached
        if self.event_count > self.max_events * 2:
            self.log_display.clear()
            self.event_count = 0
            self.log_display.append('<span style="color: #808080;">[Log trimmed to prevent overflow]</span>')

    def _on_stats_updated(self, stats: dict):
        """Update system statistics display"""
        cpu = stats.get("cpu_percent", 0)
        memory_mb = stats.get("memory_mb", 0)
        memory_pct = stats.get("memory_percent", 0)

        # Color code CPU usage
        cpu_color = "green"
        if cpu > 50:
            cpu_color = "orange"
        if cpu > 80:
            cpu_color = "red"

        # Color code memory usage
        mem_color = "green"
        if memory_pct > 50:
            mem_color = "orange"
        if memory_pct > 80:
            mem_color = "red"

        self.cpu_label.setText(f'<span style="color: {cpu_color};">CPU: {cpu:.1f}%</span>')
        self.memory_label.setText(
            f'<span style="color: {mem_color};">Memory: {memory_mb:.1f} MB ({memory_pct:.1f}%)</span>'
        )

    def _on_pause_toggled(self, checked: bool):
        """Handle pause/resume toggle"""
        if checked:
            self.pause_btn.setText("Resume")
        else:
            self.pause_btn.setText("Pause")

    def _on_level_filter_changed(self, level_text: str):
        """Handle level filter change"""
        if level_text == "ALL":
            self.enabled_levels = {level.value for level in EventLevel}
        else:
            self.enabled_levels = {level_text.lower()}

    def _on_category_filter_changed(self, category_text: str):
        """Handle category filter change"""
        if category_text == "ALL":
            self.enabled_categories = {cat.value for cat in EventCategory}
        else:
            self.enabled_categories = {category_text}

    def _on_max_events_changed(self, value: int):
        """Handle max events change"""
        self.max_events = value

    def clear_log(self):
        """Clear the log display"""
        self.log_display.clear()
        self.event_count = 0
        logger.debug("Debug console log cleared")

    def export_snapshot(self):
        """Export diagnostic snapshot"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/debug_snapshot_{timestamp}.json"
            self.hub.export_json(filename)

            # Show confirmation in log
            self.log_display.append(f'<span style="color: #4ec9b0;">[EXPORTED] Snapshot saved to {filename}</span>')

            logger.info(f"Debug snapshot exported to {filename}")

        except Exception as e:
            self.log_display.append(f'<span style="color: red;">[ERROR] Failed to export: {e}</span>')
            logger.error(f"Failed to export snapshot: {e}")

    def toggle_visibility(self):
        """Toggle console visibility"""
        self.setVisible(not self.isVisible())

    def closeEvent(self, event):
        """Clean up on close"""
        # Stop system monitor
        self.system_monitor.stop()

        # Unregister handler
        self.hub.router.unregister_handler(self.handler)

        super().closeEvent(event)


if __name__ == "__main__":
    # Test the debug console
    import sys

    from PyQt6.QtWidgets import QApplication, QMainWindow

    from core.diagnostics import debug, error, info, warn

    app = QApplication(sys.argv)

    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Debug Console Test")
    window.resize(1200, 800)

    # Create and dock console
    console = DebugConsole(window)
    window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, console)

    # Generate some test events
    def generate_test_events():
        info("system", "Application started", event_type="AppStart")
        debug("network", "Connecting to DTC", context={"host": "127.0.0.1", "port": 11099})
        info("data", "Market data received", context={"symbol": "ES", "price": 4500.25})
        warn("ui", "Slow render detected", context={"frame_time_ms": 35.5})
        error("core", "Configuration error", context={"missing_key": "API_KEY"})

    # Generate events after a short delay
    QTimer.singleShot(500, generate_test_events)

    # Show window
    window.show()

    sys.exit(app.exec())
