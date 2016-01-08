from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtCore import Qt, pyqtSignal, QItemSelection
from typing import List

from skymodman import constants, ModEntry
from skymodman.utils import withlogger

class QModEntry(ModEntry):
    """
    Namedtuple subclass that eases accessing derived properties for displaying in the Qt GUI
    """
    # from the python docs: [Set] __slots__ to an empty tuple. This helps keep memory requirements low by preventing the creation of instance dictionaries.
    __slots__=()

    @property
    def checkState(self):
        return Qt.Checked if self.enabled else Qt.Unchecked

    def __eq__(self, other):
        return self.name == other.name and self.enabled == other.enabled and self.ordinal == other.ordinal




@withlogger
class ModTableModel(QtCore.QAbstractTableModel):
    """
    QAbstractTableModel specialized to consider each row as a single item for some purposes.
    """

    COLUMNS = (COL_ENABLED, COL_NAME, COL_MODID, COL_VERSION, COL_ORDER) = list(range(5))

    VISIBLE_COLS = [COL_ENABLED, COL_NAME, COL_MODID, COL_VERSION]

    DBLCLICK_COLS = [COL_MODID, COL_VERSION]

    headers = ["", "Name", "Mod ID", "Version"]

    # emitted when self.modified_rows becomes either non-empty or empty
    # (but not if the 'empty'-status doesn't change)
    tableDirtyStatusChange = pyqtSignal(bool)

    def __init__(self, parent, manager: 'ModManager', *args):
        super(ModTableModel, self).__init__(parent, *args)
        self._table = parent
        self.manager = manager # type: ModManager

        self.mods = [] # type: List[QModEntry]
        self.vheader_field = constants.COL_ORDER
        self.visible_columns = []

        self.modified_rows = {}

        self.LOGGER.debug("init ModTableModel")

    @property
    def isDirty(self):
        return len(self.modified_rows) > 0

    def rowCount(self, parent = QtCore.QModelIndex(), *args, **kwargs):
        """
        Number of mods installed
        :param parent: ignored
        :return:
        """
        return len(self.mods)

    def columnCount(self, parent = QtCore.QModelIndex(), *args, **kwargs):
        """
        At the moment, returns 4. (Enabled, Name, ID, Version)
        :param parent: ignored
        :return:
        """
        return len(self.VISIBLE_COLS)

    def data(self, index: QtCore.QModelIndex, role=Qt.DisplayRole):
        """ Qt override
        Controls how the data for a cell is presented.
        :param index:
        :param role: we handle Qt.CheckStateRole for the enabled column,
                    and Qt.DisplayRole for everything else.
        :return: for the checkbox: Qt.Checked or Qt.Unchecked, depending on whether or not the mod is enabled.
        All other columns just return their text value.
        """
        col = index.column()
        if role == Qt.DisplayRole and col != constants.COL_ENABLED:
            return self.mods[index.row()][col]
        elif role == Qt.CheckStateRole and col == constants.COL_ENABLED:
            return self.mods[index.row()].checkState
        elif role == Qt.EditRole and col == constants.COL_NAME:
            return self.mods[index.row()].name
        elif role == Qt.ToolTipRole and col == constants.COL_NAME:
            # return directory name as tooltip for name field
            return self.mods[index.row()].directory

    def setData(self, index, value:str, role=None):
        """ Qt-override.
        This handles changes to the checkbox (whether the mod is enabled/disabled)
        and to the displayed name field.
        Here is where we need to track changes to items to allow undo
        :param index: which cell was edited
        :param value: the new value of the cell (ignored for the enabled column)
        :param role: we hangle Qt.CheckStateRole for the Enabled col and Qt.EditRole for the name col
        :return:
        """
        if role==Qt.CheckStateRole and index.column() == constants.COL_ENABLED:
            self.toggleEnabledState(index.row())
            return True

        elif role == Qt.EditRole and index.column() == constants.COL_NAME:
            row = index.row()
            mod = self.mods[row]
            new_name = value.strip() # remove trailing/leading space

            # don't bother recording if there was no change
            if new_name == mod.name: return False
            # and don't allow empty names
            if new_name == "": return False

            newmod = mod._replace(name=new_name)

            need_notify = self.onModDataEdit(row, mod, newmod)

            self.dataChanged.emit(index, index)

            if need_notify is not None:
                self.tableDirtyStatusChange.emit(need_notify)
            return True

        return super(ModTableModel, self).setData(index, value, role)

    def onModDataEdit(self, row:int, current:QModEntry, edited: QModEntry):
        """
        checks if the new value of the mod matches the value of the mod
         at the time of the last save
         :param row: the row-index of the mod in the table and self.mods
         :param current: current value of the mod at this index in self.mods
         :param edited: the user-edited value of the mod at this index
         :return: One of True, False, or None, corresponding to which signal value
         should be emitted by tableDirtyStatusChange(). True indicates that a clean
         table was just made dirty (has unsaved changes), False means that a dirty
         table now once again matches its clean state, and None means there has been
         no change in this status (and no signal should be emitted)
         """

        notify_dirty = None

        if row in self.modified_rows:
            # if it has returned to its initial state,
            # remove the row from the list of modified rows
            if edited == self.modified_rows[row]:
                del self.modified_rows[row]

                # if that was the last item, notify that table
                # no longer has unsaved changes.
                if len(self.modified_rows) == 0:
                    notify_dirty = False
        else:
            # store initial value
            self.modified_rows[row] = current

            # if this was the first item, notify that table
            # now has unsaved changes
            if len(self.modified_rows) == 1:
                notify_dirty = True

        self.mods[row] = edited # update value with edited entry
        return notify_dirty

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
        Returns labels for the vertical and horizontal headers of the table
        :param section: if orientation==Qt.Horizontal, this is the column number.
                        if orientation==Qt.Vertical, this is the row number.
        :param orientation: either Qt.Horizontal or Qt.Vertical
        :param role: we're only interested in Qt.DisplayRole for the moment.
        :return:
        """
        # self.logger.debug("Loading header data for {}:{}:{}".format(row_or_col, orientation, role))
        if role==Qt.DisplayRole:

            if orientation == Qt.Horizontal:
                return self.headers[section]

            else: # vertical header
                return self.mods[section].ordinal

        return super(ModTableModel, self).headerData(section, orientation, role)

    def flags(self, index: QtCore.QModelIndex):
        """
        Called for each cell in the table. this model returns:

            for the 'Enabled' (checkbox) column: Qt.ItemIsEnabled | Qt.ItemIsUserCheckable

            For the 'Mod ID' and 'Version' columns: Qt.ItemIsSelectable

            For the 'Name' column: Qt.ItemIsSelectable | Qt.ItemIsEditable

        If the backing ModEntry for this row is enabled, then id, version, and name will also
        include Qt.ItemIsEnabled in their flags.

        Should an index be passed that, somehow, doesn't match any of these columns,
        Qt.NoItemFlags is returned.

        :param index: Table index of the cell in question.
        :return: the effective itemFlags for the cell at the specified index
        """
        col = index.column()

        if col == self.COL_ENABLED:
            return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable

        # _flags = Qt.NoItemFlags #start with nothing

        # if this row is enabled, start with the enabled flag
        # if self.mods[index.row()].enabled:
        _flags = Qt.ItemIsEnabled

        # mod id and version are selectable
        if col in [self.COL_MODID, self.COL_VERSION]:
            return _flags | Qt.ItemIsSelectable

        # name is selectable and editable
        if col == self.COL_NAME:
            return _flags | Qt.ItemIsSelectable | Qt.ItemIsEditable

        return _flags
    
    def rowDataChanged(self, row):
        """Emits data changed for every item in this table row"""
        idx_start = self.index(row, 0)
        idx_end = self.index(row, self.columnCount())
        self.dataChanged.emit(idx_start, idx_end)

    def loadData(self):
        """
        Query the ModManager for a full set of mod-data from the database. This is done during
        setup and when the profile is changed, and triggers a full reset of the table.
        :return:
        """
        self.beginResetModel()
        # set (or reset) the list of tracked changes
        self.modified_rows = {}
        # load fresh mod info

        self.mods = [QModEntry(**d) for d in self.manager.basicModInfo()]

        # self.mods = [QModEntry._make(e) for e in self.manager.basicModInfo()]
        self.endResetModel()

    def on_doubleClick(self, index:QtCore.QModelIndex):
        """
        Double-clicking on a row will toggle that mod active or inactive (same as clicking
        the checkbox in the first column
        :param index: QModelIndex corresponding to the cell that was just clicked.
        :return:
        """
        if not index.isValid() or index.column() not in self.DBLCLICK_COLS: return

        self.toggleEnabledState(index.row())

    def toggleEnabledState(self, row: int):
        """
        For the mod at row `row`, set it enabled if it is currently disabled, or vice-versa.
        This adjusts the enabled-status of all the other fields and emits a datachanged()
        signal for each one.
        :param row: the number of the mod in the table-display; also the index of the mod in
        the model's `self.mods` list, and the effective ordinal rank of this mod in the installation list.
        :return:
        """
        mod = self.mods[row]
        newmod = mod._replace(enabled=int(not mod.enabled))

        need_notify = self.onModDataEdit(row, mod, newmod)

        for c in self.VISIBLE_COLS:
            if c==constants.COL_ENABLED:
                continue
            index = self.index(row, c) # type: QtCore.QModelIndex

        self.rowDataChanged(row)

        if need_notify is not None:
            self.tableDirtyStatusChange.emit(need_notify)

    def revert(self):
        """
        Reset all modified rows to their initial state (i.e., the values of the fields the
        last time the mods list was saved.)
        """
        for cached_mod in self.modified_rows.values():
            original_row = cached_mod.ordinal-1
            self.mods[original_row] = cached_mod
            self.rowDataChanged(original_row)

        self.modified_rows.clear()
        self.tableDirtyStatusChange.emit(False)

    def save(self):
        """
        Save the data for the rows marked as modified to disk. The current state will
        become the new base state (the state returned to when the Revert button is pressed)
        :return:
        """
        # list of (name, enabled, ordinal) tuples to send to modmanager
        # to_save = [(self.mods[row].name, self.mods[row].enabled, self.mods[row].ordinal) for row in self.modified_rows]

        to_save = [self.mods[row] for row in self.modified_rows]

        self.manager.saveUserEdits(to_save)

        self.modified_rows.clear()
        self.tableDirtyStatusChange.emit(False)


    # def moveRows(self, sourceParent: QtCore.QModelIndex, start: int, count: int, destParent: QtCore.QModelIndex, destChild: int):
    #     return super(ModTableModel, self).moveRows(sourceParent, start, count, destParent, destChild)

    def shiftRows(self, start_row:int, end_row:int, move_to_row:int, parent=QtCore.QModelIndex()):
        """
        Move the contiguous section of rows from start..end to the position specified by dest_index;
         that is, after the move, start_row will have be at position dest_index.
        :param start_row:
        :param end_row:
        :param move_to_row:
        :return:
        """

        # beginMoveRows(index srcParent, int srcFirst, int srcLast, index destParent, int destChild)
        #   we have same parent, so we use: (parent, first, last, parent, dest)


        # when moving rows down, the entire section is moved so that the first element is in dest; but beginMoveRows defines
        # destChild (the last argument) as the row BEFORE which the section is moved; so moving rows
        # 2-4 to row 5 would mean that destchild would be (5+((4-2)+1))=8
        # FROM DOCS:
        #   "the new index for the source row i (which is between sourceFirst and sourceLast)
        #       is equal to (destinationChild-sourceLast-1+i)"
        # thus the new index for row 3 in our example would be (8-4-1+3)=6;
        # in terms of move_to_row,
        #   destChild = (move_to_row + num_rows_moves)
        #   num_rows_moved = (srcLast - srcFirst)+1
        #   dC = mtr+srcLast-srcFirst+1

        #  > dC = 5+4-2+1 = 8
        #  > 3..5->8 ==> dC = 8+5-3+1 = 11

        # track this to see if we should emit a tableDirty signal afterwards
        initial_modified_count = len(self.modified_rows)


        selection = self.mods[start_row:end_row+1] #  mods being moved
        count = len(selection)
        # displaced = [] # mods that will be reordered as a side-effect of this operation

        new_modified_rows = []
        if move_to_row > start_row:
            # moving mods down in the list (ordinal number increases)
            shift_distance = move_to_row - start_row # this is how many unselected mods will be displaced

            self.beginMoveRows(parent, start_row, end_row, parent, move_to_row + count)

            for i in range(start_row, start_row+shift_distance):
                # shift items between selection and destination index up by <count>
                r = self.reorderMod(i, self.mods[i+count])
                # self.mods[i] = self.mods[i+count]
                if r is not None: new_modified_rows.append(r)

            for i in range(count):
                # move selection into place
                r = self.reorderMod(move_to_row+i, selection[i])
                # self.mods[move_to_row+i] = selection[i]
                if r is not None: new_modified_rows.append(r)


            self.endMoveRows()


        elif move_to_row < start_row:
            # moving mods up (ordinal number decreases)
            shift_distance = start_row - move_to_row

            self.beginMoveRows(parent, start_row, end_row, parent, move_to_row)

            # shift items between selection and destination index down by <count>
            for i in range(end_row, end_row-shift_distance, -1):
                r = self.reorderMod(i, self.mods[i-count])
                if r is not None: new_modified_rows.append(r)
            for i in range(count):
                r = self.reorderMod(move_to_row+i, selection[i])
                if r is not None: new_modified_rows.append(r)

                # self.mods[move_to_row+i] = selection[i]

            self.endMoveRows()
        else:
            return False


        for r in new_modified_rows:
            self.modified_rows.update(r)

        if initial_modified_count: # >0
            if len(self.modified_rows) == 0: self.tableDirtyStatusChange.emit(False)

        else: # imc==0
            if len(self.modified_rows) > 0: self.tableDirtyStatusChange.emit(True)

        return True

    def reorderMod(self, new_row: int, mod:QModEntry ):
        """
        Moves the given mod to the new position in the list of mods and updates its ordinal number to match.

        :param new_row: destination row for mod being moved
        :param mod: the mod entry which is being moved to the new position
        :return: a dict of length 1 containing a pair to insert into the self.modified_rows dict
        after the reorder-loop has finished running; or None if nothing to insert
        """
        old_row = mod.ordinal-1

        updated = mod._replace(ordinal=new_row+1)

        r=None
        # check modified rows list
        if old_row in self.modified_rows:
            # compare updated mod to saved initial state:
            if updated == self.modified_rows[old_row]:
                del self.modified_rows[old_row]
            else:
                # update entry to associate the intial mod state with its new row position.
                # **create updated entry, but do not insert into modified_rows yet
                # as that could cause issues as we continue through the list of mods to reorder;
                # instead, return the entry for caller to save and handle
                r={new_row: self.modified_rows[old_row]}
        else:
            # create initial entry
            r = {new_row: mod}

        self.mods[new_row] = updated

        return r





@withlogger
class ModTableView(QtWidgets.QTableView):
    """
    Slightly specialized QTableView to help with displaying the custom model
     (and to allow refactoring of a lot of the table-specific code out of the MainWindow class)
    """

    itemsSelected = pyqtSignal()
    selectionCleared = pyqtSignal()

    itemsMoved = pyqtSignal(list, QtCore.QAbstractTableModel)

    def __init__(self, parent, manager, *args, **kwargs):
        super(ModTableView, self).__init__(parent, *args, **kwargs)
        self.manager = manager
        self._model = None #type: ModTableModel
        self.LOGGER.debug("Init ModTableView")


    def initUI(self, grid):
        self.LOGGER.debug("init ModTable UI")
        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ContiguousSelection)
        self.setObjectName("mod_table")
        grid.addWidget(self, 1, 0, 1, 5) # from old qtdesigner file

        self.setModel(ModTableModel(self, self.manager))
        hheader = self.horizontalHeader()  # type: QHeaderView
        hheader.setHighlightSections(False)
        hheader.setSectionResizeMode(constants.COL_NAME, QHeaderView.Stretch)
        hheader.setDefaultAlignment(Qt.AlignLeft)

        # f = hheader.font() #type: QtGui.QFont
        # f = QtGui.QFont('cursive')
        # f.setPointSize(12)
        # f.setCapitalization(QtGui.QFont.SmallCaps)
        # hheader.setFont(f)
        # self.setFont(QtGui.QFont('serif', 12))

        vheader = self.verticalHeader()  # type: QHeaderView
        vheader.setFont(QtGui.QFont('mono', 10))
        vheader.setDefaultAlignment(Qt.AlignRight)

        self.doubleClicked.connect(self._model.on_doubleClick)


    def setModel(self, model):
        super(ModTableView, self).setModel(model)
        self._model = model

    def loadData(self):
        self._model.loadData()
        self.resizeColumnsToContents()

    def revertChanges(self):
        self._model.revert()

    def saveChanges(self):
        self._model.save()

    def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection):
        # self.LOGGER.debug("Selection Changed:\n    selected: {}\n    deselected: {}".format(selected.indexes(), deselected.indexes()))
        # self.LOGGER.debug("SelectedIndexes:\n   {}".format(self.selectedIndexes()))
        if len(self.selectedIndexes()) > 0:
            self.itemsSelected.emit()
        else:
            self.selectionCleared.emit()
            
            
        super(ModTableView, self).selectionChanged(selected, deselected)

    def onMoveModsUpAction(self, distance:int=1):
        """
        currently only handles moving mod (or selection of mods) up 1 spot at a time
        :return:
        """
        # rows = [idx.row() for idx in self.selectedIndexes()]
        rows = list(set([idx.row() for idx in self.selectedIndexes()]))
        # print(rows)
        if rows:

            self.LOGGER.debug("Moving rows {}-{} to row {}.".format(rows[0], rows[-1], rows[0]-distance))

            self._model.shiftRows(rows[0], rows[-1], rows[0]-distance)

        # emit signal to allow up/down buttons to be toggled as necessary
        self.itemsMoved.emit(self.selectedIndexes(), self._model)
        # self.checkSelection()

    def onMoveModsDownAction(self, distance:int=1):
        rows = list(set([idx.row() for idx in self.selectedIndexes()]))
        # print(rows)

        if rows:

            self.LOGGER.debug("Moving rows {}-{} to row {}.".format(rows[0], rows[-1], rows[0]+distance))

            self._model.shiftRows(rows[0], rows[-1], rows[0] + distance)

        self.itemsMoved.emit(self.selectedIndexes(), self._model)


        # self.checkSelection()


    # def checkSelection(self):
    #     print(set([p.row() for p in self.selectedIndexes()]))



    # def edit(self, index, trigger=None, event=None):
    #     if index.column() == constants.COL_NAME:
    #         return super(ModTableView, self).edit(index, trigger, event)
    #     else:
    #         return False


if __name__ == '__main__':
    from skymodman.managers import ModManager