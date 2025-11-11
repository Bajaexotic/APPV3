from PyQt6 import QtCore, QtWidgets


class _UiInvoker(QtCore.QObject):
    call_sig = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.call_sig.connect(lambda fn: fn())


def ui_thread(func):
    def wrapper(self, *args, **kwargs):
        app = QtWidgets.QApplication.instance()
        if app is not None and QtCore.QThread.currentThread() is not app.thread():
            if not hasattr(self, "_ui_invoke") or self._ui_invoke is None:
                self._ui_invoke = _UiInvoker(self)
            self._ui_invoke.call_sig.emit(lambda: func(self, *args, **kwargs))
            return
        return func(self, *args, **kwargs)

    return wrapper
