"""
Error Policy Manager for APPSIERRA Debug Subsystem

This module implements the error policy matrix, loading policies from YAML
configuration and providing recovery enforcement.

Usage:
    from core.error_policy import handle_error, ErrorPolicyManager

    # Handle an error with automatic policy enforcement
    handle_error(
        error_type="dtc_connection_drop",
        category="network",
        context={"host": "127.0.0.1", "port": 11099}
    )

    # Get policy for custom handling
    policy = ErrorPolicyManager.get_instance().get_policy("json_parse_failure", "data")
    if policy.should_retry():
        # Custom retry logic
        pass
"""

from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
import time
from typing import Any, Dict, Optional

import yaml

from core.diagnostics import DiagnosticsHub, log_event
from utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class ErrorPolicy:
    """
    Error policy configuration for a specific error type.

    Defines how the system should respond to an error:
    - What recovery action to take
    - Whether to escalate (notify user/higher severity logging)
    - Whether to dump diagnostic snapshot
    - Retry configuration (if applicable)
    """

    error_type: str
    category: str
    recovery: str
    escalation: bool
    dump_snapshot: bool
    severity: str
    message: str
    max_retries: int = 0
    backoff_ms: int = 1000
    threshold_ms: Optional[int] = None
    threshold_percent: Optional[int] = None

    def should_retry(self) -> bool:
        """Check if this policy supports retries"""
        return self.recovery in ["auto_retry", "cancel_retry"] and self.max_retries > 0

    def should_escalate(self) -> bool:
        """Check if this error should be escalated"""
        return self.escalation

    def should_dump(self) -> bool:
        """Check if diagnostic snapshot should be created"""
        return self.dump_snapshot

    def get_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay for given attempt.

        Args:
            attempt: Retry attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        if not self.should_retry():
            return 0.0

        # Exponential backoff: base_ms * (2 ** attempt)
        delay_ms = self.backoff_ms * (2**attempt)
        return delay_ms / 1000.0

    def to_dict(self) -> dict[str, Any]:
        """Convert policy to dictionary"""
        return {
            "error_type": self.error_type,
            "category": self.category,
            "recovery": self.recovery,
            "escalation": self.escalation,
            "dump_snapshot": self.dump_snapshot,
            "severity": self.severity,
            "message": self.message,
            "max_retries": self.max_retries,
            "backoff_ms": self.backoff_ms,
        }


