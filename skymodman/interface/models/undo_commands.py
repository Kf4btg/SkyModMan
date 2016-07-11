from collections import deque

from PyQt5.QtWidgets import QUndoCommand

from skymodman.utils import shifter


class UndoCmd(QUndoCommand):
    """
    Common base class for an undo commands with callbacks.
    Deriving classes can simply override _undo_() and _redo_()
    to define the true functionality of their undo/redo methods
    and the pre/post callbacks will be made automatically.
    Alternatively, they could override redo() and undo() themselves
    to skip the callbacks or make adjustments.
    """

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

class ChangeModAttributeCommand(UndoCmd):
    """
    Used to change a mod attribute *other* than ordinal
    (i.e. do not use this when the mod's install order is
    being changed)


    """
    def __init__(self, mod_entry, attribute, value, text="Change {}", *args, **kwargs):
        """
        :param QModEntry mod_entry: the mod object
        :param str attribute: name of the attribute to change
        :param value: the new value of the attribute
        """
        super().__init__(text=text.format(attribute), *args, **kwargs)

        self.mod = mod_entry
        self.attr = attribute
        self.old_val = getattr(self.mod, self.attr)
        self.new_val = value


    def _redo_(self):
        """
        Also known as "do". Change to value of the attribute from the
        old value to the new.
        """

        setattr(self.mod, self.attr, self.new_val)

    def _undo_(self):
        """
        Restore the original value of the attribute
        """
        setattr(self.mod, self.attr, self.old_val)


class ShiftRowsCommand(UndoCmd):

    def __init__(self, model,
                 start, end, dest, # begin_move_rows, end_move_rows, parent_index,
                 # range_start, range_end, count, step,
                 text="Reorder Mods", *args, **kwargs):
        """

        :param model: the TreeModel for the mods table

        :param int range_start: initial starting row of the range of items
        :param int range_end: final row of the range
        :param int count: how many rows are being moved

        :param int step: either 1 or -1, depending on whether we're
            shifting up or down, respectively
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


        # self.range_start = range_start
        # self.range_end = range_end
        # self.count = count
        # self.step = step

    @property
    def shifter(self):
        return self._shift


    # def _do_shift(self, sequence, slice_start, slice_end, count, vector):
    #
    #     # modlist = self._model.mod_entries
    #
    #     # copy the slice into a deque;
    #     deck = deque(sequence[slice_start:slice_end])
    #
    #     # rotate the deck in the opposite direction and voila!
    #     # its like we shifted everything.
    #     deck.rotate(count * vector)
    #
    #     # pop em back in, replacing the entry's ordinal to reflect
    #     # the mod's new position
    #     for i in range(slice_start, slice_end):
    #         # mod = deck.popleft()
    #         # mod.ordinal = i+1
    #         sequence[i] = deck.popleft()
    #         # self.list[i] = deck.popleft()
    #         # self.list[i].ordinal = i+1

    def _redo_(self):
        # call shift with the regular step value
        # self._do_shift(self._model.mod_entries, self.range_start, self.range_end, self.count,
        #                self.step)

        self._shift()

        self._model.endMoveRows()
        # add the indices of each shifted row to the model's modified-
        # rows tracker
        self._model.mark_modified(range(self._start, self._end))

    def _undo_(self):
        # undo just involves rotating in the opposite direction
        # self._do_shift(self.range_start, self.range_end, self.count,
        #                -self.step)

        self._shift(True)

        self._model.endMoveRows()
        # chop the most recent entries off the model's modifed-rows
        # tracker
        self._model.unmark_modified(self._end - self._start)


class RemoveRowsCommand(UndoCmd):
    
    def __init__(self, model, start, end, text=None, *args, **kwargs):
        """

        :param model:
        :param int start:
        :param int end:
        :param text:
        :param args:
        :param kwargs:
        """
        if text is None:
            text="Reorder Mod" + ("s" if start != end else "")
        super().__init__(text=text, *args, **kwargs)

        self._model = model
        self.start = start
        self.end = end

        self.removed = []




