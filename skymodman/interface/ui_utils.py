from contextlib import contextmanager

@contextmanager
def blocked_signals(qt_object):
    """A context manager that takes any QObject and blocks signals on it while the
    embedded statements are being executed, then reenables them."""
    qt_object.blockSignals(True)
    yield
    qt_object.blockSignals(False)


@contextmanager
def undomacro(stack, text):
    """
    Any QUndoCommands made within this context manager will be
    compressed into a single macro.

    :param stack: the QUndoStack that will receive the macro. Returned
        as the value for the with...as statement.
    :param text: the text to display in the Un/Redo actions for this
        macro.
    """
    stack.beginMacro(text)
    yield stack
    stack.endMacro() # indexChanged() is emitted