class ErrorPolicyManager:
    """
    Singleton manager for error policies.

    Loads policies from YAML configuration and provides lookup/enforcement.
    """

    _instance = None
    _lock = None

    def __init__(self, policy_file: Optional[str] = None):
        if ErrorPolicyManager._instance is not None:
            raise RuntimeError("ErrorPolicyManager is a singleton. Use get_instance().")

        self.policies: dict[str, dict[str, ErrorPolicy]] = {}
        self.default_policy: Optional[ErrorPolicy] = None

        # Load policies
        if policy_file is None:
            policy_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "debug_policies.yml")

        self._load_policies(policy_file)
        logger.info(f"ErrorPolicyManager initialized with {self._count_policies()} policies")

    @classmethod
    def get_instance(cls, policy_file: Optional[str] = None) -> "ErrorPolicyManager":
        """Get singleton instance (thread-safe)"""
        import threading

        if cls._lock is None:
            cls._lock = threading.Lock()

        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(policy_file)
        return cls._instance

    def _load_policies(self, policy_file: str):
        """Load policies from YAML file"""
        try:
            policy_path = Path(policy_file)
            if not policy_path.exists():
                logger.warning(f"Policy file not found: {policy_file}, using defaults")
                self._create_default_policies()
                return

            with open(policy_path) as f:
                config = yaml.safe_load(f)

            if not isinstance(config, dict):
                logger.error("Invalid policy file format, using defaults")
                self._create_default_policies()
                return

            # Parse policies by category
            for category, error_types in config.items():
                if category == "default":
                    # Handle default policy
                    if "unknown_error" in error_types:
                        self.default_policy = self._parse_policy(
                            "unknown_error", "default", error_types["unknown_error"]
                        )
                    continue

                if not isinstance(error_types, dict):
                    continue

                if category not in self.policies:
                    self.policies[category] = {}

                for error_type, policy_config in error_types.items():
                    policy = self._parse_policy(error_type, category, policy_config)
                    if policy:
                        self.policies[category][error_type] = policy

            logger.info(f"Loaded {self._count_policies()} error policies from {policy_file}")

        except Exception as e:
            logger.error(f"Failed to load policy file: {e}, using defaults")
            self._create_default_policies()

    def _parse_policy(self, error_type: str, category: str, config: dict[str, Any]) -> Optional[ErrorPolicy]:
        """Parse a single policy from configuration"""
        try:
            return ErrorPolicy(
                error_type=error_type,
                category=category,
                recovery=config.get("recovery", "log_continue"),
                escalation=config.get("escalation", True),
                dump_snapshot=config.get("dump_snapshot", False),
                severity=config.get("severity", "error"),
                message=config.get("message", f"{category} error: {error_type}"),
                max_retries=config.get("max_retries", 0),
                backoff_ms=config.get("backoff_ms", 1000),
                threshold_ms=config.get("threshold_ms"),
                threshold_percent=config.get("threshold_percent"),
            )
        except Exception as e:
            logger.error(f"Failed to parse policy {category}.{error_type}: {e}")
            return None

    def _create_default_policies(self):
        """Create minimal default policies when config is missing"""
        self.default_policy = ErrorPolicy(
            error_type="unknown_error",
            category="default",
            recovery="log_continue",
            escalation=True,
            dump_snapshot=True,
            severity="error",
            message="Unknown error occurred",
        )

    def _count_policies(self) -> int:
        """Count total number of loaded policies"""
        count = 0
        for category_policies in self.policies.values():
            count += len(category_policies)
        return count

    def get_policy(self, error_type: str, category: str) -> ErrorPolicy:
        """
        Get policy for specific error type.

        Args:
            error_type: Error type (e.g., "dtc_connection_drop")
            category: Error category (e.g., "network")

        Returns:
            ErrorPolicy instance (default if not found)
        """
        if category in self.policies and error_type in self.policies[category]:
            return self.policies[category][error_type]

        # Return default policy
        return self.default_policy or ErrorPolicy(
            error_type=error_type,
            category=category,
            recovery="log_continue",
            escalation=True,
            dump_snapshot=False,
            severity="error",
            message=f"Error: {category}.{error_type}",
        )

    def list_policies(self, category: Optional[str] = None) -> dict[str, Any]:
        """
        List all policies or policies for specific category.

        Args:
            category: Optional category filter

        Returns:
            Dictionary of policies
        """
        if category:
            return {error_type: policy.to_dict() for error_type, policy in self.policies.get(category, {}).items()}
        else:
            return {
                cat: {error_type: policy.to_dict() for error_type, policy in cat_policies.items()}
                for cat, cat_policies in self.policies.items()
            }


