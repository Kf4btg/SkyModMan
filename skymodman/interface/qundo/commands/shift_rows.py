from skymodman.utils.shifter import shifter
from ..undocmd import UndoCmd

class ShiftRowsCommand(UndoCmd):

    __slots__ = ("_start", "_end", "_model", "_shift")

    def __init__(self, model,
                 start, end, dest,
                 text="Reorder Mods", *args, **kwargs):
        """

        :param model: the TreeModel for the mods table

        :param int start: initial starting row of the range of items
        :param int end: final row of the range
        :param int dest: destination row for the head of the range

        :param str text: optional text that will appear in the
            Undo/Redo menu items

        """
        super().__init__(text=text, *args, **kwargs)
        self._start = start
        self._end = end

        # self.list = collection
        # to simplify things, we're just going to grab a reference to
        # the model itself. It may not be the most correct thing to do,
        # but I like it better than exceedingly complex callbacks or
        # passing two dozen different parameters
        self._model = model

        self._shift = shifter(model.mod_entries, start, end, dest)

    @property
    def shifter(self):
        return self._shift

    def _redo_(self):
        """perform shift in "forward" direction"""
        self._shift()

        self._model.endMoveRows()

        # add the indices of each shifted row to the model's modified-
        # rows tracker
        self._model.mark_modified(self._shift.affected_range)

    def _undo_(self):
        # undo just involves rotating in the opposite direction,
        # so we call shift() with reverse=True
        self._shift(True)

        self._model.endMoveRows()
        # chop the most recent entries off the model's
        # modifed-rows tracker
        self._model.unmark_modified(len(self._shift.affected_range))

cmd = ShiftRowsCommand