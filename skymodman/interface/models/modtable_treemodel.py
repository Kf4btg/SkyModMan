from functools import partial
import re

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QAbstractItemModel, QModelIndex, QMimeData

from skymodman.constants import (Column as COL, ModError)
from skymodman.log import withlogger


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
Qt_ForegroundRole = Qt.ForegroundRole
Qt_FontRole       = Qt.FontRole

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

col_to_attr = {
    COL_ORDER:     lambda m: m.ordinal,
    COL_ENABLED:   lambda m: m.enabled,
    COL_NAME:      lambda m: m.name,
    COL.DIRECTORY: lambda m: m.directory,
    COL_MODID:     lambda m: m.modid,
    COL_VERSION:   lambda m: m.version,
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

# base set of flags for table cells
_base_flags = Qt_ItemIsEnabled | Qt_ItemIsSelectable | \
                 Qt_ItemIsDragEnabled | Qt_ItemIsDropEnabled
# </editor-fold>



@withlogger
class ModTable_TreeModel(QAbstractItemModel):

    # noinspection PyArgumentList
    tablehaschanges = pyqtSignal(bool)

    # let view know selection may have moved
    # noinspection PyArgumentList
    # notifyViewRowsMoved = pyqtSignal()
    # noinspection PyArgumentList
    hideErrorColumn = pyqtSignal(bool)
    # noinspection PyArgumentList
    errorsAnalyzed = pyqtSignal(int)

    # noinspection PyArgumentList
    newEntryAdded = pyqtSignal()
    """
    Signals that an entirely new entry has been entered into the table.
    """

    # noinspection PyArgumentList
    rowsDropped = pyqtSignal(int, int, int)
    """emitted when a user drags a row or section of rows from
    one part of the list to another. The parameters are the first
    row of the dragged section, the last row of the dragged section,
    and the row of the item that they dropped the section on."""

    def __init__(self, parent, manager, **kwargs):
        """
        """
        # noinspection PyArgumentList
        super().__init__(parent, **kwargs)
        self._parent = parent

        self.Manager = manager
        """:type: skymodman.managers.modmanager.ModManager"""

        # initialize as empty list so our rowCount() method doesn't crash
        self.mods = []
        """:type: skymodman.types.modcollection.ModCollection"""
        self.errors = {} # type: dict [str, int]
        # self.errtypes = ModError.NONE

        # self.vheader_field = COL_ORDER

        ## to speed up drag-n-drop operations, track the start and
        ## end of the dragged range as ints (so we don't need to split()
        ## and int() the mimedata multiple times per second)
        self._drag_start = -1
        self._drag_end = -1

        # the 'disabled' text color
        self.disabled_foreground = QtGui.QBrush(
            QtGui.QPalette().color(QtGui.QPalette.Disabled,
                                   QtGui.QPalette.Text))

        # italic font for unmanaged mods
        self.unmanaged_font = QtGui.QFont()
        self.unmanaged_font.setItalic(True)

        self.LOGGER << "init ModTable_TreeModel"

    ##===============================================
    ## PROPERTIES
    ##===============================================

    def __getitem__(self, row):
        """
        Allows list-like access to the backing collection of ModEntries.

        :param int row: Row number of the mod from the mod table
        :return: QModEntry instance representing the mod in that row. If `row` is out of bounds or cannot be implicitly converted to an int, return None.
        """
        try:
            return self.mods[row]
            # return self.mod_entries[row]
        except (TypeError, IndexError):
            return None

    def get_mod_for_index(self, index):
        """
        Return the ModEntry for the row in which `index` appears.

        :param QModelIndex index:
        :return:
        """
        if index.isValid(): return self.mods[index.row()]

    def mod_missing(self, mod_entry):
        """
        Return whether the specified mod is currently in an error state.

        :param QModEntry mod_entry:
        :return: True iff the mod has the ModError.DIR_NOT_FOUND error
        """
        try:
            return self.errors[mod_entry.directory] == ModError.DIR_NOT_FOUND
        except KeyError:
            # mod has no errors
            return False

    ##===============================================
    ## Required Qt Abstract Method Overrides
    ##===============================================

    def rowCount(self, *args, **kwargs) -> int:
        return len(self.mods)

    def columnCount(self, *args, **kwargs) -> int:
        return len(col2Header)

    def parent(self, child_index=None):
        # There are no children (yet...) so I guess this should
        # always return invalid??
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
            return self.createIndex(row, col, self.mods[row])
        except IndexError:
            return QModelIndex()


    ## Data Provider
    ##===============================================
    def data(self, index, role=Qt_DisplayRole):
        col = index.column()

        mod = self.mods[index.row()]

        # now that the ordinal is more loosely coupled to the
        # mod, we can actually return the value specifically for that
        # mod, potentially allowing filtering/categories/other fun
        # stuff without messing up the 'order' column
        if col == COL_ORDER:
            # ???: which of the following two is better? mod.ordinal
            # is a property which basically does the exact same
            # thing as the other statement...but it feels more
            # intuitive, as if the mod just knows where it is in line.
            # It might be slightly less performant, though...i guess
            # we'll reconsider if it becomes an issue

            # return self.mods.index(mod.directory) if role == Qt_DisplayRole else None
            return mod.ordinal if role == Qt_DisplayRole else None

        # In lieu of a rant about delegates, I'll just note here that
        # I never could get the font color to change using a custom
        # delegate, but returning this here works fine:
        if role == Qt_ForegroundRole and not mod.enabled:
            return self.disabled_foreground

        # show unmanaged mods in italic font
        if role == Qt_FontRole and not mod.managed:
            return self.unmanaged_font

        # handle errors
        if col == COL_ERRORS:
            try:
                err_type = self.errors[mod.directory]
            except KeyError:
                # no error for this mod
                return

            if err_type & ModError.DIR_NOT_FOUND:
                # noinspection PyArgumentList,PyTypeChecker
                return (QtGui.QIcon.fromTheme('dialog-error')
                            if role == Qt_DecorationRole
                        else "Mod data not found."
                            if role == Qt_ToolTipRole
                        else None)

            if err_type & ModError.MOD_NOT_LISTED:
                # noinspection PyArgumentList,PyTypeChecker
                return (QtGui.QIcon.fromTheme('dialog-warning')
                            if role == Qt_DecorationRole
                        else "This mod was found in the mods "
                             "directory but has not previously "
                             "been seen my this profile. Be sure "
                             "that it is either set up correctly "
                             "or disabled before running any tools."
                            if role == Qt_ToolTipRole
                        else None)

        elif col == COL_ENABLED:

            ## although our delegate catches the editor event to know
            # when the user clicked on the checkbox, we never actually
            # open the editor (we just hijack the event to wrap
            # a setData() call), so we don't need to handle edit_role

            if role == Qt_CheckStateRole:
                return Qt_Checked if mod.enabled else Qt_Unchecked

        # for every other column, return the stored value as the
        # display role
        elif role == Qt_DisplayRole:
            return col_to_attr[col](mod)
            # return getattr(mod, col2field[col])
        elif col == COL_NAME:
            if role == Qt_EditRole:
                return mod.name
            if role == Qt_ToolTipRole:
                return mod.directory

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """

        :param section:
        :param orientation:
        :param role:
        :return: column header for the specified section (column) number.
        """
        if role == Qt_DisplayRole and orientation == Qt.Horizontal:
                return col2Header[section]

            # the vertical header doesn't work, anyway...
            # else:  # vertical header
            #     return self.mods.index()
            #     return self.mod_entries[section].ordinal

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
            # drop enabled allows dropping "before" rows and also
            # after the final row
            return Qt_ItemIsEnabled | Qt_ItemIsDropEnabled

        col = index.column()

        if col == COL_ENABLED:
            return _base_flags | Qt_ItemIsEditable
            # return _base_flags | Qt_ItemIsUserCheckable

        if col == COL_NAME:
            return _base_flags | Qt_ItemIsEditable

        return _base_flags

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

        # compile for performance
        regex = re.compile(regex, re.IGNORECASE)

        # setup function to compare a mod's name with the regex
        def findstr(modentry):
            return regex.search(modentry.name)

        # and set that function as the first arg for the method that
        # searches parts of the list
        searcher = partial(self._search_slice, findstr)

        try:
            # search backwards if dir<0
            next_result = searcher(
                start=current_row-1,
                step=-1) if reverse else searcher(
                start=current_row+1)

        except StopIteration:
            # we've reached one end of the list, so wrap search
            # to the opposite end and continue until we either find a
            # match or return to the starting point.
            try:
                next_result = searcher(
                    end=current_row-1,
                    step=-1) if reverse else searcher(
                    end=current_row + 1)
            except StopIteration:
                return QModelIndex()

        if next_result:
            return self.createIndex(next_result.ordinal, COL_NAME)

        # i don't think we'll ever reach here...
        # but better safe than sorry, I guess
        self.LOGGER << "<--End of mod table search"
        return QModelIndex()

    def _search_slice(self, match_func, start=None, end=None, step=1):
        if start is None:
            if end is None:
                return next(filter(match_func, self.mods[::step]))
            return next(filter(match_func, self.mods[:end:step]))
        elif end is None:
            return next(filter(match_func, self.mods[start::step]))
        return next(filter(match_func, self.mods[start:end:step]))

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

        # now we have a custom delegate's editorEvent to catch when the
        # user clicks on the checkbox, so we use EditRole instead
        if role == Qt_EditRole:
            if index.column() == COL_ENABLED:
                row = index.row()
                # value is passed as bool, but we store as int
                # TODO: actually, if we don't store the enabled status in the database any more, there's really no point in using ints instead of bools...

                self.mods[row].enabled = int(value)

                # since we change the appearance of the text across
                # the entire row when 'enabled' is changed,
                # emit the data changed signal for each cell in row
                self.dataChanged.emit(self.index(row, 0),
                                      self.index(row,
                                                 self.columnCount() - 1)
                                      )
                return True

            elif index.column() == COL_NAME:
                # assume name is valid (view does check)

                self.mods[index.row()].name = value

                self.dataChanged.emit(index, index)

                return True
        else:
            return super().setData(index, value, role)

        # if role was edit, but column was not
        # enabled/name, just ret false
        return False

    ##===============================================
    ## Modifying Row Position
    ##===============================================

    def prepare_move(self, src_row, dest_row, count):
        """
        Prepare and return all the required parameters to fully execute
        a 'change-order' operation--both forward and in reverse--in
        order to support the Undo system. A LOT of information is
        returned, but that's just to make sure that every piece of
        information is explicitly specified. Zero additional calculations
        should be required after this step.

        Pass the returned values to do_move() of this model to actually
        perform the move.

        :param int src_row:
        :param int dest_row:
        :param int count:

        :return: A 10-tuple. The first two values are the "first" and
            "last" rows that define the full range of indices in the
             collection that will affected by this move. The next 4
             values are used in the forward operation, and the final
             4 for the reverse operation.

            "first", "last", and "split" (or its counterpart "rev_split")
            will become the arguments for collection.do_move(). Everything
            else will be a parameter for beginMoveRows()

            In full and in order:
                0) first
                1) last

                2) split
                3) srcFirst
                4) srcLast
                5) destinationChild

                6) rev_split
                7) rev_srcFirst
                8) rev_srcLast
                9) rev_destinationChild

        """
        first, last, split = self.mods.prepare_move(src_row, dest_row, count)
        rsplit = last - first - split # split param for reverse-shift

        ## get args for beginMoveRows:
        ## C++ signature:
        # bool QAbstractItemModel::beginMoveRows(
        #   const QModelIndex &sourceParent,
        #   int sourceFirst,
        #   int sourceLast,
        #   const QModelIndex &destinationParent,
        #   int destinationChild)

        # note:: moving down means "move to row BEFORE destinationChild",
        # so e.g. moving row 2 down by 1 to row 3 would mean
        # ``destinationChild=4``. Moreover, destinationChild is the row
        # that will come after the ENTIRE block of moved rows...so,
        # moving rows 2 and 3 down by 2 (to become rows 4 and 5)
        # requires ``destinationChild=6``
        #
        # Moving up is more sensible, where
        # moving row 3 up by 1 to row 2 means ``destinationChild=2``

        # destinationChild depends on direction of movement
        if dest_row < src_row: #UP
            destinationChild, rdestinationChild = first, last
            srcLast, rsrcLast=last-1,first+rsplit-1
            rsrcFirst=first
        else: #Down
            destinationChild, rdestinationChild = last, first
            srcLast, rsrcLast = first + split - 1, last - 1
            rsrcFirst = dest_row

        # bmr_args = (parent, src_row, srcLast, parent, destinationChild)
        # rbmr_args = (parent, rsrcFirst, rsrcLast, parent, rdestinationChild)

        return (first, last, # always the same
                # args for forward (redo)
                split, src_row, srcLast, destinationChild,
                # args for reverse (undo)
                rsplit, rsrcFirst, rsrcLast, rdestinationChild)


    def do_move(self, first, last, split,
                srcFirst, srcLast, destinationChild,
                parent=QModelIndex()):
        """
        Performs execution of a move operation where all the
        variables have been pre-calculated.

        The first three parameters (`first`, `last`, and `split`) are
        used by the move() operation in the modcollection. The
        remaining arguments are required by the
        QAbstractItemModel.beginMoveRows() method. There's likely a lot
        of overlap, but because just _precisely_ what that overlap is
        depends on a LOT of factors, so it's best to precalculate
        everything beforehand and pass them all individually.

        :param int first: first row of entire affected block
        :param int last: last row of entire affected block (actually,
            the row just beyond it)
        :param int split: the offset from `first` that defines the
            divider between the 'shifted' and the 'shiftee' blocks...
            i.e. the point where the selection ends and the rows
            that have to be moved to accomodate the movement of the
            selection begin

        :param int srcFirst: the srcFirst parameter for beginMoveRows
        :param int srcLast: the srcLast param for beginMoveRows
        :param int destinationChild: the destinationChild param for
            beginMoveRows
        :param QModelIndex parent: the QModelIndex in the TreeModel
            that contains all these rows; we only worry about flat
            movements here (within the same parent), and this is
            very likely to be the invisible root Item of the view.
        """

        self.beginMoveRows(parent, srcFirst, srcLast,
                           parent, destinationChild)

        self.mods.exec_move(first, last, split)

        self.endMoveRows()

    ##===============================================
    ## Getting data from disk into model
    ##===============================================

    def load_data(self):
        """
        Load fresh data and reset everything. Called when first loaded
        and when something major changes, like the active profile.
        """
        self.beginResetModel()

        # we use the same collection as the rest of the application,
        # so we shouldn't modify it (unless specifically told to do so
        # by user interaction, of course)
        self.mods = self.Manager.modcollection

        # see if we currently have any errors
        self.check_mod_errors()

        self.endResetModel()
        self.tablehaschanges.emit(False)

    def check_mod_errors(self):
        """
        Check which mods, if any, encountered errors during load and
        show or hide the Errors column appropriately.
        """

        self.errors = self.Manager.mod_errors

        # Hide or show the Errors column based on whether any of the mods
        # have a non-zero error type
        # let rest of app know what we have; this should show/hide
        # the Errors column as needed
        self.errorsAnalyzed.emit(self.Manager.mod_error_types)

    def reload_errors_only(self):
        self.beginResetModel()
        self.check_mod_errors()
        self.endResetModel()

    ##===============================================
    ## Save & Revert
    ##===============================================

    def save(self):
        """
        Save all changes made to the mod table to disk
        """

        # no need to mess w/ the whole 'which rows were modifed' thing,
        # since there's no need to update the database anymore;
        # just write the current state of the collection to disk
        self.Manager.save_mod_info()

    def missing_mods(self):
        """Yield all the mods in the model that are currently showing
        the DIR_NOT_FOUND error type."""

        yield from (m for m in self.mods if self.mod_missing(m))

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

        # save these as ints to speed up canDropMimeData
        self._drag_start = rows[0]
        self._drag_end = rows[-1]

        mimedata = QMimeData()
        mimedata.setText("{0._drag_start} {0._drag_end}".format(self))
        return mimedata

    def canDropMimeData(self, data, action, row, column, parent):
        """
        don't allow dropping selection on itself
        """

        return super().canDropMimeData(
            data, action, row, column, parent) and (
            row <= self._drag_start or row >= self._drag_end)

    def dropMimeData(self, data, action, row, column, parent):
        """

        :param QMimeData data: contains a string that is 2 ints separated by whitespace, e.g.:  '4 8' This string corresponds to the first and last row in the block of rows being dragged
        :param Qt.DropAction action:
        :param int row:
        :param int column:
        :param QModelIndex parent: The hovered item (drop target)
        :return: True unless drop would place selection in same spot
        """

        # from the qt docs: "When row and column are -1 it means that
        # the dropped data should be considered as dropped directly
        # on parent. Usually this will mean appending the data as
        # child items of parent. If row and column are greater than
        # or equal zero, it means that the drop occurred just before
        # the specified row and column in the specified parent."


        # split the text (e.g. "3 3", "5 12", etc)
        start, end = [int(r) for r in data.text().split()]

        if row < 0:
            # "dropped directly on parent"

            if not parent.isValid(): # dropped in empty space
                # -- place after final item
                self.rowsDropped.emit(start, end, self.rowCount())
            elif start-1 != parent.row():
                # make sure this wouldn't place the selection back
                # in the exact same spot

                # -- place below parent
                self.rowsDropped.emit(start, end, parent.row() + 1)
            else:
                return False
        else:
            # "occurred just before the specified row and column"

            # parent is always invalid in this case, but "row" is just
            # before what would appear to be the parent
            self.rowsDropped.emit(start, end, row)

        return True

    ##===============================================
    ## Adding and Removing Rows/Columns (may need later)
    ##===============================================

    # this is not an override of removeRows() because that screws up
    # our drag-and-drop implementation...even though we don't call
    # super() during the dropMimeData method...
    def remove_rows(self, row, count, parent=QModelIndex()):
        """
        Remove mod[s] (row[s]) from the model.

        :param int row:
        :param int count:
        :param QModelIndex parent:
        :return:
        """

        end = row+count-1

        self.beginRemoveRows(parent, row, end)

        self.Manager.Collector.delete_items(row, count)

        self.endRemoveRows()

        return True

    def insert_entries(self, row, entries, errors=None,
                       parent=QModelIndex()):
        """
        Add the given mod(s) to the mod collection at position `row`

        :param row:
        :param entries:
        :param parent:
        :param errors: if the error types for all/some of the entries
            are known beforehand (e.g., when undoing the removal of a
            mod w/ an error), pass a {mod_key: ModError} dict to assign
            those error types upon insertion.
        """
        # don't allow out-of-bounds insertions
        row = min(row, len(self.mods))

        end = row + len(entries) - 1

        self.beginInsertRows(parent, row, end)

        self.Manager.Collector.insert_items(row, entries, errors)

        self.endInsertRows()

    def add_mod(self, entry):
        """Add an entirely new Mod to the table"""

        self.insert_entries(len(self.mods), [entry])

        self.newEntryAdded.emit()



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

