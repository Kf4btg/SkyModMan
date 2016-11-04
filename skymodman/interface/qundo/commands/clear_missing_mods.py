from PyQt5.QtWidgets import QUndoCommand

# from ..undocmd import UndoCmd
#
# class ClearMissingModsCommand(UndoCmd):
#
#     def __init__(self, model, text="Clear Missing Mods", *args, **kwargs):
#         super().__init__(text=text, *args, **kwargs)
#
#         self._model = model
#         self._count = len(model.mods)
#
#         # a dopple-list
#         self.removed = [None] * self._count
#         self.remaining = [None] * self._count
#
#
#     def _redo_(self):
#         entries = self._model.mods
#         is_missing = self._model.mod_missing
#
#         for i in range(self._count):
#             m = entries[i]
#             if is_missing(m):
#                 self.removed[i] = m
#             else:
#                 self.remaining[i] = m
#
#         # re-assign the mod_entries list to only those mods that
#         # remained after removing all the missing
#         ## --filter the self.remaining projection to the non-None items
#         entries.clear()
#         entries.extend(
#             filter(lambda e: e is not None, self.remaining))
#
#     def _undo_(self):
#
#         # combine the non-None entries from our two saved lists
#         # back into a single list
#         self._model.mods.clear()
#         self._model.mods.extend([
#             self.removed[i]
#                 if self.removed[i] is not None
#                 else self.remaining[i]
#             for i in range(self._count)
#         ])
#
#         # reset the storage arrays
#         self.removed = [None] * self._count
#         self.remaining = [None] * self._count


class ClearMissingModsCommand(QUndoCommand):

    # noinspection PyArgumentList
    def __init__(self, model, text="Clear Missing", *args, **kwargs):
        if text:
            super().__init__(text, *args, **kwargs)
        else:
            super().__init__(*args, **kwargs)

        self._model = model # ModTable_TreeModel

        # get list of mods marked missing at this moment

        _missing = list(model.missing_mods())

        # group into sequential...sequences

        self.groups = []
        curr_group = []
        last_ord = _missing[0].ordinal - 1

        # I had come up with some crazy keyfunc to use with
        # itertools.groupby(), but this is a fair bit simpler:

        for m in _missing:
            o=m.ordinal

            # if current ordinal is imm. after the previous missing
            # mod, group them into a single sequence
            if o == last_ord + 1:
                # store mod entries w/ their current ordinal
                # since, once they're removed, the `ordinal`
                # property on the ModEntry instance will no longer
                # return a meaningful value;
                # this essentially makes curr_group an OrderedDict
                curr_group.append((o, m))
            else:
                # otherwise add the current sequence to the collection
                # of sequential mods
                self.groups.append(curr_group)
                # and start a new sequence with this mod
                curr_group = [(o, m)]

            # update last seen ordinal
            last_ord = o

        # add the final group to the list-list
        if curr_group:
            self.groups.append(curr_group)

    def redo(self):
        """remove the mods from the model/collection"""

        # remove them in groups of sequential indices

        # probably best to block signals and just call a model reset
        self._model.beginResetModel()
        self._model.blockSignals(True)

        for g in self.groups:
            # g is a list of (int, ModEntry) tuples
            self._model.remove_rows(g[0][0], len(g))

        self._model.blockSignals(False)
        # have model re-evaluate the current errors
        self._model.check_mod_errors(True)
        self._model.endResetModel()



    def undo(self):
        """
        Insert the previously removed ModEntries back into the model/
        collection
        """

        self._model.beginResetModel()
        self._model.blockSignals(True)

        # send each group of sequential entries to the model
        for g in self.groups:
            self._model.insert_entries(g[0][0], [e for o,e in g])

        self._model.blockSignals(False)
        # have model re-evaluate the current errors
        self._model.check_mod_errors(True)
        self._model.endResetModel()


cmd = ClearMissingModsCommand
