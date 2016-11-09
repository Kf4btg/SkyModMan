# from functools import partial, lru_cache
from functools import lru_cache
# from itertools import repeat
from bisect import bisect_left
from collections import deque

from PyQt5.QtCore import Qt, QModelIndex, QAbstractItemModel, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QUndoStack

from skymodman import Manager
from skymodman.log import withlogger #, tree
# from skymodman.interface.qundo import UndoCmd
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
    # noinspection PyArgumentList
    hasUnsavedChanges = pyqtSignal(bool)

    def __init__(self, parent, **kwargs):
        """

        :param parent: parent widget (specifically, the file-viewer QTreeView)
        """
        # noinspection PyArgumentList
        super().__init__(parent=parent,**kwargs)
        self._parent = parent
        self.manager = Manager() # should be initialized by now
        self.DB = self.manager.DB
        # self.rootpath = None #type: str
        self.modname = None #type: str
        self.rootitem = None #type: QFSItem

        self.mod = None
        """:type: skymodman.types.ModEntry"""

        # the mod table has this stored on the custom view,
        # but we have no custom view for the file tree, so...here it is
        # self.undostack = QUndoStack()

        # maintain a flattened list of the files for the current mod
        self._files = [] # type: list [QFSItem]

        # list of hidden files for the current 'clean state' of the tree
        # (should correspond to entries in "hiddenfiles" db table)
        self._saved_state = []

        # and a list of indices of files which are hidden
        # self._hidden = [] # type: list [int]

        self.command_queue = deque()

    # @property
    # def root_path(self):
    #     return self.rootpath

    @property
    def root_item(self):
        return self.rootitem

    # @property
    # def current_mod(self):
    #     return self.modname

    # @property
    # def has_unsaved_changes(self):
    #     return self.DB.in_transaction

    def setMod(self, mod_entry):
        """Set the mod that this model is focusing on to `mod_entry`.
        Pass ``None`` to reset the model to empty"""

        # if mod_entry is self.mod: return

        # commit any changes we've made so far
        # self.save()

        # drop the undo stack
        # self.undostack.clear()

        # and the index-cache
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

    def _setup_or_reload_tree(self):
        """
        Loads thde data from the db and disk
        """
        self._load_tree()

        # now mark hidden files
        self._mark_hidden_files()

        # this used to call resetModel() stuff, too, but I decided
        # this wasn't the place for that. It's a little barren now...

    def _load_tree(self):
        """
        Build the tree from the rootitem
        """
        # name for this item is never actually seen
        self.rootitem = QFSItem(path="", name="data", parent=None)


        QFSItem.build_filetree(self.rootitem,
                               self.mod.filetree,
                               name_filter=lambda n: n.lower() == "meta.ini")

        # build yonder tree
        # self.rootitem.build_children(self.mod.filetree, name_filter=lambda
        #             n: n.lower() == 'meta.ini')

        # create flattened list of just the files
        self._files = [f for f in
                       self.rootitem.iterchildren(recursive=True)
                       if not f.isdir]

        # for f in self._files:
        #     f.print()

        # print([str(i) for i in self._files])

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

        # if i != len(self._files) and self._files[i] == file:
        #     return i
        # raise ValueError

    def _hidden_file_indices_db(self):
        """Get the list of currently hidden files from the database
        and return a list of the indices corresponding to those files
        in self._files"""

        idxs=[]

        # the alternative to this (searching for each file by path to
        # get index) would be to do some sort of...math...or something
        # with the start/end index of the mod's entries in the database,
        # referencing position of each file returned...
        # but ehhhhhhhh, math.


        # XXX: or, uh...there might already be a better way than either of these...and I've already written it. I guess I did, anyway. Obviously I don't remember it. Anyway, down in ``item_from_path()``...

        for hf in self.DB.hidden_files(self.mod.directory):
            # NTS: As the number of hidden files approaches the total
            # number of files in the mod, this bin search algo becomes
            # less and less efficient compared to just going through
            # the loop linearly once. Might be a moot point, though,
            # as hiding the vast majority of files in a mod seems a
            # very unlikely thing to want to do.
            try:
                idxs.append(self._locate(hf))
            except ValueError:
                self.LOGGER.error("Hidden file {0!r} was not found".format(hf))

        # it's probably in order already, but just to be sure...
        return sorted(idxs)

    def _hidden_file_indices(self):
        """Rather than querying the database, this examines the current
        state of the FSItems in the internal _files list"""
        return [i for i, item in enumerate(self._files) if item.hidden]

    def _mark_hidden_files(self):

        # hfiles = list(r['filepath'] for r in self.DB.select(
        #     "filepath",
        #     FROM="hiddenfiles",
        #     WHERE="directory = ?",
        #     params=(self.mod.directory,)
        # ))

        # hfiles = list(self.DB.hidden_files(self.mod.directory))

        # locate the hidden files in the file list using binary search:
        # for hf in hfiles:
        for hf in self.DB.hidden_files(self.mod.directory):
            try:
                idx = self._locate(hf)
                # don't recurse, these should all be files;
                # also use the internal _set_checkstate to avoid the
                # parent.child_state invalidation step
                self._files[idx]._set_checkstate(Qt_Unchecked, False)
                # track indices of hidden files
                # self._hidden.append(idx)
            except ValueError:
                self.LOGGER.error("Hidden file {0!r} was not found".format(hf))

        # only files (with their full paths relative to the root of
        # the mod directory) are in the hidden files list; thus we
        # need only compare files and not dirs to the list. As usual,
        # a directory's checkstate will be derived from its children
        # for c in self.rootitem.iterchildren(True):
        #     if c.lpath in hfiles:
        #         c.checkState = Qt_Unchecked

    def getitem(self, index) -> QFSItem:
        """Extracts actual item from given index

        :param QModelIndex index:
        """
        if index.isValid():
            item = index.internalPointer()
            if item: return item
        return self.rootitem

    # def item_from_path(self, path_parts):
    #     """
    #
    #     :param path_parts: a tuple where each element is an element in
    #         the filesystem path leading from the root item to the item
    #     :return: the item
    #     """
    #     item = self.rootitem
    #     for p in path_parts:
    #         item = item[p]
    #
    #     return item

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
            # return "Name"
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
                    if item.lpath in self.DB.file_conflicts.by_mod[self.modname]:
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

            # item.checkState = value #triggers cascade if this a dir
            # last_item = item.set_checkstate(value, item.isdir)

            # first item in file's path is top-level ancestor
            # toplvl_ancestor = self.rootitem[item.row_path[0]]


            # if this item is the last checked/unchecked item in a dir,
            # make sure the change is propagated up through the parent
            # hierarchy, to make sure that no folders remain checked
            # when none of their descendants are.
            # ancestor = self._get_highest_affected_ancestor(item, value)

            # if ancestor is not item:
            #     index1 = self.getIndexFromItem(ancestor)

            # item.set_checkstate now does the work for us
            # if toplvl_ancestor is item:
            #     index1 = index
            # else:
            #     index1 = self.getIndexFromItem(toplvl_ancestor)
            #
            # if last_item is item:
            #     index2 = index
            # else:
            #     index2=self.getIndexFromItem(last_item)

            # using the "last_child_changed" value--which SHOULD be the most
            # "bottom-right" child that was just changed--to feed to
            # datachanged saves a lot of individual calls. Hopefully there
            # won't be any concurrency issues to worry about later on.

            # self._send_data_through_proxy(index1,index2)

            # update the db with which files are now hidden
            # self.update_db(index1, index2)
                           # self.getIndexFromItem(QFSItem.last_child_changed))

            return True
        return super().setData(index, value, role)

    # def _get_highest_affected_ancestor(self, item, value):
    #     """worst name for a function ever but i can't think of better"""
    #     if item.parent and item.parent.children_checkState() == value:
    #         return self._get_highest_affected_ancestor(item.parent, value)
    #     else:
    #         return item

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

        # self.hasUnsavedChanges.emit(True)

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


    # def set_as_hidden(self, file_index_list):
    #     """
    #
    #     :param file_index_list: a list of ints indicating which files
    #         in self._files should be set hidden.
    #     :return:
    #     """

    # def change_hidden_states(self, to_hide=None, to_unhide=None):
    #     """
    #     Hides or unhides the indicated files. Does no checks to see if
    #     the operation would be redundant.
    #
    #     :param list[int] to_hide: indices (from self.locate()) of
    #         files to mark as hidden
    #     :param list[int] to_unhide: indices (from self.locate()) of
    #         files to mark as not-hidden
    #     """
    #
    #     # these are all files, so there'll be no cascade as with
    #     # directories. However, we need to make sure the parent
    #     # checkstate gets properly modified
    #     _all = to_hide + to_unhide
    #
    #     # the largest index in the two lists corresponds to the "bottom-
    #     # right" item as needed by dataChanged
    #
    #     bot_right = self._files[max(_all)]
    #
    #     # top left is the top-most parent of the smallest index (first
    #     # row-number in the item's row path
    #     top_left = self._files[self._files[min(_all)].row_path[0]]
    #
    #     for i in to_hide:
    #         self._files[i].setChecked(False, False)
    #     for i in to_unhide:
    #         self._files[i].setChecked(True, False)
    #
    #
    #
    #
    #     self._send_data_through_proxy(
    #         self.getIndexFromItem(top_left),
    #         self.getIndexFromItem(bot_right)
    #     )



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
        current_state = set(self._hidden_file_indices())

        # hidden files when last saved
        clean_state = set(self._saved_state)

        # deltas
        to_hide = [self._files[i].path for i in sorted(current_state - clean_state)]
        to_unhide = [self._files[i].path for i in  sorted(clean_state - current_state)]

        # update database, write to disk
        self.manager.save_hidden_files(self.mod.directory, to_unhide, to_hide)

        # make the current state the saved state
        self._saved_state = current_state

        # if self.DB.in_transaction:
        #     self.DB.commit()
        #     self.manager.save_hidden_files()
            # self.hasUnsavedChanges.emit(False)

    # def revert_changes(self):
    #     """
    #     Undo all changes made to the tree since the last save.
    #     """
    #     self.beginResetModel()
    #
    #     #SOOOO...
    #     # will a rollback/drop-the-undostack work here?
    #     # or is individually undoing everything (a bunch of savepoint-
    #     # rollbacks) better? I guess it depends on whether we want to
    #     # be able to define a "clean" point in the middle of a
    #     # transaction...
    #
    #     self.DB.rollback()
    #     self.undostack.clear()
    #
    #     self._setup_or_reload_tree()
    #
    #     self.endResetModel()
        # self.hasUnsavedChanges.emit(False)

    # def update_db(self, start_index, final_index):
    #     """Make  changes to database.
    #     NOTE: this does not commit them! That must be done separately
    #
    #     :param start_index: index of the "top-left" affected item
    #     :param final_index: index of the "bottom-right" affected item
    #
    #
    #     """
    #     cb = partial(self._send_data_through_proxy,
    #                  start_index, final_index)
    #
    #     self.undostack.push(
    #         ChangeHiddenFilesCommand(self.rootitem,
    #                                  # os.path.basename(self.rootpath),
    #                                  self.mod.directory,
    #                                  self.DB,
    #                                  post_redo_callback=cb,
    #                                  post_undo_callback=cb
    #                                  ))
        # self.hasUnsavedChanges.emit(True)



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



