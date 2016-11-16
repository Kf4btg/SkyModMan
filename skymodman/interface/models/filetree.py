from functools import lru_cache
from bisect import bisect_left
from collections import deque

from PyQt5.QtCore import Qt, QModelIndex, QAbstractItemModel, pyqtSlot
from PyQt5.QtWidgets import QUndoStack

from skymodman import Manager
from skymodman.log import withlogger #, tree
from skymodman.interface.typedefs import QFSItem

from skymodman.interface.qundo.commands.hide_files import HideFileCommand, HideDirectoryCommand


# actually provides a small (but noticeable) speedup
# Qt_Checked = Qt.Checked
Qt_Unchecked = Qt.Unchecked
# Qt_PartiallyChecked = Qt.PartiallyChecked
Qt_CheckStateRole = Qt.CheckStateRole
Qt_DisplayRole = Qt.DisplayRole
Qt_DecorationRole = Qt.DecorationRole

COLUMNS = (COL_NAME, COL_PATH, COL_CONFLICTS) = range(3)
ColHeaders = ("Name", "Path", "Conflicts")

@withlogger
class ModFileTreeModel(QAbstractItemModel):
    """
    A custom model that presents a view into the actual files saved
    within a mod's folder. It is vastly simplified compared to the
    QFileSystemModel, and only supports editing the state of the
    checkbox on each file or folder (though there is some neat trickery
    that propagates a check-action on a directory to all of its
    descendants)
    """
    #TODO: calculate and inform the user of any file-conflicts that will occur in their mod-setup to help them decide what needs to be hidden.

    # rootPathChanged = pyqtSignal(str)

    def __init__(self, parent, **kwargs):
        """

        :param parent: parent widget (specifically, the file-viewer QTreeView)
        """
        # noinspection PyArgumentList
        super().__init__(parent=parent,**kwargs)
        self._parent = parent
        self.manager = Manager() # should be initialized by now
        self.modname = None #type: str
        self.rootitem = None #type: QFSItem

        self.mod = None
        """:type: skymodman.types.ModEntry"""

        # maintain a flattened list of the files for the current mod
        self._files = [] # type: list [QFSItem]

        # set of hidden files for the current 'clean state' of the tree
        # (should correspond to entries in "hiddenfiles" db table)
        self._saved_state = set()

        self.command_queue = deque()

    def setMod(self, mod_entry):
        """Set the mod that this model is focusing on to `mod_entry`.
        Pass ``None`` to reset the model to empty"""

        # clear the index-cache
        self._locate.cache_clear()

        # tells the view to get ready to redisplay its contents
        self.beginResetModel()
        self.mod = mod_entry

        if mod_entry is None: # reset Model to show nothing
            self.rootitem=None
            self.modname=None

        else:
            # the mod's _unique_ name
            self.modname = self.mod.directory

            self._setup_or_reload_tree()

        # tells the view it should get new
        # data from model & reset itself
        self.endResetModel()

    @property
    def root_item(self):
        return self.rootitem

    @property
    def current_hidden_file_indices(self):
        """Rather than querying the database, this examines the current
        state of the FSItems in the internal _files list"""
        return [i for i, item in enumerate(self._files) if item.hidden]

    def _setup_or_reload_tree(self):
        """
        Loads thde data from the db and disk
        """
        self._load_tree()

        # now mark hidden files
        self._mark_hidden_files(self._saved_state)

        # this used to call resetModel() stuff, too, but I decided
        # this wasn't the place for that. It's a little barren now...

    def _load_tree(self):
        """
        Build the tree from the rootitem
        """
        # name for this item is never actually seen
        self.rootitem = QFSItem(path="", name="data", parent=None)


        # build yonder tree
        QFSItem.build_filetree(self.rootitem,
                               self.mod.filetree,
                               name_filter=lambda n: n.lower() == "meta.ini")

        # create flattened list of just the files
        self._files = [f for f in
                       self.rootitem.iterchildren(recursive=True)
                       if not f.isdir]

        # reset the "saved state" (indices of hidden files on load)
        self._saved_state = self._get_hidden_file_indices()


    @lru_cache()
    def _locate(self, file):
        """Given an FSItem or a file path (str), return the index of
        that item (or the item with that path) in the flattened file
        list"""

        # perform a binary search for the file/path
        i = bisect_left(self._files, file)

        # make sure the index returned is of the exact item searched for
        try:
            if self._files[i] == file:
                return i
        except IndexError:
            # this will only happen if 'file' doesn't exist in list
            # and would have come after the final item, so `i` will
            # be equal to len(self._files). Point is, file wasn't there
            pass

        raise ValueError

    def _get_hidden_file_indices(self):
        """Get the set of currently hidden files from the database
        and return a list of the indices corresponding to those files
        in self._files"""

        hidden = set()

        # the alternative to this (searching for each file by path to
        # get index) would be to do some sort of...math...or something
        # with the start/end index of the mod's entries in the database,
        # referencing position of each file returned...
        # but ehhhhhhhh, math.

        for hf in self.manager.hidden_files_for_mod(self.mod.directory):
            # NTS: As the number of hidden files approaches the total
            # number of files in the mod, this bin search algo becomes
            # less and less efficient compared to just going through
            # the loop linearly once. Might be a moot point, though,
            # as hiding the vast majority of files in a mod seems a
            # very unlikely thing to want to do.
            try:
                hidden.add(self._locate(hf))
            except ValueError:
                self.LOGGER.error("Hidden file {0!r} was not found".format(hf))

        return hidden

    def _mark_hidden_files(self, hidden_file_indices):

        # note:: if there is an IndexError here, THE WORLD WILL BURN
        for idx in hidden_file_indices:
            # use the internal _set_checkstate to avoid the
            # parent.child_state invalidation step
            self._files[idx]._set_checkstate(Qt_Unchecked, False)

    def getitem(self, index) -> QFSItem:
        """Extracts actual item from given index

        :param QModelIndex index:
        """
        if index.isValid():
            item = index.internalPointer()
            if item: return item
        return self.rootitem

    def columnCount(self, *args, **kwargs) -> int:
        """Dir/File Name(+checkbox), path to file, file conflicts """
        # return 2
        return len(COLUMNS)

    def rowCount(self, index=QModelIndex(), *args, **kwargs) -> int:
        """Number of children contained by the item referenced by `index`

        :param QModelIndex index:
        """
        # return 0 until we actually have something to show
        return self.getitem(index).child_count if self.rootitem else 0

    def headerData(self, section, orient, role=None):
        """super() call should take care of the
        size hints &c.

        :param int section:
        :param orient:
        :param role:
        """
        if orient == Qt.Horizontal and role == Qt_DisplayRole:
            return ColHeaders[section]
        return super().headerData(section, orient, role)

    def index(self, row, col, parent=QModelIndex(), *args, **kwargs):
        """

        :param int row:
        :param int col:
        :param QModelIndex parent:
        :return: the QModelIndex that represents the item at (row, col)
            with respect to the given  parent index. (or the root index
            if parent is invalid)
        """

        if parent.isValid():
            parent_item = parent.internalPointer()
        else:
            parent_item = self.rootitem

        child = parent_item[row]
        if child:
            return self.createIndex(row, col, child)

        return QModelIndex()

    def getIndexFromItem(self, item) -> QModelIndex:
        return self.createIndex(item.row, 0, item)

    # handle the 'parent' overload w/ the next two slots
    @pyqtSlot('QModelIndex', name="parent", result = 'QModelIndex')
    def parent(self, child_index=QModelIndex()):

        if not child_index.isValid():
            return QModelIndex()

        # get the parent FSItem from the reference stored in each FSItem
        parent = child_index.internalPointer().parent

        if not parent or parent is self.rootitem:
            return QModelIndex()

        # Every FSItem has a row attribute
        # which we use to create the index
        return self.createIndex(parent.row, 0, parent)

    @pyqtSlot(name='parent', result='QObject')
    def parent_of_self(self):
        return self._parent

    def flags(self, index):
        """
        Flags are held at the item level; lookup and return them from
        the item referred to by the index

        :param QModelIndex index:
        """
        return self.getitem(index).itemflags

    def data(self, index, role=Qt.DisplayRole):
        """
        We handle DisplayRole to return the filename, CheckStateRole to
        indicate whether the file has been hidden, and Decoration Role
        to return different icons for folders and files.

        :param QModelIndex index:
        :param role:
        """

        item = self.getitem(index)
        col = index.column()

        if role == Qt_DisplayRole:
            if col == COL_PATH:
                return item.parent.path + "/"
            elif col == COL_NAME:
                return item.name
            else: # column must be "Conflicts"
                try:
                    # TODO: provide a way (perhaps a drop-down list on the Conflicts column) to easily identify and navigate to the other mods containing a conflicting file
                    if item.lpath in self.manager.file_conflicts.by_mod[self.modname]:
                        return "Yes"
                # if the mod was not in the conflict map,
                # then return none
                except KeyError:
                    return None

        # if it's not the display role, we only care about the name column
        elif col == COL_NAME:
            if role == Qt_CheckStateRole:
                # hides the complexity of the tristate workings
                return item.checkState
            elif role == Qt_DecorationRole:
                return item.icon

    def setData(self, index, value, role=Qt_CheckStateRole):
        """Only the checkStateRole can be edited in this model.
        Most of the machinery for that is in the QFSItem class

        :param QModelIndex index:
        :param value:
        :param role:
        """
        if not index.isValid():
            return False

        item = self.getitem(index)

        if role == Qt_CheckStateRole:

            if item.isdir:
                cmd = HideDirectoryCommand(item, self, value==Qt_Unchecked)
            else:
                cmd = HideFileCommand(item, self)

            self.queue_command(cmd)

            return True
        return super().setData(index, value, role)

    # noinspection PyUnresolvedReferences
    def _send_data_through_proxy(self, index1, index2, *args):
        proxy = self._parent.model() #QSortFilterProxyModel

        # if the two QModelIndexes are the same
        if index1 is index2:
            pindex = proxy.mapFromSource(index1)
            proxy.dataChanged.emit(pindex, pindex, *args)
        else:
            proxy.dataChanged.emit(proxy.mapFromSource(index1),
                               proxy.mapFromSource(index2), *args)


    def emit_dataChanged(self, index1, index2):
        self._send_data_through_proxy(index1, index2)

    def emit_itemDataChanged(self, item_topleft, item_botright):

        if item_topleft is item_botright:
            iindex = self.getIndexFromItem(item_topleft)
            self._send_data_through_proxy(iindex, iindex)
        else:
            self._send_data_through_proxy(
                self.getIndexFromItem(item_topleft),
                self.getIndexFromItem(item_botright)
            )

    def queue_command(self, command):
        """
        After creating a QUndoCommand, put it our command queue for
        the stack handler to grab when it's ready
        """
        self.command_queue.append(command)

    def dequeue_command(self):
        """
        Remove and return the oldest command in the command queue
        """
        return self.command_queue.popleft()

    def item_from_row_path(self, row_path):
        """
        Given the row path (a list of ints) of an item, retrieve that
        item from the file hierarchy

        :param row_path:
        :return:
        """

        item=self.rootitem

        for r in row_path:
            # each item of row_path is a row number;
            # just follow the trail down the tree
            item = item[r]

        return item

    def item_path_from_row_path(self, row_path):
        """
        Given the row-path for an item, return a list of the nodes that
        will be traversed to get to the item

        :param list[int] row_path:
        :rtype: list[QFSItem]
        """

        item = self.rootitem

        p=[]

        for r in row_path:
            item=item[r]
            p.append(item)

        return p

    ##=============================================
    ## Saving/undoing
    ##=============================================

    def save(self):
        """
        Commit any unsaved changes (currenlty just to hidden files) to
        the db and save the updated db state to disk
        """

        # hidden files right now
        current_state = set(self.current_hidden_file_indices)

        # hidden files when last saved
        clean_state = self._saved_state

        # deltas
        to_hide = [self._files[i].path for i in sorted(current_state - clean_state)]
        to_unhide = [self._files[i].path for i in  sorted(clean_state - current_state)]

        # update database, write to disk
        self.manager.save_hidden_files(self.mod.directory, to_unhide, to_hide)

        # make the current state the saved state
        self._saved_state = current_state


