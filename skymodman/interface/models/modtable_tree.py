from PyQt5 import QtCore, QtGui
# from PyQt5.QtWidgets import QHeaderView, QTreeView, QAbstractItemView, QMenu, QAction
from PyQt5.QtCore import Qt, pyqtSignal, QAbstractItemModel, QModelIndex, QMimeData

from skymodman import ModEntry
from skymodman.managers import modmanager as Manager
from skymodman.constants import (Column as COL, SyncError)
# , DBLCLICK_COLS, VISIBLE_COLS)
# from skymodman.constants import SyncError
from skymodman.utils import withlogger
from skymodman.thirdparty.undo import undoable #, group #,stack
# from skymodman.utils.timedundo import groupundoable, stack, _undoable
from skymodman.utils.timedundo import stack

from functools import total_ordering, partial
from collections import deque
import re


# <editor-fold desc="ModuleConstants">

# HEADERS =   ["Order", "", "Name", "Folder", "Mod ID", "Version", "Errors"]
# COLUMNS = {COL.ORDER, COL.ENABLED, COL.NAME, COL.DIRECTORY, COL.MODID, COL.VERSION, COL.ERRORS}
VISIBLE_COLS  = [COL.ORDER, COL.ENABLED, COL.NAME, COL.MODID, COL.VERSION, COL.ERRORS]
DBLCLICK_COLS = {COL.MODID, COL.VERSION}

# Locally binding some names to improve resolution speed in some of the constantly-called methods like data()
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
    COL_ORDER: "ordinal",
    COL_ENABLED: "enabled",
    COL_NAME: "name",
    COL.DIRECTORY: "directory",
    COL_MODID: "modid",
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
    # from the python docs: [Set] __slots__ to an empty tuple. This helps keep memory requirements low by preventing the creation of instance dictionaries.
    __slots__=()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def checkState(self):
        return Qt_Checked if self.enabled else Qt_Unchecked

    def __lt__(self, other):
        return self.ordinal < other.ordinal #ordinal is unique, but not constant
    def __gt__(self, other):
        return self.ordinal > other.ordinal


    def __eq__(self, other):
        """This is for checking if two mods are are equal with regards to their **editable** fields"""
        return self.name == other.name \
               and self.enabled == other.enabled \
               and self.ordinal == other.ordinal


