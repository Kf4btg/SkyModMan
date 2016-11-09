from PyQt5.QtWidgets import QUndoCommand

class HideDirectoryCommand(QUndoCommand):
    """Command for hiding/unhiding a folder (and thereby all of its
    contents)"""

    def __init__(self, item, model, hide, text="", *args, **kwargs):
        """

        :param skymodman.interface.typedefs.QFSItem item: the QFSitem
            corresponding to the directory clicked
        :param model: the FileTree Model
        :param hide: whether the folder (and its contents) should
            be unchecked (`hide`==True) or checked
        :param text: Undo command text (leave blank for default)
        """

        self._setchecked = not hide

        if not text:
            text = "{} Files".format("Unhide" if self._setchecked else "Hide")

        super().__init__(text, *args, **kwargs)

        self.model = model

        # row path to clicked directory
        self.dir_path = item.row_path

        # get snapshot of currently hidden files under this dir;
        # use 'relative' row-paths from the clicked directory.
        # the checkstates will be forcefully reapplied on undo

        # curr_state = list of tuples:
        # [(row_path, is_hidden), ...] for each child item (file/dir)
        # in dir

        # intialize w/ the current checkstate of the clicked-upon
        # directory
        curr_state = [((None,), item.checkState)] # type: list [tuple[tuple[int], int]]

        def _(base_path):
            for c in item.iterchildren(True):

                # append row path as tuple(row, row, row...),
                # then value as int (Qt.*Checked)
                curr_state.append(
                    (tuple(base_path + [c.row]), c.checkState)
                )
                if c.isdir:
                    # recurse, extending the base rel-path with row
                    # of child directory
                    _(base_path+[c.row])
                # else:
                #     curr_state.append(
                #         (tuple(base_path+[c.row]), c.checkState)
                #     )

        # build snapshot, starting w/ empty list (path)
        _([])

        # save the "current state" as the state to revert to during undo
        self.undo_state = curr_state

    def redo(self):

        # FSItem-hierarchy from top-lvl to clicked dir
        item_path = self.model.item_path_from_row_path(self.dir_path)

        base_dir = item_path[-1]

        # now just call set_checked on last item in item_path,
        # and checkstate will cascade down
        last_item_changed = base_dir.setChecked(self._setchecked, recurse=True)

        # now we need to emit data changed for several things:
        # first, the range from the clicked directory to the final
        # modified item.
        # Then, for each parent directory in the clicked-dir's path

        self.model.emit_itemDataChanged(item_path[-1],
                                        last_item_changed)

        for ppart in item_path[:-1]:
            # make sure to invalidate the cached child_states
            # for the parents in the hierarchy
            ppart._invalidate_child_state()
            self.model.emit_itemDataChanged(ppart, ppart)


    def undo(self):
        """Here, we need to set the state of the hidden files to what
        it was before the cascade-change"""

        item_path = self.model.item_path_from_row_path(self.dir_path)

        base_dir = item_path[-1]

        # all row-paths in undo_state are relative to the base-dir
        # (the folder the user clicked on)

        item=base_dir
        for rpath, check_state in self.undo_state:
            item=base_dir
            for r in rpath:
                item=item[r]

            item.force_set_checkstate(check_state)

        # after loop, "item" should be the 'bottom_right' affected item

        self.model.emit_itemDataChanged(base_dir, item)

        for ppart in item_path[:-1]:
            # make sure to invalidate the cached child_states
            # for the parents in the hierarchy
            ppart._invalidate_child_state()
            self.model.emit_itemDataChanged(ppart, ppart)


class HideFileCommand(QUndoCommand):
    """Command for hiding a single file in the file-tree view"""

    def __init__(self, item, model, text="", *args, **kwargs):

        # we'll be toggling the current state; so, if it is currently
        # hidden, we'll want to check (unhide) it.
        self._setchecked = item.hidden


        if not text:
            text = "{} File".format("Unhide" if self._setchecked else "Hide")

        super().__init__(text, *args, **kwargs)

        self.model = model

        # get tree-descent path to item
        self.path = item.row_path



    def _do(self, reverse=False):

        set_checked = self._setchecked
        if reverse: set_checked = not set_checked

        # this gets us a sequence of FSItems, starting with the
        # top-level folder all the way down to the file that was
        # changed
        file_path = self.model.item_path_from_row_path(self.path)

        # the last item will the file that should be changed
        file_path[-1].setChecked(set_checked, False)

        # emit data changed for the item and each parent folder

        for ppart in file_path: # each is a QFSItem
            # invalidate cached checkstate for folders so they
            # will recalculate it.
            ppart._invalidate_child_state()
            self.model.emit_itemDataChanged(ppart, ppart)
            # index = self.model.getIndexFromItem(ppart)
            # self.model.emit_dataChanged(index, index)


    def redo(self):
        self._do()


    def undo(self):
        self._do(True)

