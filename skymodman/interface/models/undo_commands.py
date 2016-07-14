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

class ChangeModAttributeCommand(UndoCmd):
    """
    Used to change a mod attribute *other* than ordinal
    (i.e. do not use this when the mod's install order is
    being changed)


    """

    __slots__ = ("mod", "attr", "old_val", "new_val")

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
            text="Remove Mod" + ("s" if last > first else "")
        super().__init__(text=text, *args, **kwargs)

        self._model = model
        self.start = first
        self.end = last+1 # the slice-end

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


class ClearMissingModsCommand(UndoCmd):

    def __init__(self, model, text="Clear Missing Mods", *args, **kwargs):
        super().__init__(text=text, *args, **kwargs)

        self._model = model
        self._count = len(model.mod_entries)

        # a dopple-list
        self.removed = [None] * self._count
        self.remaining = [None] * self._count


    def _redo_(self):
        entries = self._model.mod_entries
        is_missing = self._model.mod_missing

        for i in range(self._count):
            m = entries[i]
            if is_missing(m):
                self.removed[i] = m
            else:
                self.remaining[i] = m

        # re-assign the mod_entries list to only those mods that
        # remained after removing all the missing
        ## --filter the self.remaining projection to the non-None items
        self._model.mod_entries = list(filter(lambda e: e is not None, self.remaining))

    def _undo_(self):

        # combine the non-None entries from our two saved lists
        # back into a single list
        self._model.mod_entries = [
            self.removed[i]
                if self.removed[i] is not None
                else self.remaining[i]
            for i in range(self._count)
        ]

        # reset the storage arrays
        self.removed = [None] * self._count
        self.remaining = [None] * self._count






