# graph_diagnostics.py
from PyQt6 import QtCore, QtWidgets
import pyqtgraph as pg

from config.theme import THEME
from core.app_manager import MainWindow


app = QtWidgets.QApplication([])
win = MainWindow()
win.show()


def print_graph_metrics():
    try:
        p = getattr(win.panel_balance, "_plot", None)
        c = getattr(win.panel_balance, "graph_container", None)
        if not p or not c:
            print("[Diag] Graph or container not found.")
            return
        print("\n==== Graph Diagnostics ====")
        print(f"Container visible: {c.isVisible()}")
        print(f"Container size: {c.width()}x{c.height()}")
        print(f"Plot visible: {p.isVisible()}")
        print(f"Plot size: {p.width()}x{p.height()}")
        lay = c.layout()
        if lay:
            m = lay.contentsMargins()
            print(f"Layout margins: L={m.left()}, T={m.top()}, R={m.right()}, B={m.bottom()}")
            print(f"Layout spacing: {lay.spacing()}")
        vb = p.getPlotItem().getViewBox()
        print(f"ViewBox autoRangeEnabled: {vb.state.get('autoRangeEnabled', None)}")
        print(f"ViewBox defaultPadding: {vb.state.get('defaultPadding', 'n/a')}")
        print("============================\n")
    except Exception as e:
        print(f"[Diag ERROR] {e}")


timer = QtCore.QTimer()
timer.timeout.connect(print_graph_metrics)
timer.start(3000)

app.exec()
