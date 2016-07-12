from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QAbstractItemModel, QModelIndex, QMimeData

from skymodman import ModEntry
from skymodman.managers import modmanager as Manager
from skymodman.constants import (Column as COL, SyncError, ModError)
from skymodman.utils import withlogger
from skymodman.interface.models.undo_commands import (
    ChangeModAttributeCommand, ShiftRowsCommand, RemoveRowsCommand)

from functools import total_ordering, partial
from collections import deque
import re


# <editor-fold desc="ModuleConstants">

# VISIBLE_COLS  = [COL.ORDER, COL.ENABLED, COL.NAME, COL.MODID,
#                  COL.VERSION, COL.ERRORS]
# DBLCLICK_COLS = {COL.MODID, COL.VERSION}

# Locally binding some names to improve resolution speed in some of
# the constantly-called methods like data() (in profiling, the speedup
# was small, but noticeable, especially for large operations)
COL_ENABLED = COL.ENABLED.value
COL_NAME    = COL.NAME.value
COL_ERRORS  = COL.ERRORS.value
COL_ORDER   = COL.ORDER.value
COL_VERSION = COL.VERSION.value
COL_MODID   = COL.MODID.value

Qt_DisplayRole    = Qt.DisplayRole
Qt_CheckStateRole = Qt.CheckStateRole
Qt_EditRole       = Qt.EditRole
Qt_ToolTipRole    = Qt.ToolTipRole
Qt_DecorationRole = Qt.DecorationRole

Qt_Checked   = Qt.Checked
Qt_Unchecked = Qt.Unchecked

Qt_ItemIsSelectable    = Qt.ItemIsSelectable
Qt_ItemIsEnabled       = Qt.ItemIsEnabled
Qt_ItemIsEditable      = Qt.ItemIsEditable
Qt_ItemIsUserCheckable = Qt.ItemIsUserCheckable
Qt_ItemIsDragEnabled   = Qt.ItemIsDragEnabled
Qt_ItemIsDropEnabled   = Qt.ItemIsDropEnabled

col2field = {
    COL_ORDER:     "ordinal",
    COL_ENABLED:   "enabled",
    COL_NAME:      "name",
    COL.DIRECTORY: "directory",
    COL_MODID:     "modid",
    COL_VERSION:   "version",
}

col2Header={
    COL.ORDER:     "#",
    COL.ENABLED:   " ",
    COL.NAME:      "Name",
    COL.DIRECTORY: "Folder",
    COL.MODID:     "Mod ID",
    COL.VERSION:   "Version",
    COL.ERRORS:    "Errors",
}
# </editor-fold>

@total_ordering
class QModEntry(ModEntry):
    """
    Namedtuple subclass that eases accessing derived properties for displaying in the Qt GUI
    """
    # from the python docs: [Set] __slots__ to an empty tuple. This
    # helps keep memory requirements low by preventing the creation of
    # instance dictionaries.
    __slots__=("errors", )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.errors = SyncError.NONE

    @property
    def checkState(self):
        return Qt_Checked if self.enabled else Qt_Unchecked

    def __lt__(self, other):
        return self.ordinal < other.ordinal #ordinal is unique, but not constant
    def __gt__(self, other):
        return self.ordinal > other.ordinal


    def __eq__(self, other):
        """This is for checking if two mods are are equal with regards
        to their **editable** fields"""
        return self.name == other.name \
               and self.enabled == other.enabled \
               and self.ordinal == other.ordinal


