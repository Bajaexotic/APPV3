"""
Health Watchdog for APPSIERRA Debug Subsystem

Monitors subsystem health and detects:
- Unresponsive components (heartbeat timeout)
- Resource exhaustion (memory, CPU)
- Event queue backlog
- Performance degradation
- Thread deadlocks

Usage:
    from core.health_watchdog import HealthWatchdog, register_component

    # Register a component for monitoring
    register_component("dtc_client", heartbeat_timeout=30.0)

    # Send heartbeats from the component
    from core.health_watchdog import heartbeat
    heartbeat("dtc_client")

    # Start the watchdog (usually in app initialization)
    watchdog = HealthWatchdog.get_instance()
    watchdog.start()
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
import threading
import time
from typing import Dict, List, Optional

from core.diagnostics import DiagnosticsHub, log_event
from core.error_policy import handle_error
from utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class ComponentHealth:
    """Health status for a monitored component"""

    name: str
    last_heartbeat: float
    heartbeat_timeout: float
    is_healthy: bool = True
    consecutive_failures: int = 0
    total_failures: int = 0
    last_failure_time: Optional[float] = None
    metadata: dict = field(default_factory=dict)

    def is_responsive(self, current_time: float) -> bool:
        """Check if component is responsive based on heartbeat"""
        elapsed = current_time - self.last_heartbeat
        return elapsed < self.heartbeat_timeout

    def update_health(self, is_healthy: bool, current_time: float):
        """Update health status"""
        if not is_healthy:
            self.consecutive_failures += 1
            self.total_failures += 1
            self.last_failure_time = current_time
            self.is_healthy = False
        else:
            self.consecutive_failures = 0
            self.is_healthy = True


@dataclass
class HealthMetrics:
    """System-wide health metrics"""

    timestamp: float
    total_components: int
    healthy_components: int
    unhealthy_components: int
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    event_queue_size: int
    thread_count: int
    active_threads: list[str] = field(default_factory=list)


class HealthWatchdog:
    """
    Monitors system and component health.

    Runs in a background thread and:
    - Checks component heartbeats
    - Monitors resource usage
    - Detects performance issues
    - Triggers alerts on health degradation
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, check_interval: float = 5.0, resource_check_interval: float = 10.0):
        if HealthWatchdog._instance is not None:
            raise RuntimeError("HealthWatchdog is a singleton. Use get_instance().")

        self.check_interval = check_interval
        self.resource_check_interval = resource_check_interval

        # Component registry
        self.components: dict[str, ComponentHealth] = {}
        self.components_lock = threading.Lock()

        # Watchdog thread
        self.thread: Optional[threading.Thread] = None
        self.running = False

        # Resource monitoring
        self.last_resource_check = 0.0
        self.resource_thresholds = {"cpu_percent": 80.0, "memory_percent": 80.0, "event_queue_size": 1000}

        # Diagnostics
        self.hub = DiagnosticsHub.get_instance()

        # Health callbacks
        self.health_callbacks: list[Callable[[HealthMetrics], None]] = []

        logger.info("HealthWatchdog initialized")

    @classmethod
    def get_instance(cls, **kwargs) -> "HealthWatchdog":
        """Get singleton instance (thread-safe)"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(**kwargs)
        return cls._instance

    def register_component(self, name: str, heartbeat_timeout: float = 30.0, metadata: Optional[dict] = None):
        """
        Register a component for health monitoring.

        Args:
            name: Component name (unique identifier)
            heartbeat_timeout: Seconds before component considered unresponsive
            metadata: Optional metadata about the component
        """
        with self.components_lock:
            if name in self.components:
                logger.warning(f"Component {name} already registered, updating config")

            self.components[name] = ComponentHealth(
                name=name, last_heartbeat=time.time(), heartbeat_timeout=heartbeat_timeout, metadata=metadata or {}
            )

        log_event(
            category="system",
            level="info",
            message=f"Component registered for health monitoring: {name}",
            event_type="ComponentRegistered",
            context={"component": name, "timeout": heartbeat_timeout},
        )

    def unregister_component(self, name: str):
        """Unregister a component"""
        with self.components_lock:
            if name in self.components:
                del self.components[name]

        log_event(
            category="system",
            level="info",
            message=f"Component unregistered: {name}",
            event_type="ComponentUnregistered",
            context={"component": name},
        )

    def heartbeat(self, component_name: str, metadata: Optional[dict] = None):
        """
        Record a heartbeat from a component.

        Args:
            component_name: Name of the component
            metadata: Optional metadata to update
        """
        current_time = time.time()

        with self.components_lock:
            if component_name not in self.components:
                logger.warning(f"Heartbeat from unregistered component: {component_name}")
                # Auto-register with default timeout
                self.components[component_name] = ComponentHealth(
                    name=component_name, last_heartbeat=current_time, heartbeat_timeout=30.0
                )
                return

            component = self.components[component_name]
            component.last_heartbeat = current_time

            # Update metadata if provided
            if metadata:
                component.metadata.update(metadata)

            # If component was unhealthy, mark as recovered
            if not component.is_healthy:
                component.update_health(True, current_time)
                log_event(
                    category="system",
                    level="info",
                    message=f"Component recovered: {component_name}",
                    event_type="ComponentRecovered",
                    context={
                        "component": component_name,
                        "downtime_sec": current_time - (component.last_failure_time or 0),
                    },
                )

    def start(self):
        """Start the watchdog thread"""
        if self.running:
            logger.warning("HealthWatchdog already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._watchdog_loop, daemon=True, name="HealthWatchdog")
        self.thread.start()

        log_event(category="system", level="info", message="Health watchdog started", event_type="WatchdogStarted")

    def stop(self):
        """Stop the watchdog thread"""
        if not self.running:
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)

        log_event(category="system", level="info", message="Health watchdog stopped", event_type="WatchdogStopped")

    def _watchdog_loop(self):
        """Main watchdog monitoring loop"""
        while self.running:
            try:
                current_time = time.time()

                # Check component heartbeats
                self._check_component_health(current_time)

                # Check resource usage periodically
                if current_time - self.last_resource_check >= self.resource_check_interval:
                    self._check_resource_health(current_time)
                    self.last_resource_check = current_time

                # Get overall health metrics
                metrics = self._get_health_metrics(current_time)

                # Notify callbacks
                for callback in self.health_callbacks:
                    try:
                        callback(metrics)
                    except Exception as e:
                        logger.error(f"Health callback error: {e}")

                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Watchdog loop error: {e}")
                time.sleep(self.check_interval)

    def _check_component_health(self, current_time: float):
        """Check all component heartbeats"""
        with self.components_lock:
            components = list(self.components.values())

        for component in components:
            is_responsive = component.is_responsive(current_time)

            if not is_responsive and component.is_healthy:
                # Component became unresponsive
                elapsed = current_time - component.last_heartbeat
                component.update_health(False, current_time)

                log_event(
                    category="system",
                    level="error",
                    message=f"Component unresponsive: {component.name}",
                    event_type="ComponentUnresponsive",
                    context={
                        "component": component.name,
                        "timeout": component.heartbeat_timeout,
                        "elapsed": elapsed,
                        "last_heartbeat": datetime.fromtimestamp(component.last_heartbeat).isoformat(),
                    },
                )

                # Trigger error policy
                handle_error(
                    error_type="component_unresponsive",
                    category="system",
                    context={"component": component.name, "elapsed": elapsed},
                )

    def _check_resource_health(self, current_time: float):
        """Check system resource usage"""
        try:
            import psutil

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            if cpu_percent > self.resource_thresholds["cpu_percent"]:
                log_event(
                    category="perf",
                    level="warn",
                    message=f"High CPU usage detected: {cpu_percent:.1f}%",
                    event_type="HighCPU",
                    context={"cpu_percent": cpu_percent},
                )

            # Memory usage
            memory = psutil.virtual_memory()
            if memory.percent > self.resource_thresholds["memory_percent"]:
                log_event(
                    category="perf",
                    level="warn",
                    message=f"High memory usage detected: {memory.percent:.1f}%",
                    event_type="HighMemory",
                    context={"memory_percent": memory.percent, "memory_mb": memory.used / (1024 * 1024)},
                )

            # Event queue size
            queue_size = len(self.hub.events)
            if queue_size > self.resource_thresholds["event_queue_size"]:
                log_event(
                    category="system",
                    level="warn",
                    message=f"Event queue backlog: {queue_size} events",
                    event_type="EventQueueBacklog",
                    context={"queue_size": queue_size},
                )

        except Exception as e:
            logger.error(f"Resource health check error: {e}")

    def _get_health_metrics(self, current_time: float) -> HealthMetrics:
        """Get current health metrics"""
        with self.components_lock:
            total = len(self.components)
            healthy = sum(1 for c in self.components.values() if c.is_healthy)
            unhealthy = total - healthy

        # Get resource metrics
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=0)
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            memory_pct = memory.percent
        except:
            cpu = 0.0
            memory_mb = 0.0
            memory_pct = 0.0

        # Thread info
        active_threads = [t.name for t in threading.enumerate() if t.is_alive()]

        return HealthMetrics(
            timestamp=current_time,
            total_components=total,
            healthy_components=healthy,
            unhealthy_components=unhealthy,
            cpu_percent=cpu,
            memory_mb=memory_mb,
            memory_percent=memory_pct,
            event_queue_size=len(self.hub.events),
            thread_count=threading.active_count(),
            active_threads=active_threads,
        )

    def get_component_status(self, component_name: str) -> Optional[ComponentHealth]:
        """Get health status for a specific component"""
        with self.components_lock:
            return self.components.get(component_name)

    def get_all_statuses(self) -> dict[str, ComponentHealth]:
        """Get health status for all components"""
        with self.components_lock:
            return self.components.copy()

    def register_health_callback(self, callback: Callable[[HealthMetrics], None]):
        """Register a callback to be notified of health updates"""
        if callback not in self.health_callbacks:
            self.health_callbacks.append(callback)

    def unregister_health_callback(self, callback: Callable[[HealthMetrics], None]):
        """Unregister a health callback"""
        if callback in self.health_callbacks:
            self.health_callbacks.remove(callback)


# Convenience functions for global instance
def register_component(name: str, heartbeat_timeout: float = 30.0, metadata: Optional[dict] = None):
    """Register a component with the global watchdog"""
    watchdog = HealthWatchdog.get_instance()
    watchdog.register_component(name, heartbeat_timeout, metadata)


def heartbeat(component_name: str, metadata: Optional[dict] = None):
    """Send a heartbeat from a component"""
    watchdog = HealthWatchdog.get_instance()
    watchdog.heartbeat(component_name, metadata)


def get_component_status(component_name: str) -> Optional[ComponentHealth]:
    """Get status of a component"""
    watchdog = HealthWatchdog.get_instance()
    return watchdog.get_component_status(component_name)


if __name__ == "__main__":
    # Test the health watchdog
    print("Testing Health Watchdog")
    print("=" * 50)

    watchdog = HealthWatchdog.get_instance(check_interval=2.0)

    # Register test components
    register_component("test_component_1", heartbeat_timeout=5.0)
    register_component("test_component_2", heartbeat_timeout=10.0)

    # Start watchdog
    watchdog.start()

    # Send heartbeats
    print("\nSending heartbeats...")
    for i in range(5):
        heartbeat("test_component_1")
        if i % 2 == 0:
            heartbeat("test_component_2")
        time.sleep(2)

    print("\nStopping heartbeats for test_component_1...")
    for i in range(5):
        heartbeat("test_component_2")  # Only component 2 sends heartbeats
        time.sleep(2)

    # Check statuses
    print("\n" + "=" * 50)
    print("Component Statuses:")
    for name, status in watchdog.get_all_statuses().items():
        print(f"  {name}: {'HEALTHY' if status.is_healthy else 'UNHEALTHY'}")
        print(f"    Failures: {status.total_failures}")
        print(f"    Last heartbeat: {datetime.fromtimestamp(status.last_heartbeat).isoformat()}")

    watchdog.stop()
    print("\nTest complete!")
