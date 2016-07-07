from contextlib import contextmanager

@contextmanager
def blocked_signals(qt_object):
    """A context manager that takes any QObject and blocks signals on it while the
    embedded statements are being executed, then reenables them."""
    qt_object.blockSignals(True)
    yield
    qt_object.blockSignals(False)