@withlogger
class ModTable_TreeModel(QAbstractItemModel):

    tablehaschanges = pyqtSignal(bool)
    # undoevent = pyqtSignal(str, str) # undotext, redotext

    # let view know selection may have moved
    notifyViewRowsMoved = pyqtSignal()

    hideErrorColumn = pyqtSignal(bool)

    def __init__(self, parent, **kwargs):
        """
        """
        super().__init__(**kwargs)
        self._parent = parent

        # noinspection PyUnresolvedReferences
        self.mod_entries = [] #type: list[QModEntry]

        # noinspection PyUnresolvedReferences
        self.errors = {}  # type: dict[str, int]
                          #  of {mod_directory_name: err_type}
        # keep a reference to the keys() dictview (which will
        # dynamically update itself)
        self.missing_mods = self.errors.keys()

        self.vheader_field = COL_ORDER

        # track the row numbers of every mod in the table that is
        # changed in any way. Every time a change is made, the row
        # number is appended to the end of the deque, even if it
        # is already present. Allowing duplicates in this way lets
        # an undo() remove the most recent changes without losing
        # track of any previous changes made to that row.

        # More importantly, this allows us to directly specify precisely
        # which mods need to be updated in the DB when the user issues
        # a save command, rather than updating every entry in the table
        # each time. This can safe a lot of cycles when only 1 or 2
        # entries have been modified
        self._modifications = deque()

        self.LOGGER << "init ModTable_TreeModel"

    ##===============================================
    ## PROPERTIES
    ##===============================================

    @property
    def isDirty(self) -> bool:
        return len(self._modifications) > 0

    def __getitem__(self, row):
        """
        Allows list-like access to the backing collection of ModEntries.

        :param int row: Row number of the mod from the mod table
        :return: QModEntry instance representing the mod in that row. If `row` is out of bounds or cannot be implicitly converted to an int, return None.
        """
        try:
            return self.mod_entries[row]
        except (TypeError, IndexError):
            return None

    def getModForIndex(self, index):
        """
        Return the ModEntry for the row in which `index` appears.

        :param QModelIndex index:
        :return:
        """
        if index.isValid(): return self.mod_entries[index.row()]

    def mod_missing(self, mod_entry):
        """
        Return whether the specified mod is currently in an error state.

        :param QModEntry mod_entry:
        :return:
        """
        return mod_entry.directory in self.missing_mods

    def mark_modified(self, iterable):
        """
        Add the items from `iterable` to the collection of modified rows.

        :param iterable: an iterable collection of ints. The values must
            all be valid indices in the model's list of mods
        """
        self._modifications.extend(iterable)

    def unmark_modified(self, count):
        """
        Remove the `count` most recent additions to the modifications
        collection

        :param int count:
        :return:
        """
        for _ in range(count):
            self._modifications.pop()

    def _push_command(self, command):
        """
        Push a QUndoCommand to the parent's undo_stack
        :param command:
        """
        self._parent.undo_stack.push(command)

    ##===============================================
    ## Required Qt Abstract Method Overrides
    ##===============================================

    def rowCount(self, *args, **kwargs) -> int:
        return len(self.mod_entries)

    def columnCount(self, *args, **kwargs) -> int:
        return len(col2Header)

    def parent(self, child_index=None):
        # There are no children (yet...) so I guess this should always return invalid??
        return QModelIndex()

    def index(self, row, col=0, parent=QModelIndex(), *args,
              **kwargs) -> QModelIndex:
        """
        :param int row:
        :param int col:
        :param QModelIndex parent:
        :return: the QModelIndex that represents the item at (row, col) with respect
                 to the given  parent index. (or the root index if parent is invalid)
        """

        # This never happens:
        # if parent.isValid() and parent.column() != 0:
        #     self.logger << "parent is valid: {}".format(parent.data())
        #     return QModelIndex()

        try:
            child = self.mod_entries[row]
            return self.createIndex(row, col, child)
        except IndexError:
            return QModelIndex()


    ## Data Provider
    ##===============================================
    # noinspection PyArgumentList
    def data(self, index, role=Qt_DisplayRole):
        col = index.column()

        # handle errors first
        if col == COL_ERRORS:
            try:
                err = self.errors[self.mod_entries[index.row()].directory]
                for case, choices in [(lambda r: role == r,
                                       lambda d: d[err])]:

                    if case(Qt_DecorationRole): return QtGui.QIcon.fromTheme(
                            choices({SyncError.NOTFOUND:
                                         'dialog-error',
                                     SyncError.NOTLISTED:
                                         'dialog-warning'}))

                    if case(Qt_ToolTipRole): return choices(
                            {SyncError.NOTFOUND:
                                 "Mod data not found.",
                             SyncError.NOTLISTED:
                                 "This mod was found in the mods "
                                 "directory but has not previously "
                                 "been seen my this profile. Be sure "
                                 "that it is either set up correctly "
                                 "or disabled before running any tools."
                             })
            except KeyError:
                # no errors for this mod
                return

        elif col == COL_ENABLED:
            if role == Qt_CheckStateRole:
                return self.mod_entries[index.row()].checkState

        # just display the row number here;
        # this allows us to manipulate the ordinal number a bit more
        # freely behind the scenes
        elif col == COL_ORDER:
            if role == Qt_DisplayRole:
                return index.row() + 1

        else:
            # if col == COL_ORDER and role == Qt_DisplayRole:
            #     m = self.mod_entries[index.row()]
            #     print("col_order,", m.name, ":", getattr(m, col2field[col]))
            # for every other column, return the stored value as the
            # display role
            if role==Qt_DisplayRole:
                return getattr(self.mod_entries[index.row()], col2field[col])
            if col == COL_NAME:
                if role == Qt_EditRole:
                    return self.mod_entries[index.row()].name
                if role == Qt_ToolTipRole:
                    return self.mod_entries[index.row()].directory

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """

        :param section:
        :param orientation:
        :param role:
        :return: column header for the specified section (column) number.
        """
        if role == Qt.DisplayRole:

            if orientation == Qt.Horizontal:
                return col2Header[section]

            else:  # vertical header
                return self.mod_entries[section].ordinal

        return super().headerData(section, orientation, role)

    def flags(self, index):
        """
        For the cell specified by `index`, return the appropriate
        flag value:

            * Invalid Index: enabled
            * 'Enabled' column: enabled, selectable, draggable,
              droppable, checkable
            * 'Name' column: enabled, selectable, draggable, droppable,
              editable
            * Any other column: enabled, selectable, draggable,
              droppable

        :param QModelIndex index:
        """
        if not index.isValid():
            return Qt_ItemIsEnabled
        col = index.column()

        _flags = Qt_ItemIsEnabled | Qt_ItemIsSelectable | \
                 Qt_ItemIsDragEnabled | Qt_ItemIsDropEnabled

        if col == COL_ENABLED:
            return _flags | Qt_ItemIsUserCheckable

        if col == COL_NAME:
            return _flags | Qt_ItemIsEditable

        return _flags

    def search(self, text, start_index, direction=1) -> QModelIndex:
        """
        Search for the given text in the mod list (names, by default),
        and return the model index of the first or next matching entry.

        :param str text: search text
        :param QModelIndex start_index: the currently selected index;
            search will begin here and search down the table
        :param int direction: if negative, search backwards from
            current location
        :return: QModelIndex
        """
        # an invalid index will have row==-1
        current_row = start_index.row()

        reverse = direction < 0

        # Wildcard matching:
        #replace any '*' and '?' with '.*' and '.', respectively,
        # but maintain any '.' (or other re metachars) in the text as
        # literal chars
        regex = re.sub(r'\\\?', '.',
                       re.sub(r'\\\*', '.*',
                            re.escape(text))
                       )

        regex = re.compile(regex, re.IGNORECASE)

        def findstr(modentry):
            return regex.search(modentry.name)

        searcher = partial(self._search_slice, findstr)

        try:
            # search backwards if dir<0
            next_result = searcher(
                    start=current_row-1, step=-1) \
                        if reverse else searcher(
                    start=current_row+1)

        except StopIteration:
            # we've reached one end of the list, so wrap search
            # to the opposite end and continue until we either find a
            # match or return to the starting point.
            try:
                next_result = searcher(end=current_row-1, step=-1) \
                              if reverse \
                              else searcher(end=current_row + 1)
            except StopIteration:
                return QModelIndex()

        if next_result:
            return self.createIndex(next_result.ordinal-1, COL_NAME)

        # i don't think we'll ever reach here...
        # but better safe than sorry, I guess
        self.LOGGER << "<--End of mod table search"
        return QModelIndex()

    def _search_slice(self, match_func, start=None, end=None, step=1):
        if start is None:
            if end is None:
                return next(filter(match_func, self.mod_entries[::step]))
            return next(filter(match_func, self.mod_entries[:end:step]))
        elif end is None:
            return next(filter(match_func, self.mod_entries[start::step]))
        return next(filter(match_func, self.mod_entries[start:end:step]))

    ##===============================================
    ## Setting Data
    ##===============================================

    def setData(self, index, value, role=None):
        """
        Currently, the only editable fields are the enabled column
        (checkbox) and the name field (lineedit)

        :param QModelIndex index:
        :param value:
        :param role:
        :return:
        """

        if role == Qt_CheckStateRole:
            if index.column() == COL_ENABLED:
                row = index.row()

                # callbacks for updating (1) or reverting (2)
                cb1 = partial(self._post_change_mod_attr, index, row)
                cb2 = partial(self._post_change_mod_attr, index)

                self._push_command(ChangeModAttributeCommand(
                    self.mod_entries[row],
                    "enabled",
                    int(value == Qt_Checked),
                    post_redo_callback = cb1,
                    post_undo_callback = cb2)
                )

                return True
        elif role == Qt_EditRole:
            if index.column() == COL_NAME:
                row = index.row()
                mod = self.mod_entries[row]
                new_name = value.strip()  # remove trailing/leading space
                if new_name in [mod.name, ""]: return False

                # callbacks for changing (1) or reverting (2)
                cb1 = partial(self._post_change_mod_attr, index, row)
                cb2 = partial(self._post_change_mod_attr, index)
                self._push_command(ChangeModAttributeCommand(
                    mod, "name", new_name,
                    post_redo_callback = cb1,
                    post_undo_callback = cb2)
                )

                return True
        else:
            return super().setData(index, value, role)

        # if role was checkstate or edit, but column was not
        # enabled/name, just ret false
        return False

    def _post_change_mod_attr(self, index, row=-1):
        """
        For use as a callback after updating (+ redo/undo) a
        mod attribute. Args will need to be filled in w/ partial()
        """

        # having row == -1 signifies that this is an UNDO operation,
        # so we should just pop the end off the modification deque
        if row < 0:
            # remove this row number from the modified rows stack
            self._modifications.pop()
        else:
            self._modifications.append(row)
        self.dataChanged.emit(index, index)

    ##===============================================
    ## Modifying Row Position
    ##===============================================

    def shiftRows(self, start_row, end_row, move_to_row, parent=QModelIndex(), undotext="Reorder Mods"):
        """
        :param int start_row: start of shifted block
        :param int end_row: end of shifted block
        :param int move_to_row: destination row; where the
            `start_row` should end up
        :param QModelIndex parent:
        :param str undotext: optional text that will appear in
            the Undo/Redo menu items
        """
        # create a new shift-command

        scmd = ShiftRowsCommand(
            self, start_row, end_row, move_to_row,
            text=undotext,
            post_redo_callback=self.notifyViewRowsMoved.emit,
            post_undo_callback=self.notifyViewRowsMoved.emit
        )

        # get the shifter object from the command
        shifter = scmd.shifter
        # and use it to build the beginMoveRows args
        scmd.pre_redo_callback = partial(
            self.beginMoveRows, parent,
            start_row,
            end_row,
            parent,
            shifter.block_dest())

        # get the values for the reverse operation
        scmd.pre_undo_callback = partial(
            self.beginMoveRows, parent,
            shifter.block_start(True),
            shifter.block_end(True),
            parent,
            shifter.block_dest(True)
        )

        # push to the undo stack
        self._push_command(scmd)

    ##===============================================
    ## Getting data from disk into model
    ##===============================================

    def loadData(self):
        """
        Load fresh data and reset everything. Called when first loaded
        and when something major changes, like the active profile.
        """
        self.beginResetModel()
        self._modifications.clear()

        self.mod_entries = [QModEntry(**d) for d
                            in Manager.basic_mod_info()]

        self.checkForModLoadErrors()

        self.endResetModel()
        self.tablehaschanges.emit(False)

    def checkForModLoadErrors(self):
        """
        query the manager for any errors that were encountered while
        loading the modlist for the current profile. The two error
        types are:

            * SyncError.NOTFOUND: Mod listed in the profile's saved
              list is not present on disk
            * SyncError.NOTLISTED: Mod found on disk is not in the
              profile's modlist

        The model's ``errors`` property (a str=>int dictionary) is
        populated with the results of this query; each key in the dict
        is the name of a mod (directory), and the value is the int-enum
        value of the type of error it encountered. If a mod is not
        present in this collection, then no error was encountered.

        Ideally, ``errors`` will be empty after this method is called.
        In this case, the model will notify the view to hide the Errors
        column of the table. If ``errors`` is not empty, then the Errors
        column will be shown and an icon indicating the type of error
        will be appear there in the row(s) of the problematic mod(s).
        """
        # self.errors = {}  # type: dict[str, int]
        # reset
        self.errors.clear()
        for err_mod in Manager.get_errors(SyncError.NOTFOUND): # type: str
            self.errors[err_mod] = SyncError.NOTFOUND

        for err_mod in Manager.get_errors(SyncError.NOTLISTED): # type: str
            self.errors[err_mod] = SyncError.NOTLISTED

        # only show error column when they are errors to report
        if self.errors:
            self.logger << "show error column"
            self.hideErrorColumn.emit(False)
        else:
            self.logger << "hide error column"
            self.hideErrorColumn.emit(True)

    def reloadErrorsOnly(self):
        self.beginResetModel()
        self.checkForModLoadErrors()
        self.endResetModel()

    ##===============================================
    ## Save & Revert
    ##===============================================

    def save(self):
        to_save = [self.mod_entries[row]
                   for row in set(self._modifications)]

        Manager.save_user_edits(to_save)

    def clear_missing(self):
        """
        Remove all mods that are marked with the NOT FOUND error
        from the current profile's modlist

        :return:
        """

        ## options here:
        # 1) find each row that contains an errored mod and call
        # RemoveRows on it. could be sped up by finding ranges.
        # Will need to emit dataChanged and possibly shift stuff
        # around.
        # 2) just remove them from the mod_entries list and reset the
        # model.
        # ...
        # 2 is much simpler. And if they user is doing this, there's
        # likely a lot of things to remove.

        self.beginResetModel()
        #
        # for m in self.mod_entries:
        #     try:
        #         if self.errors[m.directory] == SyncError.NOTFOUND:




    ##===============================================
    ## Drag & Drop
    ##===============================================

    def supportedDropActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        """We just draggin text around"""
        return ['text/plain']

    def mimeData(self, indexes):
        """

        :param list[QModelIndex] indexes:
        :return: A string that is 2 ints separated by whitespace, e.g.:  '4 8' This string corresponds to the first and last row in the block of rows being dragged.
        """
        rows = sorted(set(i.row() for i in indexes))
        mimedata = QMimeData()
        mimedata.setText("{} {}".format(rows[0], rows[-1]))
        return mimedata

    def dropMimeData(self, data, action, row, column, parent):
        """

        :param QMimeData data: contains a string that is 2 ints separated by whitespace, e.g.:  '4 8' This string corresponds to the first and last row in the block of rows being dragged
        :param Qt.DropAction action:
        :param int row:
        :param int column:
        :param QModelIndex parent:
        :return:
        """

        if not parent.isValid():
            return False
        p = parent.internalPointer() #type: QModEntry

        # drop above the hovered item
        dest = p.ordinal - 1
        start, end = [int(r) for r in data.text().split()]

        self.shiftRows(start, end, dest)
        return True

    ##===============================================
    ## Adding and Removing Rows/Columns (may need later)
    ##===============================================

    def removeRows(self, row, count, parent=QModelIndex(), *args, **kwargs):
        """
        Remove mod[s] (row[s]) from the model. Undoable action

        :param int row:
        :param int count:
        :param QModelIndex parent:
        :return:
        """

        end = row+count-1

        self._push_command(
            RemoveRowsCommand(
                self, row, end,
                pre_redo_callback  = partial(self.beginRemoveRows,
                                             parent, row, end),
                post_redo_callback = self.endRemoveRows,
                pre_undo_callback  = partial(self.beginInsertRows,
                                             parent, row, end),
                post_undo_callback = self.endInsertRows
            )
        )

        return True
    #
    #
    # def insertRows(self, row, count, parent = QModelIndex()):
    #     """
    #
    #     :param row:
    #     :param count:
    #     :param parent:
    #     :return:
    #     """
    #     me = self.mod_entries
    #
    #     self.beginInsertRows(parent, row, row+count-1)
    #     # left = self.mod_entries[:row]
    #     right = me[row:]
    #     me = me[:row]
    #
    #     me.extend([None]*count)
    #     me+=right
    #
    #     self.endInsertRows()