class ModFileTreeModel_QUndo(ModFileTreeModel):
    """
    An extension of the ModFileTreeModel that only handles undo events;
    everything else is delegated back to the base class
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._stack = QUndoStack(self)

    @property
    def undostack(self):
        return self._stack

    @property
    def has_unsaved_changes(self):
        return not self._stack.isClean()

    def setMod(self, mod_entry):
        if mod_entry is self.mod: return

        self.save()

        self._stack.clear()

        super().setMod(mod_entry)

        # todo: show dialog box asking if the user would like to save
        # unsaved changes; have checkbox to allow 'remembering' the answer

    def setData(self, index, value, role=Qt_CheckStateRole):
        """Simply a wrapper around the base setData() that only pushes
        a qundocommand if setData would have returned True"""

        # see if the setData() command should succeed
        if super().setData(index, value, role):
            # if it does, the model should have created and queued a
            # command; try to to grab it and push it to the undostack
            try:
                self._stack.push(self.dequeue_command())
            except IndexError as e:
                print(e)
                # if there was no command in the queue...well, what happened?
                # pass

            return True
        return False

    def save(self):

        # if we have any changes to apply:
        if not self._stack.isClean():
            super().save()
            self._stack.setClean()

    def revert_changes(self):

        # revert to 'clean' state
        self._stack.setIndex(self._stack.cleanIndex())

if __name__ == '__main__':
    # noinspection PyUnresolvedReferences
    from sqlite3 import Row
