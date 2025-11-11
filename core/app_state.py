"""
Global state manager accessor for the application.

This module provides a singleton accessor pattern for the StateManager instance,
allowing any part of the application to access the central state without requiring
explicit dependency injection.

Usage:
    from core.app_state import get_state_manager, set_state_manager

    # During app initialization (app_manager.py):
    state = StateManager()
    set_state_manager(state)

    # Anywhere in the app:
    state = get_state_manager()
    if state:
        mode = state.current_mode
"""

from __future__ import annotations

from typing import Optional

from core.state_manager import StateManager


# Global singleton instance
_state_manager: Optional[StateManager] = None


def get_state_manager() -> Optional[StateManager]:
    """
    Get the global StateManager instance.

    Returns:
        StateManager instance or None if not initialized
    """
    return _state_manager


def set_state_manager(state: StateManager) -> None:
    """
    Set the global StateManager instance.

    This should be called once during application initialization.

    Args:
        state: The StateManager instance to use globally
    """
    global _state_manager
    _state_manager = state


def reset_state_manager() -> None:
    """
    Reset the global StateManager instance.

    Useful for testing or application restart.
    """
    global _state_manager
    _state_manager = None
