"""
Theme-Aware Mixin - Standardized theme refresh for widgets and panels

Eliminates duplicate refresh_theme() methods by providing a reusable base.
All theme-aware widgets should inherit from ThemeAwareMixin.

Usage:
    from utils.theme_mixin import ThemeAwareMixin

    class MyWidget(QtWidgets.QWidget, ThemeAwareMixin):
        def __init__(self):
            super().__init__()
            self.setObjectName("MyWidget")
            self._setup_theme()

        def _build_theme_stylesheet(self) -> str:
            return f'''
                QWidget#MyWidget {{
                    background: {THEME.get('card_bg')};
                    border-radius: {THEME.get('card_radius')}px;
                }}
            '''
"""

from collections.abc import Callable
from typing import List, Optional

from PyQt6 import QtWidgets

from config.theme import THEME


class ThemeAwareMixin:
    """
    Mixin providing standardized theme refresh functionality.

    This mixin eliminates duplicate refresh_theme() implementations by:
    1. Providing a base refresh_theme() that rebuilds stylesheets
    2. Supporting delegation to child widgets
    3. Allowing custom refresh logic via hooks

    Subclasses should override:
    - _build_theme_stylesheet() - Return widget's stylesheet (most common)
    - _get_theme_children() - Return list of children to refresh (for containers)
    - _on_theme_refresh() - Custom logic after stylesheet update (optional)
    """

    def _setup_theme(self) -> None:
        """
        Initialize theme support (call in __init__).

        This applies the initial stylesheet.
        """
        self.refresh_theme()

    def refresh_theme(self) -> None:
        """
        Refresh theme styling on this widget and children.

        This is the main entry point called when theme changes.
        Override _build_theme_stylesheet() to customize behavior.
        """
        # Step 1: Update this widget's stylesheet
        stylesheet = self._build_theme_stylesheet()
        if stylesheet:
            if isinstance(self, QtWidgets.QWidget):
                self.setStyleSheet(stylesheet)

        # Step 2: Refresh child widgets
        children = self._get_theme_children()
        if children:
            for child in children:
                if hasattr(child, "refresh_theme"):
                    child.refresh_theme()

        # Step 3: Custom refresh logic (hook for subclasses)
        self._on_theme_refresh()

        # Step 4: Trigger repaint if this is a widget
        if isinstance(self, QtWidgets.QWidget):
            self.update()

    def _build_theme_stylesheet(self) -> str:
        """
        Build stylesheet for this widget using current THEME.

        Override this in subclasses to provide custom stylesheets.

        Returns:
            Stylesheet string, or empty string if no stylesheet needed

        Example:
            def _build_theme_stylesheet(self) -> str:
                return f'''
                    QWidget#MyWidget {{
                        background: {THEME.get('card_bg')};
                        color: {THEME.get('ink')};
                    }}
                '''
        """
        return ""

    def _get_theme_children(self) -> list:
        """
        Return list of child widgets that should have refresh_theme() called.

        Override this for container widgets that manage themed children.

        Returns:
            List of child widgets (must have refresh_theme() method)

        Example:
            def _get_theme_children(self) -> List:
                return [self.header, self.body, self.footer]
        """
        return []

    def _on_theme_refresh(self) -> None:
        """
        Hook for custom theme refresh logic.

        Override this to add custom behavior after stylesheet update.
        Useful for widgets that need to update internal state or colors.

        Example:
            def _on_theme_refresh(self) -> None:
                self._update_icon_colors()
                self._recalculate_layout()
        """
        pass


class ThemedPanel(QtWidgets.QWidget, ThemeAwareMixin):
    """
    Base class for themed panels.

    Provides automatic panel background styling.
    Override _build_theme_stylesheet() to add custom panel styling.
    """

    def __init__(self, panel_name: str = "ThemedPanel"):
        super().__init__()
        self.setObjectName(panel_name)
        self._panel_name = panel_name
        self._setup_theme()

    def _build_theme_stylesheet(self) -> str:
        """Default panel stylesheet with THEME background."""
        return f"QWidget#{self._panel_name} {{ background:{THEME.get('bg_panel')}; }}"