# class ChangeHiddenFilesCommand(UndoCmd):
#
#
#     def __init__(self, mod_root_item, mod_dir_name, database_mgr, text="", *args,
#                  **kwargs):
#         """
#
#         :param QFSItem mod_root:
#         :param text:
#         :param args:
#         :param kwargs:
#         """
#
#         self.root_item = mod_root_item  # QFSItem
#         self.mod_dir = mod_dir_name     # str
#         self.DB = database_mgr
#
#         # these two track the actual QFSItems that were modified
#         self.checked = []
#         self.unchecked = []
#
#         # these hold just the paths (in all lowercase)
#         # XXX: should these be saved? or referenced each time we update
#         # the DB? It'll be a tradeoff between memory and performance...
#         self.tohide = []
#         self.tounhide = []
#
#         # get currently hidden files from db
#         currhidden = list(self.DB.hidden_files(self.mod_dir))
#
#         # if nothing was already hidden, we shouldn't waste time
#         # trying to figure out what to un-hide
#         self.check_unhide = len(currhidden) > 0
#
#         # analyze checkstates, fill self.checked, self.unchecked lists
#         self._get_checkstates(self.root_item)
#
#         # now filter the lists of qfsitems down to subsets:
#         # if any items were previously hidden, determine which need
#         # to be un-hidden and which can remain, as well as any newly-
#         # hidden files
#         if currhidden:
#             # filter the list of currently hidden items by those are
#             # now checked; this will need to be "un"-hidden
#             self.checked = [c for c in self.checked
#                             if c.lpath in currhidden]
#
#             # keep a record of just the paths to speed up the db-calls
#             self.tounhide = [c.lpath for c in self.checked]
#
#             # and make sure we're not trying to "re"-hide any items that
#             # are already hidden.
#             self.unchecked = [u for u in self.unchecked
#                               if u.lpath not in currhidden]
#         else:
#             # if we're here, then no items were previously hidden
#             self.tounhide = []
#             # everything unchecked should be hidden
#
#         # this is the same no matter if currhidden or not
#         self.tohide = [u.lpath for u in self.unchecked]
#
#         if self.tohide:
#             text = "Hide Files"
#         elif self.tounhide:
#             text = "Unhide Files"
#         else:
#             # this shouldn't really ever happen...but it still
#             # pops up sometimes, even when everything seems to be
#             # working ok...
#             text = "Modify Hidden Files"
#
#         # FINALLY call the super() init
#         super().__init__(text=text, *args, **kwargs)
#
#         #track the first run
#         self._first_do = True
#
#     def _redo_(self):
#         """hide the visible, reveal the hidden"""
#
#         # create a savepoint immediately before we change the db
#         self.DB.savepoint("changehidden")
#
#         if self.tounhide:
#             self.DB.remove_hidden_files(self.mod_dir, self.tounhide)
#         if self.tohide:
#             self.DB.insert(2, "hiddenfiles",
#                               params=zip(repeat(self.mod_dir),
#                                          self.tohide))
#
#         # user changed the checkstates by clicking the first time, so
#         # we only need to do it programatically each time after the first.
#         if self._first_do:
#             self._first_do = False
#         else:
#             self._modify_checkstates(False)
#
#
#     def _undo_(self):
#         """hide the hidden, visibilate the shown"""
#         # if all goes well, we should just have to rollback to the
#         # savepoint we made earlier...
#         self.DB.rollback("changehidden")
#
#         # ... and reset the checkstates
#         self._modify_checkstates(True)
#
#     def _modify_checkstates(self, undo=False):
#         """
#         After the first "do", we'll need to check/uncheck items
#         programatically. The post-[re|un]do-callback takes care of
#         emitting the datachanged signal.
#         """
#
#         for c in self.checked: #type: QFSItem
#             c.setChecked(not undo)
#             # c.checkState = _unchecked if undo else _checked
#         for u in self.unchecked:
#             u.setChecked(undo)
#             # u.checkState = _checked if undo else _unchecked
#
#
#     def _get_checkstates(self, base,
#                           unchecked=Qt.Unchecked,
#                           pchecked=Qt.PartiallyChecked):
#         """
#         examine state of tree as it appears to user and record each
#         unchecked ("hidden") item and separately (depending on the
#         value of self.check_unhide) each checked ("visible") item.
#         These are recorded in self.unchecked and self.checked,
#         respectively.
#
#         :param skymodman.interface.models.filetree.QFSItem base:
#         """
#
#         for child in base.iterchildren():
#             cs = child.checkState
#             if cs == pchecked:
#                 # this is a directory, we need to go deeper
#                 self._get_checkstates(child)
#
#             elif cs == unchecked:
#                 if child.isdir:
#                     # if we found an unchecked folder, just add
#                     # all its children
#                     self.unchecked.extend(c
#                                        for c in child.iterchildren(True)
#                                        if not c.isdir)
#                 else:
#                     self.unchecked.append(child)
#
#             elif self.check_unhide:
#                 if child.isdir:
#                     self.checked.extend(c for c
#                                          in child.iterchildren(True)
#                                          if not c.isdir)
#                 else:
#                     self.checked.append(child)

if __name__ == '__main__':
    # noinspection PyUnresolvedReferences
    from sqlite3 import Row