class ErrorHandler:
    """
    Handles errors with policy enforcement and automatic recovery.
    """

    def __init__(self, policy_manager: Optional[ErrorPolicyManager] = None):
        self.policy_manager = policy_manager or ErrorPolicyManager.get_instance()
        self.hub = DiagnosticsHub.get_instance()

    def handle(
        self,
        error_type: str,
        category: str,
        exception: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
        operation: Optional[Callable] = None,
    ) -> bool:
        """
        Handle an error according to its policy.

        Args:
            error_type: Type of error (e.g., "dtc_connection_drop")
            category: Error category (e.g., "network")
            exception: Optional exception object
            context: Optional context dictionary
            operation: Optional callable to retry (for auto_retry policies)

        Returns:
            True if error was handled successfully, False otherwise
        """
        policy = self.policy_manager.get_policy(error_type, category)

        # Build context
        event_context = context.copy() if context else {}
        event_context["error_type"] = error_type
        event_context["recovery"] = policy.recovery

        if exception:
            event_context["exception"] = str(exception)
            event_context["exception_type"] = type(exception).__name__

        # Log the error
        log_event(
            category=category,
            level=policy.severity,
            message=policy.message,
            event_type=error_type,
            context=event_context,
            include_stack=(policy.severity in ["error", "fatal"]),
        )

        # Dump snapshot if policy requires
        if policy.should_dump():
            try:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                dump_path = f"logs/error_dump_{category}_{error_type}_{timestamp}.json"
                self.hub.export_json(dump_path)
                logger.debug(f"Error snapshot saved to {dump_path}")
            except Exception as e:
                logger.error(f"Failed to create error snapshot: {e}")

        # Execute recovery action
        return self._execute_recovery(policy, operation, context or {})

    def _execute_recovery(self, policy: ErrorPolicy, operation: Optional[Callable], context: dict[str, Any]) -> bool:
        """
        Execute the recovery action specified by policy.

        Returns:
            True if recovery successful, False otherwise
        """
        recovery = policy.recovery

        if recovery in ["auto_retry", "cancel_retry"]:
            if operation is None:
                logger.warning("Retry policy specified but no operation provided")
                return False
            return self._retry_with_backoff(policy, operation, context)

        elif recovery in ["log_continue", "continue"]:
            return True

        elif recovery in ["skip_message", "log_skip", "skip"]:
            logger.debug(f"Skipping operation due to policy: {recovery}")
            return False

        elif recovery == "abort":
            logger.error("Aborting due to policy")
            return False

        else:
            logger.warning(f"Unknown recovery action: {recovery}")
            return False

    def _retry_with_backoff(self, policy: ErrorPolicy, operation: Callable, context: dict[str, Any]) -> bool:
        """
        Retry operation with exponential backoff.

        Returns:
            True if operation succeeded, False if all retries exhausted
        """
        for attempt in range(policy.max_retries):
            if attempt > 0:
                delay = policy.get_backoff_delay(attempt - 1)
                log_event(
                    category=policy.category,
                    level="debug",
                    message=f"Retry attempt {attempt + 1}/{policy.max_retries}",
                    event_type="RetryAttempt",
                    context={"attempt": attempt + 1, "max_retries": policy.max_retries, "delay_sec": delay},
                )
                time.sleep(delay)

            try:
                result = operation()
                if result or result is None:  # Consider None as success
                    log_event(
                        category=policy.category,
                        level="info",
                        message=f"Operation succeeded on attempt {attempt + 1}",
                        event_type="RetrySuccess",
                        context={"attempts": attempt + 1},
                    )
                    return True
            except Exception as e:
                log_event(
                    category=policy.category,
                    level="warn",
                    message=f"Retry attempt {attempt + 1} failed: {e}",
                    event_type="RetryFailed",
                    context={"attempt": attempt + 1, "exception": str(e)},
                )

        log_event(
            category=policy.category,
            level="error",
            message=f"All {policy.max_retries} retry attempts exhausted",
            event_type="RetryExhausted",
            context={"max_retries": policy.max_retries},
        )
        return False


# Global error handler instance
_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def handle_error(
    error_type: str,
    category: str,
    exception: Optional[Exception] = None,
    context: Optional[dict[str, Any]] = None,
    operation: Optional[Callable] = None,
) -> bool:
    """
    Convenience function to handle errors with policy enforcement.

    Example:
        def connect_to_dtc():
            # ... connection logic ...
            pass

        success = handle_error(
            error_type="dtc_connection_drop",
            category="network",
            context={"host": "127.0.0.1"},
            operation=connect_to_dtc
        )
    """
    handler = get_error_handler()
    return handler.handle(error_type, category, exception, context, operation)


if __name__ == "__main__":
    # Test error policy system
    print("Testing Error Policy Manager")
    print("=" * 50)

    manager = ErrorPolicyManager.get_instance()

    # Test policy lookup
    policy = manager.get_policy("dtc_connection_drop", "network")
    print("\nPolicy for dtc_connection_drop:")
    print(f"  Recovery: {policy.recovery}")
    print(f"  Max retries: {policy.max_retries}")
    print(f"  Escalation: {policy.escalation}")
    print(f"  Dump snapshot: {policy.dump_snapshot}")

    # Test error handling
    print("\n" + "=" * 50)
    print("Testing error handling with retry:")

    attempt_count = [0]

    def failing_operation():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise Exception(f"Simulated failure {attempt_count[0]}")
        return True

    success = handle_error(
        error_type="dtc_connection_drop", category="network", context={"host": "127.0.0.1"}, operation=failing_operation
    )

    print(f"\nOperation result: {'SUCCESS' if success else 'FAILED'}")
    print(f"Total attempts: {attempt_count[0]}")
