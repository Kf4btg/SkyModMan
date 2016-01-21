from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QHeaderView, QTreeView, QAbstractItemView
from PyQt5.QtCore import Qt, pyqtSignal, QItemSelection, QAbstractItemModel, QModelIndex

from skymodman import ModEntry
# from skymodman.constants import (Column as COL, SyncError, DBLCLICK_COLS, VISIBLE_COLS)
from skymodman.constants import SyncError
from skymodman.utils import withlogger
from skymodman.thirdparty.undo import undoable, stack

from enum import IntEnum
from functools import total_ordering, partial
from collections import  deque

class COL(IntEnum):
    ENABLED, ORDER, NAME, DIRECTORY, MODID, VERSION, ERRORS = range(7)

col2field = {
    COL.ORDER: "ordinal",
    COL.ENABLED: "enabled",
    COL.NAME: "name",
    COL.DIRECTORY: "directory",
    COL.MODID: "modid",
    COL.VERSION:   "version",
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

# HEADERS =   ["Order", "", "Name", "Folder", "Mod ID", "Version", "Errors"]
# COLUMNS = {COL.ORDER, COL.ENABLED, COL.NAME, COL.DIRECTORY, COL.MODID, COL.VERSION, COL.ERRORS}
VISIBLE_COLS = [COL.ORDER, COL.ENABLED, COL.NAME, COL.MODID, COL.VERSION, COL.ERRORS]
DBLCLICK_COLS = {COL.MODID, COL.VERSION}




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
        return Qt.Checked if self.enabled else Qt.Unchecked

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

    def __init__(self, *, manager, parent, **kwargs):
        """
        :param skymodman.managers.ModManager manager:
        """
        super().__init__(**kwargs)
        self._parent = parent
        self.manager = manager

        self.mod_entries = [] #type: list[QModEntry]

        self.errors = {}  # dict[str, int] of {mod_directory_name: err_type}

        self.vheader_field = COL.ORDER
        # self.visible_columns = [COL.ENABLED, COL.ORDER, COL.NAME, COL.MODID, COL.VERSION]

        self._datahaschanged = None # placeholder for first start

        # track the row numbers of every mod in the table that is changed in any way.
        # Every time a change is made, the row number is appended to the end of the deque,
        # even if it is already present. Allowing duplicates in this way lets an undo()
        # remove the most recent changes without losing track of any previous changes
        # made to that row.
        self._modifications = deque()

        stack().undocallback = partial(self._undo_event, 'undo')
        stack().docallback = partial(self._undo_event, 'redo')

        self.LOGGER << "init ModTable_TreeModel"

    ##===============================================
    ## Undo/Redo callbacks
    ##===============================================



    ##===============================================
    ## PROPERTIES
    ##===============================================

    @property
    def isDirty(self) -> bool:
        return stack().haschanged()

    def rowCount(self, *args, **kwargs) -> int:
        return len(self.mod_entries)

    def columnCount(self, *args, **kwargs) -> int:
        return len(col2Header)


    @property
    def stack(self):
        return stack()

    def parent(self, child_index):
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

        if parent.isValid() and parent.column() != 0:
            return QModelIndex()

        child = self.mod_entries[row]
        if child:
            return self.createIndex(row, col, child)

        return QModelIndex()

    ##===============================================
    ## Getting and Setting Data
    ##===============================================

    @staticmethod
    def rol_col_switch(role, column):
        return [lambda r,c: role==r and column==c]

    def data(self, index, role=Qt.DisplayRole):
        col = index.column()

        # handle errors first
        if col == COL.ERRORS:
            try:
                err = self.errors[self.mod_entries[index.row()].directory]
                for case, choices in [(lambda r: role == r, lambda d: d[err])]:

                    if case(Qt.DecorationRole): return QtGui.QIcon.fromTheme(
                            choices({SyncError.NOTFOUND: 'dialog-error',
                                     SyncError.NOTLISTED: 'dialog-warning'}))

                    if case(Qt.ToolTipRole): return choices(
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
                pass
        else:
            # switch on combinations of role and column type
            for case in self.rol_col_switch(role, col):

                if case(Qt.CheckStateRole, COL.ENABLED):
                    return self.mod_entries[index.row()].checkState

                if case(Qt.EditRole, COL.NAME):
                    return self.mod_entries[index.row()].name

                if case(Qt.ToolTipRole, COL.NAME):
                    # return directory name as tooltip for name field
                    return self.mod_entries[index.row()].directory

            else:
                if role == Qt.DisplayRole and col != COL.ENABLED:
                    return getattr(self.mod_entries[index.row()], col2field[col])


    def setData(self, index, value, role=None):

        row, col = index.row(), index.column()
        mod = self.mod_entries[row]

        for case in self.rol_col_switch(role, col):

            if case(Qt.CheckStateRole, COL.ENABLED):
                # perform change and add to undo stack
                self.changeModField(index, row, mod, 'enabled', value==Qt.Checked)
                break

            if case(Qt.EditRole, COL.NAME):
                new_name = value.strip()  # remove trailing/leading space
                if new_name in [mod.name, ""]: return False

                self.changeModField(index, row, mod, 'name', new_name)
                break
        else:
            return super().setData(index, value, role)

        # one of the cases must have been satisfied to get here
        return True

    # noinspection PyUnresolvedReferences
    @undoable
    def changeModField(self, index, row, mod, field, value):
        # this is for changing a mod attribute *other* than ordinal
        # (i.e. do not use this when the mod's install order is being changed)

        #do/redo code:
        old_value = getattr(mod, field)
        # updated = mod._replace(**{field: value})
        # setattr(self.mod_entries[row], field, value)
        setattr(mod, field, value)

        # record this row numnber in the modified rows stack
        self._modifications.append(row)

        self.dataChanged.emit(index, index)

        yield "Change {}".format(field)

        # undo code:
        # reverted = self.mod_entries[row]._replace(**{field:old_value})
        # self.mod_entries[row] = reverted
        setattr(mod,field, old_value)
        # remove this row number from the modified rows stack
        self._modifications.pop()

        self.dataChanged.emit(index, index)


    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:

            if orientation == Qt.Horizontal:
                return col2Header[section]

            else:  # vertical header
                return self.mod_entries[section].ordinal

        return super().headerData(section, orientation, role)

    def flags(self, index):
        col = index.column()

        _flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable

        if col == COL.ENABLED:
            return _flags | Qt.ItemIsUserCheckable

        if col == COL.NAME:
            return _flags | Qt.ItemIsEditable

        return _flags

    ##===============================================
    ## Adding and Removing Rows/Columns
    ##===============================================





    ##===============================================
    ## Modifying Row Position
    ##===============================================

    # let's try it a smarter way
    @undoable
    def shiftRows(self, start_row, end_row, move_to_row, parent=QModelIndex()):
        """
        :param start_row:
        :param end_row:
        :param move_to_row:
        :param parent:
        :return:
        """
        # self.LOGGER << "Moving rows {}-{} to row {}.".format(start_row, end_row, move_to_row)
        # self.LOGGER << len(self._parent.selectedIndexes())
        # self.LOGGER << [(idx.row(), idx.column()) for idx in self._parent.selectedIndexes()]


        count       = 1 + end_row - start_row
        d_shift     = move_to_row - start_row      # shift distance; could be +-
        rvector     = -(d_shift//abs(d_shift))      # get inverse normal vector (see below)

        if move_to_row < start_row: # If we're moving UP:
            slice_start = dest_child = move_to_row  # get a slice from smallest index
            slice_end = 1 + end_row    # ... to the end of the rows to displace
        else: # if we're moving DOWN:
            slice_start = start_row
            slice_end   = dest_child = move_to_row + count

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

        # self._check_dirty_status()

        yield "Reorder Mods"

        self.beginMoveRows(parent, start_row, end_row, parent, dest_child)

        # hopefully, the undo just involves rotating in the opposite direction
        self._doshift(slice_start, slice_end, count, -rvector)

        self.endMoveRows()

        # remove all un-modified row numbers
        for _ in range(slice_end-slice_start):
            self._modifications.pop()

        self._parent.clearSelection()

        # self._check_dirty_status()


    def _doshift(self, slice_start, slice_end, count, uvector):
        # copy the slice for reference afterwards
        # s_copy = self.mod_entries[slice_start:slice_end]
        me = self.mod_entries

        # now copy the slice into a deque;
        deck = deque(me[slice_start:slice_end]) #type: deque[QModEntry]

        # rotate the deck in the opposite direction and voila its like we shifted everything.
        deck.rotate(count * uvector)

        for i in range(slice_start, slice_end):
            me[i]=deck.popleft()
            me[i].ordinal = i+1

        # slice em back in, but first replace the ordinal to reflect the mod's new position
        # self.mod_entries[slice_start:slice_end] = [
        #     me._replace(ordinal=slice_start + i)
        #     for i, me in enumerate(deck, start=1)]  # ordinal is 1 higher than index


    def _check_dirty_status(self):
        """
        Checks whether the table has just gone from a saved to an unsaved state, or vice-versa, and sends a notification signal iff there is a state change.
        """
        if self._datahaschanged is None or stack().haschanged() != self._datahaschanged:
            # if _datahaschanged is None, then this is the first time we've changed data this session.
            # Otherwise, we only want to activate when there is a difference between the current and cached state
            self._datahaschanged = stack().haschanged()
            self.tablehaschanges.emit(self._datahaschanged)


    def loadData(self):
        self.beginResetModel()
        self._modifications.clear()
        self._datahaschanged = None
        stack().clear()
        stack().savepoint()

        self.mod_entries = [QModEntry(**d) for d in self.manager.basicModInfo()]

        self.getErrors()

        self.endResetModel()
        self.tablehaschanges.emit(False)

    def getErrors(self):
        self.errors = {}  # reset
        for err in self.manager.getErrors(SyncError.NOTFOUND):
            self.errors[err] = SyncError.NOTFOUND

        for err in self.manager.getErrors(SyncError.NOTLISTED):
            self.errors[err] = SyncError.NOTLISTED

    def reloadErrorsOnly(self):
        self.beginResetModel()
        self.getErrors()
        self.endResetModel()

    ##===============================================
    ## Save and Revert
    ##===============================================

    def save(self):
        to_save = [self.mod_entries[row] for row in set(self._modifications)]

        self.manager.saveUserEdits(to_save)

        # for now, let's just reset the undo stack and consider this the new "start" point
        stack().clear()
        self._datahaschanged = None
        stack().savepoint()

        self._undo_event()

    def revert(self):
        self.beginResetModel()
        self.LOGGER << self.signalsBlocked()
        self.blockSignals(True)
        while stack().canundo():
            # todo: this doesn't block signals...should it?
            stack().undo()

        self.blockSignals(False)
        self.endResetModel()

    ##===============================================
    ## Undo Management
    ##===============================================

    def undo(self):
        stack().undo()

    def redo(self):
        stack().redo()

    def _undo_event(self, action=None):
        if action is None: # Reset
            self.tablehaschanges.emit(False)
            self.undoevent.emit(None, None)
        else:
            self._check_dirty_status()
            self.undoevent.emit(stack().undotext(),
                                stack().redotext())


@withlogger
class ModTable_TreeView(QTreeView):


    itemsSelected = pyqtSignal()
    selectionCleared = pyqtSignal()

    itemsMoved = pyqtSignal(list, QtCore.QAbstractTableModel)

    def __init__(self, *, manager, **kwargs):
        super().__init__(**kwargs)
        self.manager = manager
        self._model = None  # type: ModTable_TreeModel
        self.LOGGER << "Init ModTable_TreeView"

    def initUI(self, grid):
        self.setRootIsDecorated(False) # no collapsing
        self.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.setObjectName("mod_table")
        grid.addWidget(self, 1, 0, 1, 5)

        # self.setModel(ModTableModel(parent=self, manager=self.manager))
        self.setModel(ModTable_TreeModel(parent=self, manager=self.manager))
        self.setColumnHidden(COL.DIRECTORY, True)
        # h=self.header() #type:QHeaderView
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(COL.NAME, QHeaderView.Stretch)

        self._model.notifyViewRowsMoved.connect(self._selection_moved)



    def setModel(self, model):
        super().setModel(model)
        self._model = model

    def loadData(self):
        self._model.loadData()
        self.resizeColumnsToContents()

    def resizeColumnsToContents(self):
        for i in range(self._model.columnCount()):
            self.resizeColumnToContents(i)

    def revertChanges(self):
        self._model.revert()
        self.clearSelection()

    def saveChanges(self):
        self._model.save()

    def selectionChanged(self, selected, deselected):
        if len(self.selectedIndexes()) > 0:
            self.itemsSelected.emit()
        else:
            self.selectionCleared.emit()

        super().selectionChanged(selected, deselected)

    def _selection_moved(self):
        self.itemsMoved.emit(self.selectedIndexes(), self._model)

    def onMoveModsAction(self, distance):
        """
        :param distance: if positive, we're increasing the mod install ordinal--i.e. moving the mod further down the list.  If negative, we're decreasing the ordinal, and moving the mod up the list.
        """
        # we use set() first because Qt sends the row number once for each column in the row.
        rows = sorted(set([idx.row() for idx in self.selectedIndexes()]))
        if rows and distance != 0:

            # uvector = -distance//abs(distance) #direction unit vector

            self._model.shiftRows(rows[0], rows[-1],
                                  rows[0] + distance,
                                  self.rootIndex())

            # self.itemsMoved.emit(self.selectedIndexes(), self._model)


    def undo(self):
        self._model.undo()
    def redo(self):
        self._model.redo()

if __name__ == '__main__':
    from skymodman.managers import ModManager