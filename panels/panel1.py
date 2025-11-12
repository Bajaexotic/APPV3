# -------------------- Panel1 Module (start) -----------------------------------
from __future__ import annotations

from collections.abc import Iterable, Sequence
import sys
from typing import Any, Optional, Tuple

from PyQt6 import QtCore, QtGui, QtWidgets

from utils.logger import get_logger


log = get_logger(__name__)

log.debug(f"Python executable: {sys.executable}")
log.debug(f"Python version: {sys.version}")
log.debug("Module loading")

# -------------------- Imports & Fallbacks ------------------------------------

try:
    import pyqtgraph as pg  # type: ignore

    log.debug(f"pyqtgraph imported successfully: {pg}")
except Exception as e:
    log.error(f"ERROR importing pyqtgraph: {e}")
    import traceback

    traceback.print_exc()
    pg = None  # safe fallback: app still runs, graph disabled

import contextlib

from config.theme import THEME, ColorTheme, switch_theme
from utils.theme_helpers import normalize_color
from utils.ui_helpers import centered_row
from widgets.connection_icon import ConnectionIcon  # type: ignore
from widgets.timeframe_pills import InvestingTimeframePills  # type: ignore


# -------------------- Adaptive Masked Frame (start) ---------------------------
class MaskedFrame(QtWidgets.QFrame):
    """
    A QFrame that paints a theme background and automatically masks itself
    to the painted geometry. Children (like PlotWidget) are clipped to this shape.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bg_color = THEME.get("bg_secondary")

    def set_background_color(self, color: str) -> None:
        """Update the background color dynamically."""
        self._bg_color = color
        self.update()  # Trigger repaint

    def _shape_path(self) -> QtGui.QPainterPath:
        """Define the shape. Change this to any geometry later (waves, polygons...)."""
        rect = QtCore.QRectF(self.rect())  # [OK] convert QRect -> QRectF
        r = float(THEME.get("card_radius"))
        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, r, r)
        return path

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # 1) Paint the background (no border)
        path = self._shape_path()
        painter.setBrush(QtGui.QBrush(QtGui.QColor(self._bg_color)))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)  # Remove border
        painter.drawPath(path)

        # 2) Clip this widget (and its children) to that exact shape
        region = QtGui.QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

        # ✅ Explicitly end painter to avoid QBackingStore warnings
        painter.end()

        # Continue normal painting
        super().paintEvent(event)


# -------------------- Adaptive Masked Frame (end) -----------------------------


# -------------------- Small helpers (start) -----------------------------------
def _pnl_color(up: Optional[bool]) -> str:
    """Return a direction color from theme (green/red/neutral)."""
    if up is None:
        return str(THEME.get("pnl_neu_color"))
    return ColorTheme.pnl_color_from_direction(bool(up))


def _fmt_money(v: Optional[float]) -> str:
    if v is None:
        return "—"
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "—"


def _fmt_pct(p: Optional[float]) -> str:
    if p is None:
        return "—"
    try:
        return f"{float(p):+.2f}%"
    except Exception:
        return "—"


# -------------------- Small helpers (end) -------------------------------------


# -------------------- Panel1 (start) ------------------------------------------
class Panel1(QtWidgets.QWidget):
    """
    Panel 1 — header, graph, timeframe controls, and live readouts.
    """

    timeframeChanged = QtCore.pyqtSignal(str)

    def has_graph(self) -> bool:
        return (pg is not None) and (getattr(self, "_plot", None) is not None)

    def __init__(self) -> None:
        log.debug("Init starting")
        super().__init__()

        # Timeframe and mode state
        self._tf: str = "LIVE"
        self._mode_is_live: bool = False
        self._connected: bool = False

        # PnL state
        self._pnl_up: Optional[bool] = None
        self._pnl_val: Optional[float] = None
        self._pnl_pct: Optional[float] = None

        # CRITICAL: Strict (mode, account) scoping for equity curves
        # Key: (mode, account) tuple, Value: list of (timestamp, balance) points
        self._equity_curves: dict[tuple[str, str], list[tuple[float, float]]] = {}

        # Current active scope
        self.current_mode: str = "SIM"
        self.current_account: str = ""
        self._active_scope: tuple[str, str] = ("SIM", "")

        # Legacy compatibility - points to active curve
        self._equity_points: list[tuple[float, float]] = []

        # Session start baselines - scoped by (mode, account)
        self._session_start_balances: dict[tuple[str, str], float] = {}
        self._session_start_time: Optional[float] = None

        # Graph items
        self._plot: Optional[Any] = None
        self._vb: Optional[Any] = None  # viewbox reference
        self._line: Optional[Any] = None
        self._endpoint: Optional[Any] = None
        self._pulse_timer: Optional[QtCore.QTimer] = None
        self._pulse_phase: float = 0.0
        self._trail_lines: list[Any] = []
        self._glow_line: Optional[Any] = None
        self._perf_safe: bool = bool(THEME.get("perf_safe"))
        self._current_color: QtGui.QColor = QtGui.QColor(THEME.get("ink"))
        self._target_color: QtGui.QColor = QtGui.QColor(self._current_color)

        # Hover/scrubbing state
        self._hovering: bool = False
        self._scrub_x: Optional[float] = None
        self._hover_seg: Optional[QtWidgets.QGraphicsLineItem] = None
        self._hover_text: Optional[Any] = None  # pg.TextItem

        # Timeframe configs
        self._tf_configs: dict[str, dict[str, Optional[int]]] = {
            "LIVE": {"window_sec": 3600, "snap_sec": 60},
            "1D": {"window_sec": 86400, "snap_sec": 300},
            "1W": {"window_sec": 604800, "snap_sec": 3600},
            "1M": {"window_sec": 2592000, "snap_sec": 14400},
            "3M": {"window_sec": 7776000, "snap_sec": 43200},
            "YTD": {"window_sec": None, "snap_sec": 86400},
        }

        # External references (wired by the app)
        self._peer_panel: Optional[QtWidgets.QWidget] = None  # Panel3 reference
        self._panel2: Optional[QtWidgets.QWidget] = None  # Panel2 reference for theme refresh
        self._panel3: Optional[QtWidgets.QWidget] = None  # Panel3 reference for theme refresh

        # Build & init
        self._build_ui()
        self._init_graph()

        # CRITICAL FIX: Attach plot to container BEFORE initializing hover and pulse
        # This ensures the plot is in the layout and has proper geometry
        if hasattr(self, "_plot") and self._plot is not None:
            self._attach_plot_to_container(self._plot)

        self._init_pulse()
        self._init_hover_elements()
        self._ensure_live_pill_dot(initial=True)

        # Initialize theme based on default mode
        switch_theme("live" if self._mode_is_live else "sim")
        self._refresh_theme_colors()

        # Wire balance signal from StateManager
        self._wire_balance_signal()

        # Initialize PnL display to $0.00 (0.00%) in neutral color instead of dashes
        # This happens after wiring so signals are ready
        self.set_pnl_for_timeframe(pnl_value=0.0, pnl_pct=0.0, up=None)

        # Initialize session start time (used for PnL baseline calculation)
        import time
        self._session_start_time = time.time()

        # Schedule size check after UI is fully rendered
        QtCore.QTimer.singleShot(500, self._debug_sizes)

    # -------------------- UI BUILD (start) -----------------------------------
    def _build_ui(self) -> None:
        self.setObjectName("Panel1")
        self.setStyleSheet(f"QWidget#Panel1 {{ background:{THEME.get('bg_panel')}; }}")

        # Root layout
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # --- Unified header (connection + mode + account) ---
        header = self._build_header()
        root.addWidget(header)

        # --- Balance + PnL column (aligned left with INVESTING) ---
        vals_container = QtWidgets.QHBoxLayout()
        vals_container.setContentsMargins(0, 0, 0, 0)
        vals_container.setSpacing(0)

        # Vertical layout for balance and PnL
        vals_col = QtWidgets.QVBoxLayout()
        vals_col.setContentsMargins(0, 0, 0, 0)
        vals_col.setSpacing(12)  # 12px between balance and PnL

        self.lbl_balance = QtWidgets.QLabel("—")
        self.lbl_balance.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.lbl_balance.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        # Balance label uses brightest white from skeleton framework
        self.lbl_balance.setStyleSheet(
            f"color:{THEME.get('ink')}; "
            f"{ColorTheme.font_css(int(THEME.get('balance_font_weight')), int(THEME.get('balance_font_size')))};"
        )

        self.lbl_pnl = QtWidgets.QLabel("—  —")
        self.lbl_pnl.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.lbl_pnl.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        # PnL label uses color coordination from start (neutral until data arrives)
        self.lbl_pnl.setStyleSheet(
            f"color:{THEME.get('fg_muted')}; "
            f"{ColorTheme.font_css(int(THEME.get('pnl_font_weight')), int(THEME.get('pnl_font_size')))};"
        )

        vals_col.addWidget(self.lbl_balance)
        vals_col.addWidget(self.lbl_pnl)
        vals_col.addStretch(1)

        vals_container.addLayout(vals_col)
        vals_container.addStretch(1)
        root.addLayout(vals_container)

        # --- Graph container (MaskedFrame handles its own paint) ---
        self.graph_container = MaskedFrame()
        # FIX: Set minimum height to prevent container from collapsing to 0
        self.graph_container.setMinimumHeight(200)
        self.graph_container.setMinimumWidth(200)
        self.graph_container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding
        )

        graph_layout = QtWidgets.QVBoxLayout(self.graph_container)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_layout.setSpacing(0)

        # Make the graph container consume all available vertical space
        root.addWidget(self.graph_container, 1)

    # -------------------- UI BUILD (end) -------------------------------------

    # -------------------- Unified Header Builder (start)
    def _build_header(self) -> QtWidgets.QWidget:
        """
        Creates the header row with INVESTING label and badge:
        - INVESTING label (plain text, no pill background)
        - Badge positioned at top right of INVESTING
        """
        header = QtWidgets.QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        # "INVESTING" label (NO pill background)
        self.lbl_title = QtWidgets.QLabel("INVESTING")
        self.lbl_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.lbl_title.setStyleSheet(
            f"color: {THEME.get('investing_text_color')}; "
            f"{ColorTheme.font_css(int(THEME.get('investing_font_weight')), int(THEME.get('investing_font_size')))}; "
            "letter-spacing: 0.6px; "
            "background: transparent; "
            "border: none; "
            "padding: 0px;"
        )
        header.addWidget(self.lbl_title, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)

        # Small gap between INVESTING and badge
        header.addSpacing(int(THEME.get("badge_gap")))

        # Badge (neon pill) - positioned at top right of INVESTING
        self.mode_badge = QtWidgets.QLabel("DEBUG")  # Default to DEBUG
        self.mode_badge.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.mode_badge.setFixedHeight(int(THEME.get("badge_height")))
        self.mode_badge.setFixedWidth(int(THEME.get("badge_width")))
        # Align badge to top instead of center to position it at top right of INVESTING
        header.addWidget(self.mode_badge, 0, QtCore.Qt.AlignmentFlag.AlignTop)

        # Style badge (will be updated by set_trading_mode)
        self._update_badge_style("DEBUG")

        # Add stretch to push connection icon to the right
        header.addStretch(1)

        # Connection icon
        self.conn_icon = ConnectionIcon()
        self.conn_icon.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        header.addWidget(self.conn_icon, 0, QtCore.Qt.AlignmentFlag.AlignRight)

        container = QtWidgets.QWidget()
        container.setLayout(header)
        return container

    # -------------------- Unified Header Builder (end)

    def _update_badge_style(self, mode: str) -> None:
        """
        Apply badge pill styling based on trading mode.
        - Styles mode_badge QLabel (neon pill with background, border, radius, text color)
        - Conditionally applies glow effect (only SIM/LIVE, not DEBUG)

        Args:
            mode: One of "DEBUG", "SIM", or "LIVE"
        """
        mode = mode.upper()

        # Get structural constants from THEME
        badge_radius = int(THEME.get("badge_radius"))
        badge_font_size = int(THEME.get("badge_font_size"))
        badge_font_weight = int(THEME.get("badge_font_weight"))
        glow_blur = int(THEME.get("glow_blur_radius"))

        # Get mode-specific colors from THEME
        badge_bg = str(THEME.get("badge_bg_color"))
        badge_border = str(THEME.get("badge_border_color"))
        badge_text = str(THEME.get("badge_text_color"))
        glow_color = str(THEME.get("glow_color"))

        # Style badge with neon pill (background, border, radius)
        self.mode_badge.setStyleSheet(
            f"color: {badge_text}; "
            f"background-color: {badge_bg}; "
            f"border: 2px solid {badge_border}; "
            f"border-radius: {badge_radius}px; "
            f"padding: 0px; "
            f"{ColorTheme.font_css(badge_font_weight, badge_font_size)};"
        )

        # Apply glow effect conditionally (only if glow_color is not "none")
        if glow_color != "none" and glow_color.startswith("#"):
            # Apply glow to badge for SIM/LIVE modes
            glow_effect = QtWidgets.QGraphicsDropShadowEffect()
            glow_effect.setBlurRadius(glow_blur)
            glow_effect.setColor(QtGui.QColor(glow_color))
            glow_effect.setOffset(0, 0)
            self.mode_badge.setGraphicsEffect(glow_effect)
        else:
            # Remove glow effect for DEBUG mode
            self.mode_badge.setGraphicsEffect(None)

    def _attach_plot_to_container(self, plot: pg.PlotWidget) -> None:
        """
        Ensures PlotWidget fills graph_container via layout stretch instead of default 640×480.
        Place this block between UI BUILD (end) and Graph & Pulse (start).
        """
        lay = self.graph_container.layout()
        if lay is None:
            lay = QtWidgets.QVBoxLayout(self.graph_container)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(0)

        # Make the plot fully layout-driven (no fixed-size caps)
        plot.setParent(None)
        plot.setMinimumSize(QtCore.QSize(0, 0))
        plot.setMaximumSize(QtCore.QSize(16777215, 16777215))
        plot.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

        # Add with stretch so it fills available space
        lay.addWidget(plot, 1)  # stretch = 1
        with contextlib.suppress(Exception):
            lay.setStretchFactor(plot, 1)

        # Immediate geometry sync to avoid a frame at 640×480
        plot.setGeometry(self.graph_container.contentsRect())

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        """Keep the plot synced with the container’s inner rect."""
        try:
            if getattr(self, "_plot", None) and self.graph_container:
                self._plot.setGeometry(self.graph_container.contentsRect())
        except Exception:
            pass
        super().resizeEvent(e)

    # -------------------- Graph layout glue (end) --------------------------------
    # ---Graph and pulse (start)
    def _init_graph(self) -> None:
        log.debug(f"_init_graph called, pg={pg}")
        if pg is None:
            log.error("ERROR: pyqtgraph (pg) is None!")
            self._plot = None
            self._vb = None
            self._line = None
            self._trail_lines = []
            self._glow_line = None
            self._endpoint = None
            return

        try:
            # state
            self._perf_safe = bool(THEME.get("perf_safe"))
            self._pulse_phase = 0.0
            self._hovering = bool(getattr(self, "_hovering", False))
            self._current_color = QtGui.QColor(THEME.get("ink"))
            self._target_color = QtGui.QColor(self._current_color)

            # plot widget
            pg.setConfigOptions(antialias=True)
            self._plot = pg.PlotWidget()
            # FIX: Set visible background instead of transparent to avoid black-on-black visibility issue
            self._plot.setBackground('#0F0F1A')  # Very dark blue-gray for contrast against black panel
            self._plot.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
            self._plot.setStyleSheet("background: transparent; border: none;")
            self._plot.useOpenGL(False)
            self._plot.setMenuEnabled(False)
            # FIX: Disable mouse panning/zooming - graph should be fixed
            self._plot.setMouseEnabled(x=False, y=False)
            self._plot.hideButtons()
            self._plot.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
            self._plot.setParent(self.graph_container)
            self._plot.setCursor(QtCore.Qt.CursorShape.CrossCursor)  # Crosshair cursor for hover

            # plot item / viewbox
            plot_item = self._plot.getPlotItem()
            plot_item.hideAxis("left")
            plot_item.hideAxis("bottom")
            # FIX: Show grid lines for debugging visibility
            plot_item.showGrid(x=True, y=True, alpha=0.15)
            plot_item.setContentsMargins(0, 0, 0, 0)
            plot_item.layout.setContentsMargins(0, 0, 0, 0)

            vb = plot_item.getViewBox()
            vb.setDefaultPadding(0.02)
            # FIX: Disable mouse interaction on viewbox - prevents panning
            vb.setMouseEnabled(x=False, y=False)
            vb.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=False)  # Disable auto-range
            vb.setLimits(xMin=None, xMax=None, yMin=None, yMax=None)
            # FIX: Ensure graph moves left to right (time on X axis, balance on Y axis)
            vb.invertY(False)  # Make sure Y axis goes bottom (low) to top (high)
            vb.invertX(False)  # Make sure X axis goes left (old) to right (new)
            self._vb = vb

            # main line (initialize once; color updates dynamically later)
            base_color = QtGui.QColor(ColorTheme.pnl_color_from_direction(getattr(self, "_pnl_up", None)))
            # FIX: Increase line width from 3 to 6 for better visibility
            main_pen = pg.mkPen(base_color, width=6, join="round", cap="round")
            self._line = self._plot.plot([], [], pen=main_pen, antialias=True)
            self._line.setZValue(10)

            # trails
            self._trail_lines = []
            trail_specs = (
                [
                    {"width": 8, "alpha": 0.25, "take": 1.00},
                    {"width": 6, "alpha": 0.35, "take": 0.66},
                    {"width": 4, "alpha": 0.50, "take": 0.40},
                ]
                if not self._perf_safe
                else [{"width": 6, "alpha": 0.35, "take": 0.60}]
            )
            for spec in trail_specs:
                c = QtGui.QColor(base_color)
                c.setAlphaF(spec["alpha"])
                pen = pg.mkPen(c, width=spec["width"], join="round", cap="round")
                item = self._plot.plot([], [], pen=pen, antialias=True)
                item._trail_take = spec["take"]
                item.setZValue(5)
                self._trail_lines.append(item)

            # glow halo
            self._glow_line = None
            if not self._perf_safe:
                glow_c = QtGui.QColor(base_color)
                glow_c.setAlphaF(0.12)
                glow_pen = pg.mkPen(glow_c, width=16, join="round", cap="round")
                self._glow_line = self._plot.plot([], [], pen=glow_pen, antialias=True)
                self._glow_line.setZValue(1)

            # endpoint
            self._endpoint = pg.ScatterPlotItem(size=8, brush=pg.mkBrush(base_color), pen=None, symbol="o")
            self._endpoint.setZValue(50)
            self._plot.addItem(self._endpoint)

            # sonar rings
            self._ripple_items = []
            for i in range(3):
                ripple = pg.ScatterPlotItem(size=8, pen=pg.mkPen(base_color, width=1.0), brush=None, symbol="o")
                ripple.setZValue(30)
                self._plot.addItem(ripple)
                self._ripple_items.append(ripple)

            # hover hook
            try:
                self._plot.scene().sigMouseMoved.connect(self._on_mouse_move)
                self._plot.viewport().installEventFilter(self)
            except Exception:
                pass

            # layout glue
            lay = self.graph_container.layout()
            if lay:
                lay.setContentsMargins(0, 0, 0, 0)
                lay.setSpacing(0)
                # Remove any existing widgets
                while lay.count():
                    lay.takeAt(0)
                # Add plot with stretch factor for centering/filling
                lay.addWidget(self._plot, 1)  # stretch = 1
                self._plot.setMinimumSize(0, 0)
                self._plot.setMaximumSize(QtCore.QSize(16777215, 16777215))
                self._plot.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
                with contextlib.suppress(Exception):
                    lay.setStretchFactor(self._plot, 1)

            self._plot.show()
            self._plot.updateGeometry()
            self.graph_container.updateGeometry()

            # FIX: Force container visibility and ensure plot has minimum size
            if not self.graph_container.isVisible():
                self.graph_container.show()
            if self._plot.size().width() < 100:
                self._plot.setMinimumSize(400, 300)
            self._plot.update()
            self.graph_container.update()

            # Ensure viewbox has initial range even with no data
            import time

            now = time.time()
            try:
                # Set a reasonable default range (last hour, $0-$100k)
                self._vb.setRange(xRange=[now - 3600, now], yRange=[0, 100000], padding=0.02)
            except Exception:
                with contextlib.suppress(Exception):
                    self._vb.autoRange(padding=0.05)

            self.graph_container.installEventFilter(self)
            log.info("Graph initialized successfully")

        except Exception as e:
            log.error(f"Graph init failed: {e}")
            import traceback

            traceback.print_exc()
            self._plot = None
            self._vb = None
            self._line = None
            self._trail_lines = []
            self._glow_line = None
            self._endpoint = None

    def _init_pulse(self) -> None:
        if getattr(self, "_pulse_timer", None):
            return
        self._pulse_timer = QtCore.QTimer(self)
        self._pulse_timer.setInterval(40)  # ~25 FPS
        self._pulse_timer.timeout.connect(self._on_pulse_tick)
        self._pulse_timer.start()
        self._pulse_phase = 0.0

    def _on_pulse_tick(self) -> None:
        """Stationary endpoint with slow pulse, PnL-driven color, and gradient sonar rings."""
        if getattr(self, "_plot", None) is None or getattr(self, "_vb", None) is None:
            return
        if not self._equity_points:
            return
        # Limit endpoint pulse to LIVE and 1D timeframes
        if self._tf not in ("LIVE", "1D"):
            try:
                if getattr(self, "_endpoint", None):
                    self._endpoint.setData([], [])
                for ripple in getattr(self, "_ripple_items", []) or []:
                    ripple.setData([], [])
            except Exception:
                pass
            return

        import math

        self._pulse_phase = (self._pulse_phase + 0.035) % (2 * math.pi)
        x, y = self._equity_points[-1]

        # color directly from current PnL each tick
        pnl_color = ColorTheme.pnl_color_from_direction(getattr(self, "_pnl_up", None))
        base_color = QtGui.QColor(pnl_color)

        # update line pen dynamically (keeps graph color tied to timeframe PnL)
        self._line.setPen(pg.mkPen(base_color, width=3, join="round", cap="round"))

        # endpoint breathing
        pulse = 0.5 + 0.5 * math.sin(self._pulse_phase)
        base_size = 8
        size = base_size + 1.5 * pulse
        dot_color = QtGui.QColor(base_color)
        dot_color.setAlphaF(0.85 - 0.25 * pulse)
        self._endpoint.setSize(size)
        self._endpoint.setBrush(pg.mkBrush(dot_color))
        self._endpoint.setData([x], [y])

        # sonar rings (brighter inner edge; half-distance travel feel)
        for i, ripple in enumerate(self._ripple_items):
            phase = (self._pulse_phase + (i * 2 * math.pi / len(self._ripple_items))) % (2 * math.pi)
            frac = (1 + math.sin(phase)) / 2.0
            radius = 8 + frac * 18.0  # ~half the previous travel distance
            luminance_boost = 1.0 - frac * 0.6
            alpha = max(0.0, 0.42 * (1.0 - frac)) * luminance_boost  # a bit brighter
            ring_color = QtGui.QColor(base_color)
            ring_color.setAlphaF(alpha)
            pen = pg.mkPen(ring_color, width=1.0)
            ripple.setPen(pen)
            ripple.setSize(radius)
            ripple.setData([x], [y])

        # soft glow synced to pulse
        if self._glow_line is not None and not self._perf_safe:
            g = QtGui.QColor(base_color)
            alpha = 0.06 + 0.03 * (0.5 + 0.5 * math.sin(self._pulse_phase))
            g.setAlphaF(min(0.25, max(0.0, alpha)))
            self._glow_line.setPen(pg.mkPen(g, width=16, join="round", cap="round"))

    # -------------------- Graph & Pulse (end) --------------------------------

    # -------------------- Timeframe helpers (start) --------------------------
    def _ensure_live_pill_dot(self, initial: bool = False) -> None:
        """Ensure the LIVE dot exists and set a sane initial pulsing state."""
        try:
            if hasattr(self, "pills") and self.pills:
                if hasattr(self.pills, "set_live_dot_visible"):
                    self.pills.set_live_dot_visible(True)
                if hasattr(self.pills, "set_live_dot_pulsing"):
                    self.pills.set_live_dot_pulsing(False if initial else (self._tf == "LIVE"))
        except Exception:
            pass

    def set_timeframe(self, tf: str) -> None:
        """
        Public setter wired from pills.timeframeChanged.
        Enforces the active timeframe by replotting a windowed slice (if available).
        """
        if tf not in ("LIVE", "1D", "1W", "1M", "3M", "YTD"):
            log.warning(f"Ignoring invalid timeframe: {tf}")
            return

        self._tf = tf
        log.info(f"Timeframe changed to {tf}")

        # Route to controller if present (non-fatal if missing)
        if hasattr(self, "_on_investing_tf_changed"):
            try:
                self._on_investing_tf_changed(tf)
            except Exception as e:
                log.error(f"_on_investing_tf_changed error: {e}")

        # Replot from cache so the graph reflects the TF window
        try:
            self._replot_from_cache()
        except Exception as e:
            log.error(f"set_timeframe replot error: {e}")

        # Update LIVE pill pulse state
        self._ensure_live_pill_dot(initial=False)

        # Update PnL display for the new timeframe
        self._update_pnl_for_current_tf()

    def _update_pnl_for_current_tf(self) -> None:
        """Calculate and display PnL for the current timeframe based on ACTUAL TRADES within the timeframe."""

        try:
            from datetime import datetime, timedelta, timezone
            from data.db_engine import get_session
            from data.schema import TradeRecord
            from sqlalchemy import func

            UTC = timezone.utc
            now = datetime.now(UTC)
            mode = self._current_display_mode

            # Define timeframe ranges
            timeframe_ranges = {
                "LIVE": (now - timedelta(hours=1), now),  # Last 1 hour
                "1D": (datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=UTC), now),  # Since midnight
                "1W": (now - timedelta(weeks=1), now),  # Last 7 days
                "1M": (now - timedelta(days=30), now),  # Last 30 days
                "3M": (now - timedelta(days=90), now),  # Last 90 days
                "YTD": (datetime(now.year, 1, 1, tzinfo=UTC), now),  # Jan 1 to now
            }

            if self._tf not in timeframe_ranges:
                start_time, end_time = timeframe_ranges["LIVE"]
            else:
                start_time, end_time = timeframe_ranges[self._tf]


            # Query trades for this timeframe
            with get_session() as session:
                trades = session.query(TradeRecord).filter(
                    TradeRecord.mode == mode,
                    TradeRecord.exit_time >= start_time,
                    TradeRecord.exit_time <= end_time,
                    TradeRecord.realized_pnl is not None,  # Only trades with valid PnL
                    TradeRecord.is_closed == True
                ).all()

            if trades:
                # Calculate total PnL for timeframe (filter out None values)
                total_pnl = sum(t.realized_pnl for t in trades if t.realized_pnl is not None)
                baseline = 10000.0  # Standard SIM starting balance
                pnl_pct = (total_pnl / baseline) * 100.0


                pnl_up = total_pnl > 0 if abs(total_pnl) > 0.01 else None
            else:
                total_pnl = 0.0
                pnl_pct = 0.0
                pnl_up = None

            # Update display
            self.set_pnl_for_timeframe(pnl_value=total_pnl, pnl_pct=pnl_pct, up=pnl_up)
            log.debug(f"[panel1] PnL for {self._tf}: ${total_pnl:+.2f} ({pnl_pct:+.2f}%)")

        except Exception as e:
            import traceback
            traceback.print_exc()
            log.error(f"[panel1] Could not calculate PnL for timeframe {self._tf}: {e}")
            # Show zero on error
            self.set_pnl_for_timeframe(pnl_value=0.0, pnl_pct=0.0, up=None)

    # -------------------- Timeframe helpers (end) ----------------------------

    # -------------------- Public API (start) ---------------------------------
    def set_stats_panel(self, peer_panel: QtWidgets.QWidget) -> None:
        """Wire a cooperating stats panel (Panel3) for cross-panel use."""
        self._peer_panel = peer_panel
        self._panel3 = peer_panel  # Also store for theme refresh

    def set_panel_references(self, panel2=None, panel3=None) -> None:
        """Set references to Panel2 and Panel3 for theme synchronization."""
        if panel2:
            self._panel2 = panel2
        if panel3:
            self._panel3 = panel3

    def set_mode_live(self, live: bool) -> None:
        """
        Legacy method for backward compatibility.
        Redirects to set_trading_mode() with appropriate mode.

        Args:
            live: True for LIVE mode, False for SIM mode
        """
        self._mode_is_live = bool(live)
        self.mode_badge.setText("LIVE" if live else "SIM")

        # Update neon color based on mode
        neon_color = "#FF0000" if live else "#00FFFF"  # Red for LIVE, Cyan for SIM
        bg_rgba = "255, 0, 0" if live else "0, 255, 255"
        self.mode_badge.setStyleSheet(
            f"color: #000000; "
            f"background: rgba({bg_rgba}, 0.2); "
            f"border: 2px solid {neon_color}; "
            f"border-radius: 6px; "  # Rectangular pill shape
            "padding: 0 10px; "
            f"{ColorTheme.font_css(700, 12)};"
        )

        # Update glow effect color
        neon_glow = QtWidgets.QGraphicsDropShadowEffect()
        neon_glow.setBlurRadius(12)
        neon_glow.setColor(QtGui.QColor(neon_color))
        neon_glow.setOffset(0, 0)
        self.mode_badge.setGraphicsEffect(neon_glow)

    def _load_equity_curve_from_database(self, mode: str, account: str) -> list[tuple[float, float]]:
        """
        Rebuild equity curve from trade history in the database.

        Queries all closed trades for the given (mode, account) scope,
        sorts them by exit time, and builds a cumulative balance curve.

        Args:
            mode: Trading mode ("SIM", "LIVE", "DEBUG")
            account: Account identifier

        Returns:
            List of (timestamp, balance) points for the equity curve
        """

        try:
            from datetime import timezone
            from data.db_engine import get_session
            from data.schema import TradeRecord

            # Get starting balance (default 10k for SIM, 0 for LIVE)
            starting_balance = 10000.0 if mode == "SIM" else 0.0

            # Query all trades for this mode, ordered by exit time
            with get_session() as s:
                query = (
                    s.query(TradeRecord)
                    .filter(TradeRecord.mode == mode)
                    .filter(TradeRecord.is_closed == True)
                    .filter(TradeRecord.realized_pnl.isnot(None))
                    .filter(TradeRecord.exit_time.isnot(None))
                    .order_by(TradeRecord.exit_time.asc())
                )

                trades = query.all()

                if not trades:
                    # No trades yet, return empty curve
                    return []

                # Build equity curve: cumulative sum of P&L
                equity_points = []
                cumulative_balance = starting_balance

                for trade in trades:
                    if trade.realized_pnl is not None and trade.exit_time is not None:
                        cumulative_balance += trade.realized_pnl
                        timestamp = trade.exit_time.replace(tzinfo=timezone.utc).timestamp()
                        equity_points.append((timestamp, cumulative_balance))
                        print(f"  Trade: {trade.symbol} | PnL={trade.realized_pnl:+.2f} | Balance=${cumulative_balance:,.2f} | Time={trade.exit_time}")

                print(f"  Starting balance: ${starting_balance:,.2f}")
                if equity_points:
                    print(f"  Ending balance: ${equity_points[-1][1]:,.2f}")

                return equity_points

        except Exception as e:
            log.error(f"[Panel1] Error loading equity curve from database: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
            return []

    def _get_equity_curve(self, mode: str, account: str) -> list[tuple[float, float]]:
        """
        Get equity curve for (mode, account) scope, loading from database if not cached.

        Args:
            mode: Trading mode ("SIM", "LIVE", "DEBUG")
            account: Account identifier

        Returns:
            List of (timestamp, balance) points
        """
        scope = (mode, account)
        if scope not in self._equity_curves:
            # Load from database on first access
            self._equity_curves[scope] = self._load_equity_curve_from_database(mode, account)
        return self._equity_curves[scope]

    def set_trading_mode(self, mode: str, account: Optional[str] = None) -> None:
        """
        Update the badge display for DEBUG/SIM/LIVE modes.
        Uses the unified nested pill styling system with THEME-based colors.

        CRITICAL: This implements the ModeChanged contract:
        1. Freeze current state (automatic via scope switch)
        2. Swap to new (mode, account) scope
        3. Reload equity curve from persistent storage
        4. Single repaint

        Args:
            mode: One of "DEBUG", "SIM", or "LIVE"
            account: Account identifier (optional, defaults to empty string)
        """
        mode = mode.upper()
        if mode not in ("DEBUG", "SIM", "LIVE"):
            log.warning(f"Invalid trading mode: {mode}")
            return

        # Use empty string if account not provided
        if account is None:
            account = ""

        # Check if mode/account actually changed
        new_scope = (mode, account)
        if new_scope == self._active_scope:
            log.debug(f"[Panel1] Mode/account unchanged: {mode}, {account}")
            return

        old_scope = self._active_scope
        log.info(f"[Panel1] Mode change: {old_scope} → {new_scope}")

        # 1. Freeze: Current state automatically preserved in scoped dict

        # 2. Swap: Update active scope
        self.current_mode = mode
        self.current_account = account
        self._active_scope = new_scope

        # 3. Reload: Get equity curve for new scope
        self._equity_points = self._get_equity_curve(mode, account)

        # Switch theme first to ensure THEME has correct colors for this mode
        switch_theme(mode.lower())

        # Update badge text
        self.mode_badge.setText(f"{mode}")

        # Apply badge pill styling from THEME (now with correct colors)
        self._update_badge_style(mode)

        # Update balance label for new scope
        try:
            from core.app_state import get_state_manager
            state = get_state_manager()
            if state:
                if mode == "SIM":
                    # Get balance for this specific SIM account
                    from core.sim_balance import get_sim_balance
                    balance = get_sim_balance(account) if account else 10000.0
                else:
                    balance = state.live_balance
                self.set_account_balance(balance)
                # CRITICAL: Also add point to equity curve for new scope
                self.update_equity_series_from_balance(balance, mode=mode)
                log.debug(f"[Panel1] Updated balance for {mode}/{account}: ${balance:,.2f}")
        except Exception as e:
            log.debug(f"[Panel1] Could not update balance on mode switch: {e}")

        # 4. Single repaint: Redraw graph with new scope's data
        self._replot_from_cache()
        self._update_pnl_for_current_tf()

        log.info(f"[Panel1] Switched to {mode}/{account} ({len(self._equity_points)} points)")

    def switch_equity_curve_for_mode(self, mode: str) -> None:
        """
        DEPRECATED: Use set_trading_mode(mode, account) instead.

        Legacy method for backward compatibility. Calls set_trading_mode.
        """
        log.warning("[Panel1] switch_equity_curve_for_mode is deprecated, use set_trading_mode()")
        self.set_trading_mode(mode, self.current_account)

    def _refresh_theme_colors(self) -> None:
        """Refresh all UI elements with current THEME colors."""
        # Update panel background
        bg_color = THEME.get("bg_panel")
        self.setStyleSheet(f"QWidget#Panel1 {{ background: {bg_color}; }}")

        # Update graph container background
        if hasattr(self, "graph_container") and self.graph_container:
            self.graph_container.set_background_color(THEME.get("bg_secondary"))

        # Note: mode_badge is NOT updated here - it's managed by set_trading_mode() or set_mode_live()

        # Update balance label
        if hasattr(self, "lbl_balance") and self.lbl_balance:
            self.lbl_balance.setStyleSheet(
                f"color: {THEME.get('ink')}; "
                f"{ColorTheme.font_css(int(THEME.get('balance_font_weight')), int(THEME.get('balance_font_size')))};"
            )

        # Update PnL label
        if hasattr(self, "lbl_pnl") and self.lbl_pnl:
            pnl_color = _pnl_color(self._pnl_up)
            self.lbl_pnl.setStyleSheet(
                f"color: {pnl_color}; "
                f"{ColorTheme.font_css(int(THEME.get('pnl_font_weight')), int(THEME.get('pnl_font_size')))};"
            )

        # Refresh Panel2 and Panel3 if they're wired
        if self._panel2 and hasattr(self._panel2, "refresh_theme"):
            self._panel2.refresh_theme()
        if self._panel3 and hasattr(self._panel3, "refresh_theme"):
            self._panel3.refresh_theme()

    def set_connection_status(self, connected: bool) -> None:
        self._connected = bool(connected)
        with contextlib.suppress(Exception):
            pass

    def set_account_balance(self, balance: Optional[float]) -> None:
        self.lbl_balance.setText(_fmt_money(balance))

    def update_equity_series_from_balance(self, balance: Optional[float], mode: Optional[str] = None) -> None:
        """Add a balance point to the equity curve for graphing.

        This gets called when balance updates arrive from DTC,
        allowing us to build an equity curve over time.

        CRITICAL: Uses strict (mode, account) scoping. Balance updates
        are stored in the scoped curve for the current active scope.

        Args:
            balance: The balance value to add
            mode: Trading mode (optional, defaults to current_mode)
        """
        if balance is None:
            return

        try:
            import time

            now = time.time()
            balance_float = float(balance)

            # Use current active scope if mode not specified
            if mode is None:
                mode = self.current_mode

            # Get the scoped curve for (mode, account)
            account = self.current_account
            scope = (mode, account)
            curve = self._get_equity_curve(mode, account)

            # Append new point
            curve.append((now, balance_float))

            # Limit to last 2 hours to avoid memory bloat
            cutoff_time = now - 7200
            curve[:] = [(x, y) for x, y in curve if x >= cutoff_time]

            # Update scoped dict
            self._equity_curves[scope] = curve

            # Update active points if this is the current scope
            if scope == self._active_scope:
                self._equity_points = list(curve)

                # Redraw graph with new point (single repaint)
                self._replot_from_cache()
                self._update_pnl_for_current_tf()

            log.debug(f"[Panel1] Equity updated for {mode}/{account}: {len(curve)} points")

        except Exception as e:
            log.debug(f"[Panel1] update_equity_series_from_balance error: {e}")

    def set_pnl_for_timeframe(
        self,
        pnl_value: Optional[float],
        pnl_pct: Optional[float],
        up: Optional[bool],
    ) -> None:
        self._pnl_val = pnl_value
        self._pnl_pct = pnl_pct
        self._pnl_up = up

        self._apply_pnl_to_header()

        self._apply_pnl_to_pills(up)

        self._recolor_endpoint()


    # --- filter helper for the active timeframe -----------------------------
    def _filtered_points_for_current_tf(self) -> list[tuple[float, float]]:
        """
        Return a slice of the active mode's equity points that fits the active timeframe window.
        If window_sec is None (YTD), return all points.

        Uses the currently active (mode, account) scoped curve.
        """
        # Get the active curve for current scope
        pts = list(self._equity_points or [])

        log.debug(f"[Panel1] Filtering points for {self.current_mode}/{self.current_account}: {len(pts)} total")

        if not pts:
            return []

        cfg = self._tf_configs.get(self._tf, {})
        window_sec = cfg.get("window_sec")

        if not window_sec:
            return pts  # None or 0 -> no trim

        last_x = float(pts[-1][0])
        x_min = last_x - float(window_sec)

        i0 = 0
        for i, (x, _) in enumerate(pts):
            if x >= x_min:
                i0 = i
                break

        filtered = pts[i0:]
        if filtered:

        return filtered

    # --- replot current cache with TF filtering -----------------------------
    def _replot_from_cache(self) -> None:
        """
        Use the cached full series (self._equity_points) and display only the
        windowed slice for the active timeframe. Updates line, endpoint, trails/glow,
        and auto-range.
        """
        if not getattr(self, "_line", None) or not getattr(self, "_plot", None):
            return

        pts = self._filtered_points_for_current_tf()
        if pts:
            xs, ys = zip(*pts)
            try:
                self._line.setData(xs, ys)
                # Show endpoint only for LIVE and 1D
                if getattr(self, "_endpoint", None):
                    if self._tf in ("LIVE", "1D"):
                        self._endpoint.setData([xs[-1]], [ys[-1]])
                    else:
                        self._endpoint.setData([], [])
            except Exception as e:
                log.error(f"_replot_from_cache setData failed: {e}")
                return

            with contextlib.suppress(Exception):
                self._update_trails_and_glow()

            try:
                self._auto_range(xs, ys)
            except Exception:
                with contextlib.suppress(Exception):
                    self._plot.getPlotItem().enableAutoRange(x=True, y=True)
        else:
            try:
                self._line.setData([], [])
                if getattr(self, "_endpoint", None):
                    self._endpoint.setData([], [])
            except Exception:
                pass

        # Also enforce ripple visibility based on timeframe
        try:
            if self._tf not in ("LIVE", "1D"):
                for ripple in getattr(self, "_ripple_items", []) or []:
                    ripple.setData([], [])
        except Exception:
            pass

    def _update_trails_and_glow(self) -> None:
        """Update trailing lines and glow effect with current data."""
        if not self._equity_points or not getattr(self, "_line", None):
            return
        try:
            pts = self._filtered_points_for_current_tf()
            if pts:
                xs, ys = zip(*pts)
                # Update trail lines with fractional data
                for trail_item in getattr(self, "_trail_lines", []) or []:
                    if hasattr(trail_item, "_trail_take"):
                        take = trail_item._trail_take
                        start_idx = max(0, int(len(xs) * (1 - take)))
                        trail_item.setData(xs[start_idx:], ys[start_idx:])
                # Update glow line
                if getattr(self, "_glow_line", None):
                    self._glow_line.setData(xs, ys)
        except Exception as e:
            log.debug(f"_update_trails_and_glow error: {e}")

    def set_equity_series(self, points: Iterable[tuple[float, float]]) -> None:
        """
        Store full series in cache and draw only the slice matching the active TF.
        """
        self._equity_points = list(points or [])
        log.debug(f"Cached {len(self._equity_points)} equity points")

        if not getattr(self, "_line", None) or not getattr(self, "_plot", None):
            log.warning("No graph or line available!")
            return

        self._replot_from_cache()

        # Calculate and display PnL for the current timeframe
        self._update_pnl_for_current_tf()

    def update_equity_series(self, xs: Sequence[float], ys: Sequence[float]) -> None:
        try:
            if xs and ys and len(xs) == len(ys):
                self.set_equity_series(zip(xs, ys))
            else:
                self.set_equity_series([])
        except Exception:
            pass

    def refresh(self) -> None:
        with contextlib.suppress(Exception):
            self.update()

    # -------------------- Public API (end) -----------------------------------

    # -------------------- Internal wiring (start) ----------------------------
    def _auto_range(self, xs, ys) -> None:
        if not self.has_graph() or not xs or not ys:
            return

        # FIX: Set X range based on timeframe window, not just data extent
        # This prevents over-zooming when there are few data points
        cfg = self._tf_configs.get(self._tf, {})
        window_sec = cfg.get("window_sec")

        if window_sec:
            # Use the timeframe window to set X range
            # Latest time on RIGHT, oldest time on LEFT
            x_max = max(xs)  # Latest data point (RIGHT side)
            x_min = x_max - window_sec  # Start of window (LEFT side)
        else:
            # YTD or no window - fit to data
            x_min, x_max = min(xs), max(xs)

        y_min, y_max = min(ys), max(ys)
        if y_min == y_max:
            pad = max(1.0, abs(y_min) * 0.01)
            y_min -= pad
            y_max += pad
        try:
            self._plot.setXRange(x_min, x_max, padding=0.02)
            self._plot.setYRange(y_min, y_max, padding=0.10)
        except Exception:
            with contextlib.suppress(Exception):
                self._plot.enableAutoRange(axis="xy")

    def _compose_pnl_header_text(self) -> str:
        """Format PnL as: ICON $amount (percentage%)

        Example: + $50.00 (5.80%) for gains
        Example: - $50.00 (5.80%) for losses
        Example: - $0.00 (0.00%) for neutral/zero
        """

        if self._pnl_val is None or self._pnl_pct is None:
            # Panel 1 should show $0.00 (0.00%) in neutral color, not dashes
            return "- $0.00 (0.00%)"

        # Get absolute values (always display positive amounts with icon to show direction)
        pnl_abs = abs(self._pnl_val)
        pct_abs = abs(self._pnl_pct)

        # If PnL is essentially zero, show neutral icon
        if self._pnl_up is None:
            icon = "-"
        else:
            # Choose icon based on direction
            icon = "+" if self._pnl_up else "-"

        # Format: ICON $amount (percentage%)
        result = f"{icon} ${pnl_abs:,.2f} ({pct_abs:.2f}%)"
        return result

    def _apply_pnl_to_header(self) -> None:
        col = _pnl_color(self._pnl_up)
        text = self._compose_pnl_header_text()
        self.lbl_pnl.setText(text)
        self.lbl_pnl.setStyleSheet(
            f"color:{col}; "
            f"{ColorTheme.font_css(int(THEME.get('pnl_font_weight')), int(THEME.get('pnl_font_size')))};"
        )

    def _apply_pnl_to_pills(self, up: Optional[bool]) -> None:
        try:
            if hasattr(self.pills, "set_active_color"):
                self.pills.set_active_color(_pnl_color(up))
            if hasattr(self.pills, "set_live_dot_visible"):
                self.pills.set_live_dot_visible(self._tf == "LIVE")
            if hasattr(self.pills, "set_live_dot_pulsing"):
                self.pills.set_live_dot_pulsing(self._tf == "LIVE")
        except Exception:
            pass

    def _recolor_endpoint(self) -> None:
        if not self.has_graph() or self._endpoint is None:
            return
        try:
            if self._pnl_up is None:
                brush = pg.mkBrush(150, 150, 150, 255) if pg else None
            else:
                hexcol = _pnl_color(self._pnl_up)
                brush = pg.mkBrush(QtGui.QColor(hexcol)) if pg else None
            if brush:
                self._endpoint.setBrush(brush)
        except Exception:
            pass

    # -------------------- Internal wiring (end) ------------------------------

    # -------------------- Timeframe change (start) ---------------------------
    def _on_investing_tf_changed(self, tf: str) -> None:
        """Handle timeframe selection from pills or external calls."""
        if tf not in ("LIVE", "1D", "1W", "1M", "3M", "YTD"):
            return
        self._tf = tf
        self.timeframeChanged.emit(tf)

        # Update pill visuals & pulsing
        self._update_live_pill_dot(pulsing=(tf == "LIVE"))
        self._recolor_endpoint()

        # Keep pill color aligned with current PnL direction
        try:
            if hasattr(self.pills, "set_active_color"):
                self.pills.set_active_color(_pnl_color(self._pnl_up))
        except Exception:
            pass

    def _update_live_pill_dot(self, pulsing: bool) -> None:
        """Show the LIVE dot and toggle pulsing; safe if widget lacks these hooks."""
        try:
            if hasattr(self.pills, "set_live_dot_visible"):
                self.pills.set_live_dot_visible(True)
            if hasattr(self.pills, "set_live_dot_pulsing"):
                self.pills.set_live_dot_pulsing(bool(pulsing))
        except Exception:
            pass

    # -------------------- Timeframe change (end) -----------------------------

    # -------------------- Hover / Scrubbing (start) --------------------------
    def _init_hover_elements(self) -> None:
        """Create a taller solid hover line with timestamp restored to its original placement."""
        if not self.has_graph():
            return
        try:
            # Hover line (85% height, as current)
            self._hover_seg = QtWidgets.QGraphicsLineItem()
            self._hover_seg.setPen(pg.mkPen(THEME.get("fg_muted"), width=1))
            self._hover_seg.setZValue(100)
            self._hover_seg.setVisible(False)
            self._plot.getPlotItem().scene().addItem(self._hover_seg)

            # Timestamp text (restored original Y position) - universal skeleton font
            # Convert OKLCH to hex for PyQtGraph, then create QColor for proper PyQtGraph handling
            text_hex = normalize_color(THEME.get("ink"))
            text_qcolor = QtGui.QColor(text_hex)
            self._hover_text = pg.TextItem("", color=text_qcolor, anchor=(0.5, 1.0))
            # Set font to match universal skeleton (16px weight 500)
            font = QtGui.QFont(THEME.get("font_family"))
            font.setPixelSize(int(THEME.get("font_size")))
            font.setWeight(int(THEME.get("font_weight")))
            self._hover_text.setFont(font)
            self._hover_text.setZValue(101)
            self._hover_text.setVisible(False)
            self._plot.addItem(self._hover_text)

            # Mouse move connection
            self._plot.scene().sigMouseMoved.connect(self._on_mouse_move)
            self._plot.viewport().installEventFilter(self)
        except Exception:
            self._hover_seg = None
            self._hover_text = None

    def eventFilter(self, obj, event) -> bool:
        """Hide hover artifacts when cursor leaves the plot viewport."""
        try:
            if self._plot and obj == self._plot.viewport() and event.type() == QtCore.QEvent.Type.Leave:
                if self._hover_seg:
                    self._hover_seg.setVisible(False)
                if self._hover_text:
                    self._hover_text.setVisible(False)
                self._hovering = False
                self._scrub_x = None
                self._apply_pnl_to_header()
                return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _on_mouse_move(self, pos) -> None:
        """Keep hover bar tall but restore timestamp height; clamp inside left/right borders."""
        if not self._plot or self._vb is None:
            return

        # Use filtered points for the current timeframe instead of full history
        pts = self._filtered_points_for_current_tf()
        if not pts:
            if self._hover_seg:
                self._hover_seg.setVisible(False)
            if self._hover_text:
                self._hover_text.setVisible(False)
            return


        scene_rect = self._plot.sceneBoundingRect()
        if not scene_rect.contains(pos):
            if self._hover_seg:
                self._hover_seg.setVisible(False)
            if self._hover_text:
                self._hover_text.setVisible(False)
            return

        vb = self._vb
        mp = vb.mapSceneToView(pos)
        x_mouse = float(mp.x())

        # Clamp to visible range
        xr, yr = vb.viewRange()
        if x_mouse < xr[0] or x_mouse > xr[1]:
            return

        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]

        # FIX: Find nearest actual data point instead of snapping to arbitrary intervals
        # The old logic created timestamps outside the data range
        idx = self._find_nearest_index(xs, x_mouse)
        if idx is None:
            return

        x = float(xs[idx])
        y = float(ys[idx])
        self._hovering = True
        self._scrub_x = x

        # Hover line — keep current (85% height)
        if self._hover_seg:
            y_min, y_max = yr[0], yr[1]
            y_span = y_max - y_min
            frac = 0.85
            y_top = y_min + y_span * frac

            p0 = vb.mapViewToScene(QtCore.QPointF(x, y_min))
            p1 = vb.mapViewToScene(QtCore.QPointF(x, y_top))
            self._hover_seg.setLine(p0.x(), p0.y(), p1.x(), p1.y())
            if not self._hover_seg.isVisible():
                self._hover_seg.setVisible(True)

        # Timestamp — restore original higher placement
        if self._hover_text:
            from datetime import datetime

            dt = datetime.fromtimestamp(x)
            if self._tf in ("LIVE", "1D"):
                t = dt.strftime("%I:%M %p").lstrip("0")
            elif self._tf in ("1W", "1M"):
                t = dt.strftime("%b %d, %I:%M %p").replace(" 0", " ").lstrip("0")
            else:
                t = dt.strftime("%b %d, %Y").replace(" 0", " ")

            y_min, y_max = yr[0], yr[1]
            y_span = y_max - y_min
            y_top = y_min + y_span * 0.92  # raise timestamp higher again

            pad = (xr[1] - xr[0]) * 0.02
            x_clamped = max(xr[0] + pad, min(xr[1] - pad, x))

            self._hover_text.setText(t)
            self._hover_text.setPos(x_clamped, y_top)
            if not self._hover_text.isVisible():
                self._hover_text.setVisible(True)

        # Header update
        self._update_header_for_hover(x, y)

    # -------------------- Hover / Scrubbing (end) ----------------------------

    # -------------------- Hover calculations (start) -------------------------
    def _update_header_for_hover(self, x: float, y: float) -> None:
        """Update balance/PnL display for hovered point."""
        self.lbl_balance.setText(_fmt_money(y))

        # Get baseline from full equity history (not just filtered points)
        baseline = self._get_baseline_for_tf(x)
        if baseline is None:
            # If no baseline found, show just the balance
            self.lbl_pnl.setText("—  —")
            return

        pnl = y - baseline
        if abs(pnl) < 0.01:
            self.lbl_pnl.setText("$0.00 (0.00%)")
            return

        pct = 0.0 if baseline == 0 else (pnl / baseline) * 100.0
        up = pnl > 0
        tri = "+" if up else "-"
        col = _pnl_color(up)
        self.lbl_pnl.setText(f"{tri} ${abs(pnl):,.2f} ({abs(pct):.2f}%)")
        self.lbl_pnl.setStyleSheet(
            f"color:{col}; "
            f"{ColorTheme.font_css(int(THEME.get('pnl_font_weight')), int(THEME.get('pnl_font_size')))};"
        )

    def _get_baseline_for_tf(self, at_time: float) -> Optional[float]:
        """Get the baseline value for PnL calculation based on timeframe."""
        if not self._equity_points:
            return None

        import bisect
        from datetime import datetime

        xs = [p[0] for p in self._equity_points]
        ys = [p[1] for p in self._equity_points]

        if self._tf == "LIVE":
            baseline_time = at_time - 3600
        elif self._tf == "1D":
            dt = datetime.fromtimestamp(at_time)
            baseline_time = datetime(dt.year, dt.month, dt.day).timestamp()
        elif self._tf == "1W":
            baseline_time = at_time - 604800
        elif self._tf == "1M":
            baseline_time = at_time - 2592000
        elif self._tf == "3M":
            baseline_time = at_time - 7776000
        else:  # YTD
            dt = datetime.fromtimestamp(at_time)
            baseline_time = datetime(dt.year, 1, 1).timestamp()

        i = bisect.bisect_right(xs, baseline_time)
        if i == 0:
            return ys[0]
        return ys[i - 1]

    def _find_nearest_index(self, xs: list, target_x: float) -> Optional[int]:
        """Find index of nearest x (snap-aware)."""
        if not xs:
            return None
        import bisect

        i = bisect.bisect_right(xs, target_x)

        if i == 0:
            return 0
        if i >= len(xs):
            return len(xs) - 1

        result = i if abs(xs[i] - target_x) < abs(xs[i - 1] - target_x) else i - 1
        return result

    # -------------------- Hover calculations (end) ---------------------------

    # -------------------- Signal Wiring (start) --------------------------------
    def _wire_balance_signal(self) -> None:
        """Connect StateManager balance and mode signals to update display."""
        try:
            from core.app_state import get_state_manager

            state = get_state_manager()
            if state:
                # Connect balance signal
                if hasattr(state, "balanceChanged"):
                    state.balanceChanged.connect(self._on_balance_changed)
                    log.info("[Panel1] Connected balance signal")

                # Connect mode change signal
                if hasattr(state, "modeChanged"):
                    state.modeChanged.connect(self._on_mode_changed)
                    log.info("[Panel1] Connected mode change signal")
        except Exception as e:
            log.error(f"[Panel1] Failed to wire signals: {e}")

    def _on_balance_changed(self, balance: float) -> None:
        """Called when StateManager emits balanceChanged signal.
        CRITICAL: Only display balance for the current trading mode.
        """
        try:
            # Get current mode from state manager to know which balance to display
            from core.app_state import get_state_manager
            state = get_state_manager()
            current_mode = state.current_mode if state else "SIM"

            # Get the balance for the current mode
            if state:
                display_balance = state.get_balance_for_mode(current_mode)
            else:
                display_balance = balance

            # CRITICAL: Only update display if this balance is for the current mode
            # The balance parameter is ignored - we use get_balance_for_mode to get the right value

            if hasattr(self, "lbl_balance") and self.lbl_balance:
                self.lbl_balance.setText(_fmt_money(display_balance))
                # Force Qt repaint to display the change immediately
                self.lbl_balance.update()
                self.lbl_balance.repaint()
                log.debug(f"[Panel1] Balance updated to: ${display_balance:.2f}")

                # CRITICAL: Also update the equity curve and PnL display for the current timeframe
                self.update_equity_series_from_balance(display_balance, mode=current_mode)
            else:
        except Exception as e:
            log.error(f"[Panel1] Error updating balance display: {e}")

    def _on_mode_changed(self, new_mode: str) -> None:
        """Called when mode switches (SIM <-> LIVE)"""
        # Update Panel1's display mode to match StateManager
        self._current_display_mode = new_mode

        # CRITICAL: Update balance display for the new mode
        try:
            from core.app_state import get_state_manager
            state = get_state_manager()
            if state:
                new_balance = state.get_balance_for_mode(new_mode)
                if hasattr(self, "lbl_balance") and self.lbl_balance:
                    self.lbl_balance.setText(_fmt_money(new_balance))
                    self.lbl_balance.update()
                    self.lbl_balance.repaint()
        except Exception as e:

        # Refresh the PnL display with the new mode's data
        with contextlib.suppress(Exception):
            self._update_pnl_for_current_tf()

    # -------------------- Signal Wiring (end) --------------------------------

    # -------------------- Diagnostics (start) --------------------------------
    def _debug_sizes(self) -> None:
        """Debug method to check widget sizes after layout."""
        log.debug("=== SIZE DEBUG ===")
        log.debug(f"Panel1 visible: {self.isVisible()}")
        log.debug(f"Panel1 size: {self.size().width()}x{self.size().height()}")
        log.debug(f"Graph container visible: {self.graph_container.isVisible()}")
        log.debug(f"Graph container size: {self.graph_container.size().width()}x{self.graph_container.size().height()}")
        if self._plot:
            log.debug(f"Plot visible: {self._plot.isVisible()}")
            log.debug(f"Plot size: {self._plot.size().width()}x{self._plot.size().height()}")
        log.debug("=== END SIZE DEBUG ===")

    # -------------------- Diagnostics (end) ----------------------------------
