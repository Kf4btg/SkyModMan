from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QHeaderView, QTreeView#, QUndoStack
from PyQt5.QtCore import Qt, pyqtSignal, QItemSelection, QAbstractItemModel, QModelIndex

from skymodman import ModEntry
# from skymodman.constants import (Column as COL, SyncError, DBLCLICK_COLS, VISIBLE_COLS)
from skymodman.constants import SyncError
from skymodman.utils import withlogger
# from skymodman.managers import undo as Undo
# from skymodman.qt_interface.models.modtable import ModTableModel
from skymodman.thirdparty.undo import undoable, stack


# from skymodman.qt_interface.models.undoactions import ShiftRowsCommand

from enum import IntEnum
from functools import total_ordering, partial
from collections import namedtuple, deque

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


update = namedtuple('update', 'field new_value')

@total_ordering
class QModEntry(ModEntry):
    """
    Namedtuple subclass that eases accessing derived properties for displaying in the Qt GUI
    """
    # from the python docs: [Set] __slots__ to an empty tuple. This helps keep memory requirements low by preventing the creation of instance dictionaries.
    __slots__=()

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

    # def __hash__(self):
    #     return hash(self.directory) # the one constant


@withlogger
class ModTable_TreeModel(QAbstractItemModel):

    tablehaschanges = pyqtSignal(bool)
    undoevent = pyqtSignal(str, str) # undotext, redotext
    # redoevent = pyqtSignal(str)

    def __init__(self, *, manager, parent, **kwargs):
        """
        :param skymodman.managers.ModManager manager:
        """
        super().__init__(**kwargs)
        self._parent = parent
        self.manager = manager

        # self.undostack = QUndoStack()

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

        stack().undocallback = partial(self._on_undo_stack_event, 'undo')
        stack().docallback = partial(self._on_undo_stack_event, 'redo')

        # namedtuples are hashable...
        # self.modified_rows = {}

        # self.undostack = Undo.RevisionTracker()
        # self.undostack.registerType(QModEntry, lambda e: e.directory,
        #                             *QModEntry._fields,
        #                             attrsetter=lambda e,f,v: e._replace(**{f:v}))

        self.LOGGER << "init ModTable_TreeModel"

    ##===============================================
    ## Undo/Redo callbacks
    ##===============================================

    def _on_undo_stack_event(self, action=None):
        if action is None:
            self.tablehaschanges.emit(False)
            self.undoevent.emit(None, None)
        else:
            self._check_dirty_status()
            self.undoevent.emit(stack().undotext(), stack().redotext())
        #
        # if action == 'undo':
        #     self._check_dirty_status()
        #     self.undoevent.emit(stack().redotext())
        # elif action == 'redo':
        #     self._check_dirty_status()
        #     self.undoevent.emit(stack().undotext())
        # else:
        #     # stack has been cleared
        #     self.tablehaschanges.emit(False)
        #     self.undoevent.emit('', '')

    #
    # def _onundo(self):
    #     self._check_dirty_status()
    #     self.undoevent.emit(stack().redotext())
    # def _onredo(self):
    #     self._check_dirty_status()
    #     self.redoevent.emit(stack().undotext())

    ##===============================================
    ## PROPERTIES
    ##===============================================

    @property
    def isDirty(self) -> bool:
        # return len(self.modified_rows) > 0
        return stack().haschanged()

    def rowCount(self, *args, **kwargs) -> int:
        return len(self.mod_entries)

    def columnCount(self, *args, **kwargs) -> int:
        return len(col2Header)


    @property
    def stack(self):
        return stack()

    def parent(self, child_index):
        return QModelIndex()
        # if not child_index.isValid(): return QModelIndex()
        #
        # # get the parent FSItem from the reference stored in each FSItem
        # parent = child_index.internalPointer().parent
        #
        # if not parent or parent is self.rootitem:
        #     return QModelIndex()
        #
        # # Every FSItem has a row attribute which we use to create the index
        # return self.createIndex(parent.row, 0, parent)

    def index(self, row, col=0, parent=QModelIndex(), *args,
              **kwargs) -> QModelIndex:
        """

        :param int row:
        :param int col:
        :param QModelIndex parent:
        :return: the QModelIndex that represents the item at (row, col) with respect
                 to the given  parent index. (or the root index if parent is invalid)
        """

        # parent_item = self._parent.rootIndex()
        if parent.isValid() and parent.column() != 0:
            return QModelIndex()
        #     parent_item = parent.internalPointer()

        # child = parent_item[row]
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

    # noinspection PyTypeChecker
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
                # updated = self.undostack.push(mod, 'enabled', value==Qt.Checked )
                # up = update(field='enabled',
                #             new_value=value==Qt.Checked)
                break

            if case(Qt.EditRole, COL.NAME):
                new_name = value.strip()  # remove trailing/leading space
                if new_name in [mod.name, ""]: return False

                # up = update('name', new_name)
                self.changeModField(index, row, mod, 'name', new_name)

                # updated = self.undostack.push(mod, 'name', new_name)

                break
        else:
            return super().setData(index, value, role)

        # one of the cases must have been satisfied to get here
        # newmod = mod._replace(**{up.field: up.new_value})
        # self.mod_entries[row] = newmod
        # self.mod_entries[row] = updated

        # noinspection PyUnresolvedReferences
        # self.dataChanged.emit(index, index)
        # self.checkModChange(up.field, mod, newmod)
        return True


    @undoable
    def changeModField(self, index, row, mod, field, value):
        # this is for changing a mod attribute *other* than ordinal
        # (i.e. do not use this when the mod's install order is being changed)

        #do/redo code:
        old_value = getattr(mod, field)
        updated = mod._replace(**{field: value})
        self.mod_entries[row] = updated

        # record this row numnber in the modified rows stack
        self._modifications.append(row)

        self.dataChanged.emit(index, index)
        # self._emit_data_changed(index, index)

        yield "Change {}".format(field)

        # undo code:
        reverted = self.mod_entries[row]._replace(**{field:old_value})
        self.mod_entries[row] = reverted

        # remove this row number from the modified rows stack
        self._modifications.pop()

        self.dataChanged.emit(index, index)
        # self._emit_data_changed(index, index)

    #
    # def checkModChange(self, field, oldmod, newmod, no_notify=False):
    #     """
    #     If this mod has returned to its original state, remove it from the list of edited mods and notify the view if that was the table's last unsaved change.  If it has been modified for the first time, add it to the edited-list and notify the view if that was the first change made to the table.
    #
    #     :param str field: name of field in the mod entry to check for change
    #     :param QModEntry oldmod: previous state of mod
    #     :param QModEntry newmod: state of mod after user edit
    #     :param no_notify: if True, suppress any signal this method might have sent; instead, return a value indicating the updated "dirty" value of the model:
    #
    #         None   # means 'No change in Table dirtiness'
    #         False  # 'False' means 'Table is NO LONGER dirty'
    #         True   # 'True' means 'Table HAS BECOME dirty'
    #     """
    #     notify_value = None  # means 'No change in Table dirtiness'
    #     key = newmod.directory
    #     try:
    #         if getattr(newmod, field) == getattr(self.modified_rows[key], field):
    #             del self.modified_rows[key]
    #             if len(self.modified_rows) == 0: notify_value = False  # 'False' means 'Table is NO LONGER dirty'
    #     except KeyError:
    #         self.modified_rows[key] = oldmod
    #         if len(self.modified_rows) == 1: notify_value = True  # 'True' means 'Table HAS BECOME dirty'
    #
    #     if no_notify: return notify_value
    #
    #     if notify_value is not None:
    #         self.tablehaschanges.emit(notify_value)

    # def multiChangeCheck(self, mods):
    #     """
    #     when there's a lot of changes that may have happened at once, `checkModChange` would not be appropriate for the job.  This will run through a list of changed mods and determine whether any of them are newly changed or back to normal.
    #     :param mods:
    #     :return:
    #     """
    #     pass


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

    # let's try it a smart way
    # def shiftRows(self, start_row, end_row, move_to_row, parent) -> bool:
    #     """
    #     :param start_row:
    #     :param end_row:
    #     :param move_to_row:
    #     :param parent:
    #     :return:
    #     """


        # self.undostack.push(ShiftRowsCommand(self.mod_entries, start_row, end_row, move_to_row, parent))


    @undoable
    def shiftRows(self, start_row, end_row, move_to_row, parent=QModelIndex()):
        """
        :param start_row:
        :param end_row:
        :param move_to_row:
        :param parent:
        :return:
        """

        print("shift: startrow:{}, endrow:{}, destrow:{}, p:{}".format(start_row, end_row, move_to_row, parent.data()))

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


        print("count:", count ,", d_shift: ", d_shift ,", vec:",rvector)

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

        self._check_dirty_status()

        yield "Reorder Mods"

        self.beginMoveRows(parent, start_row, end_row, parent, dest_child)

        # hopefully, the undo just involves rotating in the opposite direction
        self._doshift(slice_start, slice_end, count, -rvector)

        self.endMoveRows()

        # remove all un-modified row numbers
        for _ in range(slice_end-slice_start):
            self._modifications.pop()

        self._check_dirty_status()


        # copy the slice for reference afterwards
        # s_copy = self.mod_entries[slice_start:slice_end]
        # now copy the slice into a deque;
        # d = deque(s_copy)
        # rotate the deck in the opposite direction and voila its like we shifted everything.
        # d.rotate(count*rvector)

        # slice em back in, but first replace the ordinal to reflect the mod's new position
        # self.mod_entries[slice_start:slice_end] = [me.replace(ordinal=slice_start+i)
        #                                            for i,me in ((_,d.popleft()) # this might be faster than iter??...
        #                                                         for _ in range(1,1+slice_end-slice_start))
        #                                                         ] # ordinal is 1 higher than index


    def _doshift(self, slice_start, slice_end, count, uvector):
        # copy the slice for reference afterwards
        # s_copy = self.mod_entries[slice_start:slice_end]
        from pprint import pprint
        # now copy the slice into a deque;
        deck = deque(self.mod_entries[slice_start:slice_end]) #type: deque[QModEntry]
        print("slice_start:", slice_start)
        print("slice_end:", slice_end)
        print("count:", count)
        [pprint(m._asdict()) for m in deck]

        # rotate the deck in the opposite direction and voila its like we shifted everything.
        deck.rotate(count * uvector)

        print('::::::::::::::::::::::::::::::::::::')
        [pprint(m._asdict()) for m in deck]


        # slice em back in, but first replace the ordinal to reflect the mod's new position
        self.mod_entries[slice_start:slice_end] = [
            me._replace(ordinal=slice_start + i)
            for i, me in enumerate(deck, start=1)]  # ordinal is 1 higher than index

    # def shiftRows(self, start_row, end_row, move_to_row, parent) -> bool:
    #
    #     initial_modified_count = len(self.modified_rows)
    #     # selection              = self.mod_entries[start_row:end_row + 1] #  mods being moved
    #     count                  = 1+end_row-start_row
    #     new_modified_rows      = []
    #
    #     # +sd = move down :  A [B C] D ==> A d [B C]
    #     # -sd = move up   :  A [B C] D ==> [B C] a D
    #     shift_distance = move_to_row - start_row
    #
    #     # Modify them in place
    #     for r in range(count):
    #         current = self.mod_entries[r]
    #         reordered_mod = self.mod_entries[r] = current._replace(ordinal=current.ordinal + shift_distance)
    #         new_modified_rows.append(reordered_mod.directory)
    #
    #     # inverse of normal vector to get the displacement direction
    #     nvector = shift_distance/abs(shift_distance) * -1
    #     # now update the displaced mods
    #     if shift_distance > 0:
    #         # displaced mods have current indices in range [end_row, end_row+shift_distance]
    #         # and are moved by `count` spaces in the opposite direction of the shift
    #         dstart = end_row+1
    #         dlast = dstart+shift_distance
    #     else:
    #         dstart = move_to_row
    #         dlast = start_row-1
    #
    #     for d in range(dstart, dlast):
    #         current = self.mod_entries[d]
    #         displaced_mod = self.mod_entries[d] = current._replace(ordinal=current.ordinal+(nvector*count))
    #         new_modified_rows.append(displaced_mod.directory)
    #
    #
    #
    #
    #
    #
    #
    #
    #     # <editor-fold desc="silly stuff">
    #     if move_to_row > start_row:  # A [B C] D ==> A D [B C]
    #         shift_distance = move_to_row - start_row
    #
    #         self.beginMoveRows(parent, start_row, end_row,
    #                            parent, move_to_row + count)
    #
    #         for i in range(start_row, start_row + shift_distance):
    #             # shift items between selection and destination index up by <count>
    #             r = self.reorderMod(i, self.mods[i + count])
    #             if r is not None: new_modified_rows.append(r)
    #
    #         for i in range(count):
    #             # move selection into place
    #             # r = self.reorderMod(move_to_row + i, selection[i])
    #             if r is not None: new_modified_rows.append(r)
    #
    #         self.endMoveRows()
    #
    #     elif move_to_row < start_row:  # A [B C] D ==> [B C] A D
    #         shift_distance = start_row - move_to_row
    #
    #         self.beginMoveRows(parent, start_row, end_row, parent, move_to_row)
    #
    #         # shift items between selection and destination index down by <count>
    #         for i in range(end_row, end_row - shift_distance, -1):
    #             r = self.reorderMod(i, self.mods[i - count])
    #             if r is not None: new_modified_rows.append(r)
    #         for i in range(count):
    #             # r = self.reorderMod(move_to_row + i, selection[i])
    #             if r is not None: new_modified_rows.append(r)
    #
    #         self.endMoveRows()
    #     else:
    #         return False
    #
    #     for r in new_modified_rows:
    #         self.modified_rows.update(r)
    #
    #     if initial_modified_count:  # >0
    #         if len(self.modified_rows) == 0: self.tablehaschanges.emit(False)
    #
    #     else:  # imc==0
    #         if len(self.modified_rows) > 0: self.tablehaschanges.emit(True)
    #     # </editor-fold>
    #
    #     return True

    # def reorderMod(self, new_row, mod):
    #     old_row = mod.ordinal - 1
    #
    #     updated = mod._replace(ordinal=new_row + 1)
    #
    #     r = None
    #     if old_row in self.modified_rows:
    #         if updated == self.modified_rows[old_row]:
    #             del self.modified_rows[old_row]
    #         else:
    #             r = {new_row: self.modified_rows[old_row]}
    #     else:
    #         r = {new_row: mod}
    #
    #     self.mods[new_row] = updated
    #
    #     return r




    ##===============================================
    ## Callbacks and Slots
    ##===============================================

    # def onModDataEdit(self, current, edited):
    #     """
    #
    #     :param current: current state of entry for this mod
    #     :param edited: state of mod after user edit is committed
    #     :return:
    #     """
    #     notify_dirty = None
    #     key = edited.directory
    #
    #     try:
    #         if edited == self.modified_rows[key]
    #             del self.modified_rows[key]
    #     except KeyError:
    #         self.modified_rows[key] = current
    #     # if edited.directory in self.modified_rows:
    #     #     if edited == self.modified_rows[row]:
    #     #         del self.modified_rows[row]
    #
    #             if len(self.modified_rows) == 0:
    #                 notify_dirty = False
    #     else:
    #         self.modified_rows[row] = current
    #
    #         if len(self.modified_rows) == 1:
    #             notify_dirty = True
    #
    #     self.mod_entries[row] = edited  # update value with edited entry
    #     return notify_dirty

    # def _emit_data_changed(self, index1, index2, roles=None):
    #     """Checks for change in the clean/changed state of the table, then emits the dataChanged signal for the selection between index1 and index2"""
    #
    #
    #     # then send signal
    #     if roles:
    #         self.dataChanged.emit(index1, index2, roles)
    #     else:
    #         self.dataChanged.emit(index1, index2)


    def _check_dirty_status(self):
        """
        Checks whether the table has just gone from a saved to an unsaved state, or vice-versa, and sends a notification signal iff there is a state change.
        """
        if self._datahaschanged is None or stack().haschanged() != self._datahaschanged:
            # if _datahaschanged is None, then this is the first time we've changed data this session.
            # Otherwise, we only want to activate when there is a difference between the current and cached state
            self._datahaschanged = stack().haschanged()
            self.tablehaschanges.emit(self._datahaschanged)


    # def rowDataChanged(self, row):
    #     idx_start = self.index(row, 0)
    #     idx_end = self.index(row, self.columnCount())
    #
    #     # noinspection PyUnresolvedReferences
    #     self.dataChanged.emit(idx_start, idx_end)

    def loadData(self):
        self.beginResetModel()
        self._modifications.clear()
        self._datahaschanged = None
        stack().clear()
        # self.modified_rows = {}

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

    # def toggleEnabledState(self, row):
    #     mod = self.mod_entries[row]
    #     newmod = mod._replace(enabled=int(not mod.enabled))
    #
    #     # need_notify = self.onModDataEdit(row, mod, newmod)
    #     self.mod_entries[row] = newmod
    #
    #     self.rowDataChanged(row)
    #
    #     need_notify = self.checkModChange('enabled', mod, newmod)
    #     if need_notify is not None:
    #         self.tablehaschanges.emit(need_notify)

    ##===============================================
    ## Save and Revert
    ##===============================================

    # def revert(self):
    #     for cached_mod in self.modified_rows.values():
    #         original_row = cached_mod.ordinal - 1
    #         self.mod_entries[original_row] = cached_mod
    #         self.rowDataChanged(original_row)
    #
    #     self._finish_cleanup()

    # def save(self):
    #     to_save = [self.mod_entries[row] for row in self.modified_rows]
    #
    #     self.manager.saveUserEdits(to_save)
    #     self._finish_cleanup()
    #
    # def _finish_cleanup(self):
    #     self.modified_rows.clear()
    #     self.tablehaschanges.emit(False)

    def save(self):
        to_save = [self.mod_entries[row] for row in set(self._modifications)]

        self.manager.saveUserEdits(to_save)

        # for now, let's just reset the undo stack and consider this the new "start" point
        stack().savepoint()
        stack().clear()
        self._datahaschanged = None

        self.tablehaschanges.emit(False)

    def revert(self):
        while stack().canundo():
            # todo: this doesn't block signals...should it?
            stack().undo()



    ##===============================================
    ## Undo Management
    ##===============================================

    def undo(self):
        stack().undo()

    def redo(self):
        stack().redo()



    # def undoCallback(self, action, diff):
    #
    #     for case in [action.__name__.__eq__]:
    #         if case("shiftRows"):
    #             moddir = diff["directory"]
    #             old,new = diff["shift"]

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
        # self.setSelectionMode(QtWidgets.QAbstractItemView.ContiguousSelection)
        self.setObjectName("mod_table")
        grid.addWidget(self, 1, 0, 1, 5)

        # self.setModel(ModTableModel(parent=self, manager=self.manager))
        self.setModel(ModTable_TreeModel(parent=self, manager=self.manager))
        self.setColumnHidden(COL.DIRECTORY, True)
        h=self.header() #type:QHeaderView
        h.setStretchLastSection(False)
        h.setSectionResizeMode(COL.NAME, QHeaderView.Stretch)


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

    def saveChanges(self):
        self._model.save()

    def selectionChanged(self, selected, deselected):
        if len(self.selectedIndexes()) > 0:
            self.itemsSelected.emit()
        else:
            self.selectionCleared.emit()

        super().selectionChanged(selected, deselected)

    def onMoveModsUpAction(self, distance=1):
        rows = list(set([idx.row() for idx in self.selectedIndexes()]))
        if rows:
            print(rows, distance, self.rootIndex().data())
            self.LOGGER << "Moving rows {}-{} to row {}.".format(rows[0], rows[-1], rows[0] - distance)
            self._model.shiftRows(rows[0], rows[-1], rows[0] - distance, self.rootIndex())

        self.itemsMoved.emit(self.selectedIndexes(), self._model)

    def onMoveModsDownAction(self, distance=1):
        rows = list(set([idx.row() for idx in self.selectedIndexes()]))
        print(rows, distance, self.rootIndex().data())

        if rows:
            self.LOGGER << "Moving rows {}-{} to row {}.".format(rows[0], rows[-1], rows[0] + distance)
            self._model.shiftRows(rows[0], rows[-1], rows[0] + distance, self.rootIndex())

        self.itemsMoved.emit(self.selectedIndexes(), self._model)

    def undo(self):
        self._model.undo()
    def redo(self):
        self._model.redo()

if __name__ == '__main__':
    from skymodman.managers import ModManager