class ThemedWidget(QtWidgets.QWidget, ThemeAwareMixin):
    """
    Base class for themed widgets (cards, buttons, etc.).

    Provides automatic card background and border styling.
    Override _build_theme_stylesheet() for custom widget styling.
    """

    def __init__(self, widget_name: str = "ThemedWidget"):
        super().__init__()
        self.setObjectName(widget_name)
        self._widget_name = widget_name
        self._setup_theme()

    def _build_theme_stylesheet(self) -> str:
        """Default widget stylesheet with card background and border."""
        radius = int(THEME.get("card_radius", 8))
        card_bg = THEME.get("card_bg", "#1a1a1a")
        border = THEME.get("border", "#333333")

        return f"""
            QWidget#{self._widget_name} {{
                background: {card_bg};
                border: 1px solid {border};
                border-radius: {radius}px;
            }}
        """


# ============================================================================
# Helper Functions for Common Theme Patterns
# ============================================================================


def refresh_theme_recursive(widget: QtWidgets.QWidget) -> None:
    """
    Recursively refresh theme on widget and all descendants.

    Useful for complex widget trees where you want to refresh everything.

    Args:
        widget: Root widget to start refresh from
    """
    if hasattr(widget, "refresh_theme"):
        widget.refresh_theme()
    else:
        # Fallback: traverse children manually
        for child in widget.findChildren(QtWidgets.QWidget):
            if hasattr(child, "refresh_theme"):
                child.refresh_theme()


def build_label_stylesheet(color: Optional[str] = None, font_size: Optional[int] = None) -> str:
    """
    Build a simple label stylesheet with theme colors.

    Args:
        color: Text color (defaults to THEME['ink'])
        font_size: Font size in pixels (optional)

    Returns:
        Stylesheet string for QLabel

    Example:
        label.setStyleSheet(build_label_stylesheet(color=THEME.get('text_dim'), font_size=12))
    """
    color = color or THEME.get("ink", "#ffffff")
    style = f"color: {color};"

    if font_size:
        style += f" font-size: {font_size}px;"

    return style


def build_card_stylesheet(
    bg: Optional[str] = None,
    border: Optional[str] = None,
    radius: Optional[int] = None,
) -> str:
    """
    Build a standard card stylesheet with theme values.

    Args:
        bg: Background color (defaults to THEME['card_bg'])
        border: Border color (defaults to THEME['border'])
        radius: Border radius in pixels (defaults to THEME['card_radius'])

    Returns:
        Stylesheet string for card-style widgets

    Example:
        widget.setStyleSheet(build_card_stylesheet())
    """
    bg = bg or THEME.get("card_bg", "#1a1a1a")
    border = border or THEME.get("border", "#333333")
    radius = radius if radius is not None else int(THEME.get("card_radius", 8))

    return f"""
        background: {bg};
        border: 1px solid {border};
        border-radius: {radius}px;
    """


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    """
    Example demonstrating ThemeAwareMixin usage.
    """
    import sys

    from PyQt6.QtWidgets import QApplication, QLabel

    class ExampleWidget(QtWidgets.QWidget, ThemeAwareMixin):
        def __init__(self):
            super().__init__()
            self.setObjectName("ExampleWidget")

            # Create children
            self.title = QLabel("Example Widget")
            self.content = QLabel("This widget uses ThemeAwareMixin")

            # Apply theme
            self._setup_theme()

        def _build_theme_stylesheet(self) -> str:
            return f"""
                QWidget#ExampleWidget {{
                    background: {THEME.get('card_bg')};
                    border: 1px solid {THEME.get('border')};
                    border-radius: {THEME.get('card_radius')}px;
                    padding: 16px;
                }}
            """

        def _get_theme_children(self) -> list:
            # If labels were themed widgets, they'd be refreshed too
            return []

        def _on_theme_refresh(self) -> None:
            # Custom refresh logic
            self.title.setStyleSheet(f"color: {THEME.get('ink')};")
            self.content.setStyleSheet(f"color: {THEME.get('text_dim')};")

    # Run example
    app = QApplication(sys.argv)
    widget = ExampleWidget()
    widget.show()

    print("[Example] Created themed widget")
    print("[Example] Call widget.refresh_theme() to refresh after theme change")

    sys.exit(app.exec())
