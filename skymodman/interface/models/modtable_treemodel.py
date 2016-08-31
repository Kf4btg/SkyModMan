from functools import partial
from collections import deque
import re

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QAbstractItemModel, QModelIndex, QMimeData

from skymodman.interface.typedefs import QModEntry
from skymodman.managers import modmanager
from skymodman.constants import (Column as COL, ModError)
from skymodman.utils import withlogger

# sometimes...the import system makes me very angry
from skymodman.interface.qundo.commands import (
    change_mod_attribute,
    shift_rows,
    remove_rows,
    clear_missing_mods
)

Manager = None

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
# Qt_Unchecked = Qt.Unchecked

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



@withlogger
class ModTable_TreeModel(QAbstractItemModel):

    tablehaschanges = pyqtSignal(bool)

    # let view know selection may have moved
    notifyViewRowsMoved = pyqtSignal()

    hideErrorColumn = pyqtSignal(bool)

    errorsAnalyzed = pyqtSignal(int)

    def __init__(self, parent, **kwargs):
        """
        """
        super().__init__(**kwargs)
        self._parent = parent

        global Manager
        Manager = modmanager.Manager()

        self.mod_entries = [] #type: list [QModEntry]

        self.vheader_field = COL_ORDER

        ## to speed up drag-n-drop operations, track the start and
        ## end of the dragged range as ints (so we don't need to split()
        ## and int() the mimedata multiple times per second)
        self._drag_start = -1
        self._drag_end = -1


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

        self.disabled_foreground = QtGui.QBrush(
            QtGui.QPalette().color(QtGui.QPalette.Disabled,
                                   QtGui.QPalette.Text))

        self.LOGGER << "init ModTable_TreeModel"

    ##===============================================
    ## PROPERTIES
    ##===============================================

    # @property
    # def is_dirty(self) -> bool:
    #     return len(self._modifications) > 0

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

    def get_mod_for_index(self, index):
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
        return mod_entry.error == ModError.DIR_NOT_FOUND

    def mark_modified(self, iterable):
        """
        Add the items from `iterable` to the collection of modified rows.

        :param iterable: an iterable collection of ints. The values must
            all be valid indices in the model's list of mods
        """
        # self.LOGGER << iterable
        self._modifications.extend(iterable)

    def unmark_modified(self, count):
        """
        Remove the `count` most recent additions to the modifications
        collection

        :param int count:
        :return:
        """
        # self.LOGGER << count
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
    def data(self, index, role=Qt_DisplayRole):
        col = index.column()

        # just display the row number in the "order" column.
        # this allows us to manipulate the ordinal number a bit more
        # freely behind the scenes
        if col == COL_ORDER:
            return index.row() + 1 if role == Qt_DisplayRole else None

        mod = self.mod_entries[index.row()]

        # I've heard it a thousand times from a thousand people:
        # "Don't mix your data provider with styling information!"
        # Apparently that's amateur and The Wrong Way to do it.
        # But here's the thing. I tried it The Right Way, and, besides
        # being supremely over-complicated for my purposes (I just want
        # to change the text color!), it never, ever worked correctly.
        # So it involves a custom item delegate--no problem, done.
        # Within that delegate I was able to change the font style, font
        # weight, and some other things just fine. But the text color?
        # No, to get it to look exactly like everything else but JUST
        # IN A DIFFERENT COLOR would require re-implementing almost
        # the entire low-level painting code. Which is stupid.

        # But this is simple. And works. You can take your Right Way
        # and shove it.
        if role == Qt.ForegroundRole and not mod.enabled:
            # TODO: change appearance of "unmanaged-mods". This will of course require that we first start tracking unmanaged mods...
            return self.disabled_foreground

        # handle errors first
        if col == COL_ERRORS:
            if not mod.error: return

            if mod.error & ModError.DIR_NOT_FOUND:
                # noinspection PyArgumentList,PyTypeChecker
                return (QtGui.QIcon.fromTheme('dialog-error')
                            if role == Qt_DecorationRole
                        else "Mod data not found."
                            if role == Qt_ToolTipRole
                        else None)

            if mod.error & ModError.MOD_NOT_LISTED:
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
            return mod.checkState if role == Qt_CheckStateRole else None

        # for every other column, return the stored value as the
        # display role
        elif role == Qt_DisplayRole:
            return getattr(mod, col2field[col])
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
        if role == Qt_DisplayRole:

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
            next_result = searcher(start=current_row-1, step=-1) \
                        if reverse \
                        else searcher(start=current_row+1)

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

                self._push_command(change_mod_attribute.cmd(
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
                # remove trailing/leading space
                new_name = value.strip()
                # if unchanged or blank, don't update
                if new_name in [mod.name, ""]: return False

                # callbacks for changing (1) or reverting (2)
                cb1 = partial(self._post_change_mod_attr, index, row)
                cb2 = partial(self._post_change_mod_attr, index)
                self._push_command(change_mod_attribute.cmd(
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

    def shift_rows(self, start_row, end_row, move_to_row, parent=QModelIndex(), undotext="Reorder Mods"):
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

        scmd = shift_rows.cmd(
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

    def load_data(self):
        """
        Load fresh data and reset everything. Called when first loaded
        and when something major changes, like the active profile.
        """
        self.beginResetModel()
        self._modifications.clear()

        self.mod_entries = [QModEntry(**d) for d
                            in Manager.allmodinfo()]

        self.check_mod_errors()

        self.endResetModel()
        self.tablehaschanges.emit(False)

    def check_mod_errors(self, query_db = False):
        """
        Check which mods, if any, encountered errors during load and
        show or hide the Errors column appropriately.

        If query_db is True, ask the manager to query the database and
        return a mapping of all mods (by directory name) to the value of
        their error-type (ModError.* -- hopefully NONE). Then go through
        the model's list of modentries and update the error value of
        each to the value found in the mapping. After this is done,
        hide or show the Errors column based on whether any of the mods
        have a non-zero error type
        """

        # reset
        err_types = ModError.NONE

        if query_db:
            # if we need to query the database to refresh the errors,
            # do that here:
            errors = Manager.get_errors()

            # update the "error" field of each modentry
            for m in self.mod_entries:
                m.error = errors[m.directory]
                if m.error:
                    err_types |= m.error
        else:
            # otherwise, we're just checking for any errors in any mod
            for m in self.mod_entries:
                if m.error:
                    err_types |= m.error

        self.errorsAnalyzed.emit(err_types)

    def reload_errors_only(self):
        self.beginResetModel()
        self.check_mod_errors(True)
        self.endResetModel()

    ##===============================================
    ## Save & Revert
    ##===============================================

    def save(self):
        """
        Save all changes made to the mod table to disk
        """

        modified = set(self._modifications)
        to_save = []

        # first, update ordinals of modified entries to reflect their
        # (possibly) new position
        for row in modified:
            self.mod_entries[row].ordinal = row
            to_save.append(self.mod_entries[row])

        # print(to_save)

        # to_save = [self.mod_entries[row]
        #            for row in set(self._modifications)]

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

        def post_op():
            self.check_mod_errors()
            self.endResetModel()

        self._push_command(
            clear_missing_mods.cmd(
                self,
                pre_redo_callback=self.beginResetModel,
                pre_undo_callback=self.beginResetModel,
                post_redo_callback=post_op,
                post_undo_callback=post_op,
            )
        )

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

        if super().canDropMimeData(data, action, row, column, parent):
            return row <= self._drag_start or row >= self._drag_end

    def dropMimeData(self, data, action, row, column, parent):
        """

        :param QMimeData data: contains a string that is 2 ints separated by whitespace, e.g.:  '4 8' This string corresponds to the first and last row in the block of rows being dragged
        :param Qt.DropAction action:
        :param int row: ignored; always -1
        :param int column: ignored; always -1
        :param QModelIndex parent: The hovered item (drop target)
        :return: True so long as the parent is valid, otherwise False
        """

        if not parent.isValid():
            return False
        # p = parent.internalPointer() #type: QModEntry

        dest = parent.row()

        start, end = [int(r) for r in data.text().split()]

        # print("dropMimeData: dest =", dest, ", start =", start, ", end =", end)

        self.shift_rows(start, end, dest)
        return True

    ##===============================================
    ## Adding and Removing Rows/Columns (may need later)
    ##===============================================

    # this is not an override of removeRows() because that screws up
    # our drag-and-drop implementation...even though we don't call
    # super() during the dropMimeData method...
    def remove_rows(self, row, count, parent=QModelIndex()):
        """
        Remove mod[s] (row[s]) from the model. Undoable action

        :param int row:
        :param int count:
        :param QModelIndex parent:
        :return:
        """

        end = row+count-1

        self._push_command(
            remove_rows.cmd(
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

