from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QHeaderView, QTreeView, QAbstractItemView, QMenu, QAction
from PyQt5.QtCore import Qt, pyqtSignal, QAbstractItemModel, QModelIndex, QMimeData

from skymodman import ModEntry
from skymodman.constants import (Column as COL, SyncError)
# , DBLCLICK_COLS, VISIBLE_COLS)
# from skymodman.constants import SyncError
from skymodman.utils import withlogger
from skymodman.thirdparty.undo import undoable, stack, group

from functools import total_ordering, partial
from collections import deque


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

    def __init__(self, *, manager, parent, **kwargs):
        """
        :param ModManager manager:
        """
        super().__init__(**kwargs)
        self._parent = parent
        self.manager = manager

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
        self.removed = []

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

        yield undotext

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
        """
        Load fresh data and reset everything. Called when first loaded and when something major changes, like the active profile.
        """
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

        self.manager.saveUserEdits(to_save)

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



@withlogger
class ModTable_TreeView(QTreeView):

    enableModActions = pyqtSignal(bool)

    canMoveItems = pyqtSignal(bool, bool)

    def __init__(self, *, parent, manager, **kwargs):
        # noinspection PyArgumentList
        super().__init__(parent, **kwargs)
        self.manager = manager
        self._parent = parent # type: ModManagerWindow
        self._model = None  # type: ModTable_TreeModel
        self._selection_model = None # type: QtCore.QItemSelectionModel
        self.LOGGER << "Init ModTable_TreeView"

    def initUI(self, grid):
        self.setRootIsDecorated(False) # no collapsing
        self.setObjectName("mod_table")
        grid.addWidget(self, 1, 0, 1, 5)

        self.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)

        self.setModel(ModTable_TreeModel(parent=self, manager=self.manager))
        self.setColumnHidden(COL.DIRECTORY, True) # hide directory column by default
        # h=self.header() #type:QHeaderView
        self.header().setStretchLastSection(False) # don't stretch the last section...
        self.header().setSectionResizeMode(COL_NAME, QHeaderView.Stretch)  # ...stretch the Name section!

        self._selection_model = self.selectionModel()  # keep a local reference to the selection model
        self._model.notifyViewRowsMoved.connect(self._selection_moved) # called from model's shiftrows() method
        self._model.hideErrorColumn.connect(self._hideErrorColumn) # only show error col if there are errors

    def _hideErrorColumn(self, hide):
        self.setColumnHidden(COL_ERRORS, hide)
        if not hide:
            self.resizeColumnToContents(COL_ERRORS)

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
        if self._selection_model.hasSelection():
            self.enableModActions.emit(True) # enable the button box
            self._selection_moved()   # check for disable up/down buttons
        else:
            self.enableModActions.emit(False)

        super().selectionChanged(selected, deselected)

    def _selection_moved(self):
        # check for selection to prevent movement buttons from reactivating on a redo()
        if self._selection_model.hasSelection():
            issel = self._selection_model.isSelected
            model = self._model
            self.canMoveItems.emit(
                not issel(model.index(0,0)),
                not issel(model.index(model.rowCount()-1, 0))
            )

    def _selectedrownumbers(self):
        # we use set() first because Qt sends the row number once for each column in the row.
        return sorted(set(
                [idx.row()
                 for idx in
                 self.selectedIndexes()]))

    def _tellmodelshiftrows(self, dest, *, rows=None, text="Reorder Mods"):
        """
        :param int dest: either the destination row number or a callable that takes the sorted list of selected rows as an argument and returns the destination row number.
        :param rows: the rows to shift. If None or not specified, will be derived from the current selection.
        :param text: optional text that will appear after 'Undo' or 'Redo' in the Edit menu
        """
        if rows is None:
            rows = self._selectedrownumbers()
        if rows:
            self._model.shiftRows(rows[0],
                          rows[-1],
                          dest,
                          parent=self.rootIndex(),
                          undotext=text)

    def onMoveModsToTopAction(self):
        self._tellmodelshiftrows(0, text="Move to Top")

    def onMoveModsToBottomAction(self):
        self._tellmodelshiftrows(self._model.rowCount()-1, text="Move to Bottom")

    def onMoveModsAction(self, distance):
        """
        :param distance: if positive, we're increasing the mod install ordinal--i.e. moving the mod further down the list.  If negative, we're decreasing the ordinal, and moving the mod up the list.
        """
        rows = self._selectedrownumbers()
        if  distance != 0:
            self._tellmodelshiftrows(rows[0]+distance, rows=rows)

    def undo(self):
        self._model.undo()
    def redo(self):
        self._model.redo()

    def dragEnterEvent(self, event):
        """ Qt-override.
        Implementation needed for enabling drag and drop within the view.

        :param QDragEnterEvent event:
        """
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)

    def contextMenuEvent(self, event):
        """

        :param QContextMenuEvent event:
        """
        mw = self._parent # mainwindow
        menu = QMenu(self)
        menu.addActions([mw.action_togglemod
                         ])
        menu.exec_(event.globalPos())

    def toggleSelectionCheckstate(self):
        # to keep things simple, we base the first toggle off of the enabled state of the
        # current index.  E.g., even if it's the only enabled mod in the selection,
        # the first toggle will still be a disable command. It's rough, but the user may
        # need to hit 'Space' **twice** to achieve their goal.  Might lose a lot of people over this.
        currstate = self.currentIndex().internalPointer().enabled
        sel = self.selectedIndexes()

        # group these all into one undo command
        with group(": {} Mod{}".format(
                ["Enable", "Disable"][currstate],
                "s" if len(sel)>self._model.columnCount() else "")):
            for i in sel:
                if i.column() == COL_ENABLED:
                    self._model.setData(i, [Qt_Checked, Qt_Unchecked][currstate], Qt_CheckStateRole)


if __name__ == '__main__':
    from skymodman.managers import ModManager
    from skymodman.qt_interface.managerwindow import ModManagerWindow
    from PyQt5.QtGui import QDragEnterEvent, QContextMenuEvent