@withlogger
class ModTable_TreeModel(QAbstractItemModel):

    tablehaschanges = pyqtSignal(bool)
    undoevent = pyqtSignal(str, str) # undotext, redotext
    notifyViewRowsMoved = pyqtSignal() # let view know selection may have moved
    hideErrorColumn = pyqtSignal(bool)

    def __init__(self, parent, **kwargs):
        """
        """
        super().__init__(**kwargs)
        self._parent = parent
        # self.manager = manager

        # noinspection PyUnresolvedReferences
        self.mod_entries = [] #type: list[QModEntry]

        self.errors = {}  # dict[str, int] of {mod_directory_name: err_type}

        self.vheader_field = COL_ORDER
        # self.visible_columns = [COL.ENABLED, COL.ORDER, COL.NAME, COL.MODID, COL.VERSION]

        self._datahaschanged = None # placeholder for first start

        # track the row numbers of every mod in the table that is changed in any way.
        # Every time a change is made, the row number is appended to the end of the deque,
        # even if it is already present. Allowing duplicates in this way lets an undo()
        # remove the most recent changes without losing track of any previous changes
        # made to that row.
        self._modifications = deque()

        # used to store removed rows during DnD operations
        # edit: no it's not
        # self.removed = []

        stack().undocallback = partial(self._undo_event, 'undo')
        stack().docallback = partial(self._undo_event, 'redo')

        self.LOGGER << "init ModTable_TreeModel"

    ##===============================================
    ## PROPERTIES
    ##===============================================

    @property
    def isDirty(self) -> bool:
        return stack().haschanged()

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

    ##===============================================
    ## Undo/Redo
    ##===============================================
    @property
    def stack(self):
        return stack()
    @property
    def undotext(self):
        return stack().undotext()
    @property
    def redotext(self):
        return stack().redotext()
    @property
    def canundo(self):
        return stack().canundo()
    @property
    def canredo(self):
        return stack().canredo()

    # FIXME: on the FIRST undoable action (when there are no undos available), the timed stack implementation doesn't react to the undo key sequence until the timer runs out; this is because the the Undo QAction is disabled until something is in the **real** undo stack. The non-responsive shortcut is rather jarring. Later, when there are already undos in the stack, the undo command interrupts the timer as it's supposed to.
    def undo(self):
        stack().undo()

    def redo(self):
        stack().redo()

    def _undo_event(self, action=None):
        """
        Passed to the undo stack as ``undocallback``, so that we can notify the UI of the new text
        :param action:
        """
        if action is None:  # Reset
            self.tablehaschanges.emit(False)
            self.undoevent.emit(None, None)
        else:
            self._check_dirty_status()
            self.undoevent.emit(stack().undotext(),
                                stack().redotext())

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
                for case, choices in [(lambda r: role == r, lambda d: d[err])]:

                    if case(Qt_DecorationRole): return QtGui.QIcon.fromTheme(
                            choices({SyncError.NOTFOUND: 'dialog-error',
                                     SyncError.NOTLISTED: 'dialog-warning'}))

                    if case(Qt_ToolTipRole): return choices(
                            {SyncError.NOTFOUND: "The data for this mod was not found"
                                                 "in the currently configured mod directory."
                                                 "Have the files been moved? The mod"
                                                 "cannot be loaded if it cannot be found!",
                             SyncError.NOTLISTED: "This mod was found in the mods directory"
                                                  "but has not previously been seen my this"
                                                  "profile. Be sure that it is either set up"
                                                  "correctly or disabled before running any tools."
                             })
            except KeyError:
                # no errors for this mod
                return

        elif col == COL_ENABLED:
            if role == Qt_CheckStateRole:
                return self.mod_entries[index.row()].checkState

        else:
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
        if not index.isValid():
            return Qt_ItemIsEnabled
        col = index.column()

        _flags = Qt_ItemIsEnabled | Qt_ItemIsSelectable | Qt_ItemIsDragEnabled | Qt_ItemIsDropEnabled

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
        :param QModelIndex start_index: the currently selected index; search will begin here and search down the table
        :return: QModelIndex
        """
        # an invalid index will have row==-1
        current_row = start_index.row()

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
                        if direction<0 else searcher(
                    start=current_row+1)

        except StopIteration:
            try:
                next_result = searcher(
                        end=current_row-1, step=-1) \
                    if direction < 0 else searcher(
                        end=current_row + 1)
            except StopIteration:
                return QModelIndex()

        if next_result:
            return self.createIndex(next_result.ordinal-1, COL_NAME)

        # i don't think we'll ever reach here...
        # but better safe than sorry, I guess
        self.LOGGER << "--End of mod table search"
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
        Currently, the only editable fields are the enabled column (checkbox) and the name field (lineedit)

        :param index:
        :param value:
        :param role:
        :return:
        """

        if role == Qt_CheckStateRole:
            if index.column() == COL_ENABLED:
                row = index.row()
                self.changeModField(index, row, self.mod_entries[row],
                                    'enabled', int(value == Qt_Checked))
                return True
        elif role == Qt_EditRole:
            if index.column() == COL_NAME:
                row = index.row()
                mod = self.mod_entries[row]
                new_name = value.strip()  # remove trailing/leading space
                if new_name in [mod.name, ""]: return False

                self.changeModField(index, row, mod, 'name', new_name)
                return True
        else:
            return super().setData(index, value, role)

        return False # if role was checkstate or edit, but column was not enabled/name, just ret false

    # noinspection PyUnresolvedReferences
    @undoable
    def changeModField(self, index, row, mod, field, value):
        # this is for changing a mod attribute *other* than ordinal
        # (i.e. do not use this when the mod's install order is being changed)

        #do/redo code:
        old_value = getattr(mod, field)
        setattr(mod, field, value)

        # record this row numnber in the modified rows stack
        self._modifications.append(row)

        self.dataChanged.emit(index, index)

        yield "Change {}".format(field)

        # undo code:
        setattr(mod,field, old_value)
        # remove this row number from the modified rows stack
        self._modifications.pop()

        self.dataChanged.emit(index, index)

    ##===============================================
    ## Modifying Row Position
    ##===============================================

    # let's try it a smarter way
    @undoable
    def shiftRows(self, start_row, end_row, move_to_row, parent=QModelIndex(), undotext="Reorder Mods"):
        """
        :param int start_row: start of shifted block
        :param int end_row: end of shifted block
        :param int move_to_row: destination row; where the `start_row` should end up
        :param QModelIndex parent:
        :param str undotext: optional text that will appear in the Undo/Redo menu items
        :return:
        """
        # self.LOGGER << "Moving rows {}-{} to row {}.".format(start_row, end_row, move_to_row)

        count       = 1 + end_row - start_row
        d_shift     = move_to_row - start_row      # shift distance; could be +-
        rvector     = -(d_shift//abs(d_shift))      # get inverse normal vector; this will be +1 for up, -1 for down (see below)

        _end_offset = 0 # need this later
        if move_to_row < start_row: # If we're moving UP:
            slice_start = dest_child = move_to_row  # get a slice from smallest index
            slice_end   = 1 + end_row    # ... to the end of the rows to displace
        else: # if we're moving DOWN:
            slice_start = start_row
            # slice_end   = dest_child = min(move_to_row + count, self.rowCount()) # don't go past last row

            slice_end   = move_to_row + count
            # we want to make sure we don't try to move past the end;
            # if we would, change the slice end to the max row number,
            # but save the amount we would have gone over for later reference
            _end_offset = max(0, slice_end - self.rowCount())
            if _end_offset > 0:
                slice_end -= _end_offset
            dest_child = slice_end


        # notes:
        # if we're moving DOWN:
        #   * the ordinal is increasing,
        #   * slice_start==start_row,
        #   * slice_end==move_to_row + count
        #
        # If we're moving UP:
        #   * ordinal is decreasing
        #   * slice_start == move_to_row
        #   * slice_end == end_row + 1

        # Qt expects the final argument of beginMoveRows to be the index in the model
        # before which THE ENTIRE BLOCK of moved rows will be placed.
        # For example, if our block contains three items, rows 3-5, and we want to
        # move the block such that row 3 will be at index 7--followed by row 4 at 8, and
        # row 5 at 9--our destination index (i.e. the final arg to beginMoveRows) will
        # actually be **10**, since 10 is the index immediately after the final item
        # of our moved block.
        # An easy way to calculate this is that, WHEN MOVING DOWN, the destination index is
        # equal to the target row (the target of the first moved row, that is) + the number
        # of items being moved. So, for our example above:
        #       >>> 7+3=10.
        # Moving up is simpler: the destination row and the target row are the same.

        self.beginMoveRows(parent, start_row, end_row, parent, dest_child)

        self._doshift(slice_start, slice_end, count, rvector)

        self.endMoveRows()

        # track all modified rows
        self._modifications.extend(range(slice_start, slice_end))
        self.notifyViewRowsMoved.emit()

        yield undotext

        # for the reverse beginMoveRows call, we know that what was `start_row` is now in `move_to_row`;
        # and the end_row is 'count'-1 rows beyond that; but an easier way to end_row is probably:
        #     start = move_to_row    (same as 'start_row+d_shift')
        #     end = end_row + d_shift
        # since 'd_shift' is either + or - based on the original movement
        # the dest index we can get by selecting the other possibility from the one we made above:
        #     dchild2 = slice_end if move_to_row < start_row else slice_start

        # here's where we use that offset we saved; have to subtract it from both start and
        # end to make sure we're referencing the right block of rows when calling beginMoveRows
        self.beginMoveRows(parent,
                      move_to_row - _end_offset,
                      end_row + d_shift - _end_offset, parent,
                      slice_end if move_to_row < start_row else slice_start)
        # print("undo: %d-%d -> %d" % (start_row + d_shift - _end_offset,
        #                              end_row + d_shift - _end_offset,
        #                              slice_end if move_to_row < start_row else slice_start))

        # the internal undo just involves rotating in the opposite direction
        self._doshift(slice_start, slice_end, count, -rvector)

        self.endMoveRows()

        # remove all de-modified row numbers
        for _ in range(slice_end-slice_start):
            self._modifications.pop()
        self.notifyViewRowsMoved.emit()

    def _doshift(self, slice_start, slice_end, count, uvector):
        # self.LOGGER << "Rotating [{}:{}] by {}.".format(
        #     slice_start, slice_end, count*uvector)

        # copy the slice for reference afterwards
        # s_copy = self.mod_entries[slice_start:slice_end]
        me = self.mod_entries

        # now copy the slice into a deque;
        deck = deque(me[slice_start:slice_end]) #type: deque[QModEntry]

        # rotate the deck in the opposite direction and voila its like we shifted everything.
        deck.rotate(count * uvector)
        # pop em back in, replacing the ordinal to reflect the mod's new position
        for i in range(slice_start, slice_end):
            me[i]=deck.popleft()
            me[i].ordinal = i+1

    def _check_dirty_status(self):
        """
        Checks whether the table has just gone from a saved to an unsaved state, or vice-versa, and sends a notification signal iff there is a state change.
        """
        if self._datahaschanged is None or stack().haschanged() != self._datahaschanged:
            # if _datahaschanged is None, then this is the first time we've changed data this session.
            # Otherwise, we only want to activate when there is a difference between the current and cached state
            self._datahaschanged = stack().haschanged()
            self.tablehaschanges.emit(self._datahaschanged)

    ##===============================================
    ## Getting data from disk into model
    ##===============================================

    def loadData(self):
        """
        Load fresh data and reset everything. Called when first loaded and when something major changes, like the active profile.
        """
        self.beginResetModel()
        self._modifications.clear()
        self._datahaschanged = None
        stack().clear()
        stack().savepoint()

        self.mod_entries = [QModEntry(**d) for d in Manager.basic_mod_info()]

        self.getErrors()

        self.endResetModel()
        self.tablehaschanges.emit(False)

    def getErrors(self):
        self.errors = {}  # reset
        for err in Manager.get_errors(SyncError.NOTFOUND):
            self.errors[err] = SyncError.NOTFOUND

        for err in Manager.get_errors(SyncError.NOTLISTED):
            self.errors[err] = SyncError.NOTLISTED

        # only show error column when they are errors to report
        if self.errors:
            self.logger << "show error column"
            self.hideErrorColumn.emit(False)
        else:
            self.logger << "hide error column"
            self.hideErrorColumn.emit(True)

    def reloadErrorsOnly(self):
        self.beginResetModel()
        self.getErrors()
        self.endResetModel()

    ##===============================================
    ## Save and Revert
    ##===============================================

    def save(self):
        to_save = [self.mod_entries[row] for row in set(self._modifications)]

        Manager.save_user_edits(to_save)

        # for now, let's just reset the undo stack and consider this the new "start" point
        stack().clear()
        self._datahaschanged = None
        stack().savepoint()

        self._undo_event()

    def revert(self):
        self.beginResetModel()
        # self.LOGGER << self.signalsBlocked()
        self.blockSignals(True)
        while stack().canundo():
            # todo: this doesn't block signals...should it?
            stack().undo()

        self.blockSignals(False)
        self.endResetModel()

    ##===============================================
    ## Adding and Removing Rows/Columns
    ##===============================================

    def supportedDropActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        """We just drag text around"""
        return ['text/plain']

    def mimeData(self, indexes):
        """

        :param list[QModelIndex] indexes:
        :return: A string that is 2 ints separated by spaces, e.g.:  '4 8'
            This string corresponds to the first and last row in the block of rows being dragged.
        """
        rows = sorted(set(i.row() for i in indexes))
        mimedata = QMimeData()
        mimedata.setText("{} {}".format(rows[0], rows[-1]))
        return mimedata

    def dropMimeData(self, data, action, row, column, parent):
        """

        :param QMimeData data:
        :param Qt.DropAction action:
        :param int row:
        :param int column:
        :param QModelIndex parent:
        :return:
        """

        if not parent.isValid():
            return False
        p = parent.internalPointer() #type: QModEntry

        dest = p.ordinal - 1
        start, end = [int(r) for r in data.text().split()]

        self.shiftRows(start, end, dest)
        # self.logger << "dropMimeData '{}' a{} r{} c{} p{}".format(data.text(), action, row, column, p )
        return True

    # def removeRows(self, row, count, parent=QModelIndex()):
    #     """
    #
    #     :param int row:
    #     :param int count:
    #     :param QModelIndex parent:
    #     :return:
    #     """
    #
    #     self.beginRemoveRows(parent, row, row + count - 1)
    #
    #     self.removed = self.mod_entries[row:row+count]
    #     self.mod_entries[row:row+count] = []
    #
    #     self.endRemoveRows()
    #     return True
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

