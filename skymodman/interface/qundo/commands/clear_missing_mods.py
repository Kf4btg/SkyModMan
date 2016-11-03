from ..undocmd import UndoCmd

class ClearMissingModsCommand(UndoCmd):

    def __init__(self, model, text="Clear Missing Mods", *args, **kwargs):
        super().__init__(text=text, *args, **kwargs)

        self._model = model
        self._count = len(model.mods)

        # a dopple-list
        self.removed = [None] * self._count
        self.remaining = [None] * self._count


    def _redo_(self):
        entries = self._model.mods
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
        entries.clear()
        entries.extend(
            filter(lambda e: e is not None, self.remaining))

    def _undo_(self):

        # combine the non-None entries from our two saved lists
        # back into a single list
        self._model.mods.clear()
        self._model.mods.extend([
            self.removed[i]
                if self.removed[i] is not None
                else self.remaining[i]
            for i in range(self._count)
        ])

        # reset the storage arrays
        self.removed = [None] * self._count
        self.remaining = [None] * self._count


cmd = ClearMissingModsCommand