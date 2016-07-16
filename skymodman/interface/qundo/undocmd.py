from PyQt5.QtWidgets import QUndoCommand
class UndoCmd(QUndoCommand):
    """
    Common base class for an undo commands with callbacks.
    Deriving classes can simply override _undo_() and _redo_()
    to define the true functionality of their undo/redo methods
    and the pre/post callbacks will be made automatically.
    Alternatively, they could override redo() and undo() themselves
    to skip the callbacks or make adjustments.
    """

    # use slots because we can end up with lots of these things...
    __slots__ = ("_pre_redo", "_post_redo", "_pre_undo", "_post_undo")

    def __init__(self,
                 text="",
                 *args,
                 pre_redo_callback = None,
                 pre_undo_callback = None,
                 post_redo_callback = None,
                 post_undo_callback = None,
                 **kwargs
                 ):
        """
        Any callbacks not provided default to a ``lambda:None`` no-op

        :param str text: optional text that will appear in the
            Undo/Redo menu items

        :param pre_redo_callback:
            invoked immediately before the redo action takes place
            (even the first time)
        :param pre_undo_callback:
            invoked immediately before the undo action
        :param post_redo_callback:
            invoked immediately after the redo action
        :param post_undo_callback:
            invoked immediately after the undo action

        """
        if text:
            super().__init__(text, *args, **kwargs)
        else:
            super().__init__(*args, **kwargs)


        self._pre_redo  = pre_redo_callback  or (lambda:None)
        self._post_redo = post_redo_callback or (lambda:None)
        self._pre_undo  = pre_undo_callback  or (lambda:None)
        self._post_undo = post_undo_callback or (lambda:None)

    def _set_pre_redo(self, func):
        self._pre_redo = func
    def _set_post_redo(self, func):
        self._post_redo = func
    def _set_pre_undo(self, func):
        self._pre_undo = func
    def _set_post_undo(self, func):
        self._post_undo = func

    # create write-only properties for the callbacks
    pre_redo_callback = property(fset = _set_pre_redo)
    pre_undo_callback = property(fset = _set_pre_undo)
    post_redo_callback = property(fset = _set_post_redo)
    post_undo_callback = property(fset = _set_post_undo)

    def redo(self):
        self._pre_redo()
        self._redo_()
        self._post_redo()

    def _redo_(self):
        pass

    def undo(self):
        self._pre_undo()
        self._undo_()
        self._post_undo()

    def _undo_(self):
        pass