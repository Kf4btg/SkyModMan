from ..undocmd import UndoCmd


class RemoveRowsCommand(UndoCmd):
    __slots__ = ("_model", "start", "end", "removed")

    def __init__(self, model, first, last, text=None, *args, **kwargs):
        """

        :param model:
        :param int first:
        :param int last:
        :param text:
        :param args:
        :param kwargs:
        """
        if text is None:
            text = "Remove Mod" + ("s" if last > first else "")
        super().__init__(text=text, *args, **kwargs)

        self._model = model
        self.start = first
        self.end = last + 1  # the slice-end

        # keep track of removed entries
        self.removed = model.mod_entries[self.start:self.end]

    def _redo_(self):
        # just blank out the section
        self._model.mod_entries[self.start:self.end] = []

    def _undo_(self):
        # plug the stuff back in, immediately before the index
        # from where it was removed

        # so, this works...but is it right?
        self._model.mod_entries[self.start:self.start] = self.removed


cmd = RemoveRowsCommand