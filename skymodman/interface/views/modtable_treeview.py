from functools import partial

from PyQt5 import QtWidgets, QtCore

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QEvent, QItemSelectionModel as qISM
# , pyqtProperty

from skymodman.constants import Column, ModError
from skymodman.log import withlogger

# from skymodman.interface.models import ModTable_TreeModel
from skymodman.interface.ui_utils import undomacro, blocked_signals
from skymodman.interface.qundo.commands.generic import UndoCommand
from skymodman.interface.qundo.commands import clear_missing_mods

qmenu = QtWidgets.QMenu

Qt_Checked   = Qt.Checked
Qt_Unchecked = Qt.Unchecked
Qt_CheckStateRole = Qt.CheckStateRole
PositionAtCenter = QtWidgets.QAbstractItemView.PositionAtCenter

COL_ENABLED = Column.ENABLED.value


@withlogger
class ModTable_TreeView(QtWidgets.QTreeView):

    # noinspection PyArgumentList
    enableModActions = pyqtSignal(bool)

    # noinspection PyArgumentList
    enableSearchActions = pyqtSignal(bool)
    """emitted to enable/disable the find-next/previous buttons"""

    # noinspection PyArgumentList
    canMoveItems = pyqtSignal(bool, bool)

    # noinspection PyArgumentList
    setStatusMessage = pyqtSignal(str)
    """emitted when the table would like to update the main window status bar"""

    # NTS: this could likely be more generic; it's meant to inform the
    # main window to reanalyze which actions are active (in particular,
    # the clear_missing_mods action)

    # noinspection PyArgumentList
    errorsChanged = pyqtSignal(int)

    def __init__(self, parent, *args, **kwargs):
        # noinspection PyArgumentList
        super().__init__(parent, *args, **kwargs)

        self._model  = None
        """:type: skymodman.interface.models.ModTable_TreeModel"""

        self._selection_model = None # type: qISM
        # self.LOGGER << "Init ModTable_TreeView"

        # debugging: print modentry on click
        # self.clicked.connect(lambda i: print(i.internalPointer()))

        # placeholder for the associated search box and animation
        self._searchbox = None
        """:type: QtWidgets.QLineEdit"""
        self.animate_show_search = None
        """:type: QtCore.QPropertyAnimation"""

        # a bitwise-OR combination of the types of errors currently
        # found in the table
        self._err_types = ModError.NONE

        # create an undo stack for the mods tab
        self._undo_stack = QtWidgets.QUndoStack()

    @property
    def undo_stack(self):
        return self._undo_stack

    @property
    def errors_present(self):
        return self._err_types

    @property
    def has_selection(self):
        try:
            return self._selection_model.hasSelection()
        except AttributeError:
            return False

    @property
    def item_count(self):
        try:
            return self._model.rowCount()
        except AttributeError:
            return 0

    @property
    def search_text(self):
        try:
            return self._searchbox.text()
        except AttributeError:
            # searchbox not assigned yet
            return ""

    ##=============================================
    ## Setup
    ##=============================================

    def setupui(self, search_box):
        """Setup searchbox functionality"""
        self._searchbox = search_box

        # setup the animation to show/hide the search bar
        self.animate_show_search = QtCore.QPropertyAnimation(
            self._searchbox, b"maximumWidth")
        # how long the animation takes
        # NTS: maybe don't hardcode this value?
        self.animate_show_search.setDuration(300)
        # hide searchbox initially
        self._searchbox.setMaximumWidth(0)

        self._searchbox.textChanged.connect(
            self._clear_searchbox_style)

        # i prefer searching only when i'm ready
        self._searchbox.returnPressed.connect(
            self._on_searchbox_return)

    def reset_view(self):
        """Clears the search box & undo stack, and reloads the table data"""

        # clear search box
        self._searchbox.clear()

        # reset undo stack
        self.undo_stack.clear()

        # (re)load (new?) data
        self.load_data()

    ##=============================================
    ## Qt Overrides
    ##=============================================

    def setModel(self, model):
        super().setModel(model)
        # keep a local reference to the selection model
        self._selection_model = self.selectionModel()
        self._model = model

        # called from model's do_move() method
        self._model.rowsMoved.connect(self.on_rows_moved)

        # perform a reorder operation when the user drags and drops
        # rows around:
        self._model.rowsDropped.connect(self.on_rows_dropped)

        # only show error col if there are errors
        self._model.errorsAnalyzed.connect(self._analyze_errors)

        # when a brand new mod is added, we'll have to save the table
        # and drop the undo stack
        self._model.newEntryAdded.connect(self.on_new_mod)

        ## some final UI adjustments ##

        # hide directory column by default
        self.setColumnHidden(Column.DIRECTORY, True)

        # stretch the Name section
        self.header().setSectionResizeMode(Column.NAME,
                                           QtWidgets.QHeaderView.Stretch)


        ## set custom delegates to wrap setData calls in undo-cmds

        # set a custom delegate on the enabled row
        self.setItemDelegateForColumn(COL_ENABLED, CheckBoxDelegate(self))

        # ...and on the name row
        self.setItemDelegateForColumn(Column.NAME, LineEditDelegate(self))

    def selectionChanged(self, selected=None, deselected=None):

        # enable/disable the button box
        if self.selectionModel().hasSelection():

            self.enableModActions.emit(True)
            self._selection_moved()  # check for disable up/down buttons
        else:
            self.enableModActions.emit(False)

        super().selectionChanged(selected, deselected)

    def dragEnterEvent(self, event):
        """ Qt-override.
        Implementation needed for enabling drag and drop within the view.

        :param QDragEnterEvent event:
        """
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
    #
    # ## XXX: What's the point of this??
    # def dragMoveEvent(self, event):
    #     super().dragMoveEvent(event)

    def contextMenuEvent(self, event):
        """

        :param QContextMenuEvent event:
        """

        mw = self.window()  # mainwindow

        menu = qmenu(self)
        menu.addActions([mw.action_toggle_mod,
                         mw.action_uninstall_mod,
                         mw.action_show_in_file_manager
                         ])

        # only show if error column visible and
        # at least one mod has DIR_NOT_FOUND error
        if (not self.isColumnHidden(Column.ERRORS)
            and bool(self._err_types & ModError.DIR_NOT_FOUND)):
            menu.addAction(mw.action_clear_missing)

        menu.exec_(event.globalPos())

    ##=============================================
    ## Searching
    ## <editor-fold desc="...">
    ##=============================================

    @pyqtSlot()
    def toggle_search_box(self):
        """
        Show or hide the search box based on its current state.
        """
        # 0=hidden, 1=shown
        state = 0 if self._searchbox.width() > 0 else 1

        # ref to QAnimationProperty
        an = self.animate_show_search

        # animate expansion from 0px -> 300px width when showing;
        # animate collapse from 300->0 when hiding
        an.setStartValue([300,0][state])
        an.setEndValue([0,300][state])
        an.start()

        # also, focus the text field if we're showing it
        if state:
            self._searchbox.setFocus()
        else:
            # or clear the focus and styling if we're hiding
            self._searchbox.clearFocus()
            self._searchbox.clear()

    def clear_search(self):
        """simply clears the search box"""
        self._searchbox.clear()

    def search(self, text, direction=1):
        """
        Query the model for the row containing the given text;
        if it is found, scroll to and select the row.

        :param str text:
        :param int direction: positive for up, negative for down
        :return:
        """

        cindex = self.currentIndex()

        result = self._model.search(text, cindex, direction)

        if result.isValid():
            if result == cindex:
                # this means that we're sitting on the only
                # row that matches the search; return None
                # to differentiate it.
                return None

            self._selection_model.select(result,
                                         qISM.ClearAndSelect)
            self.scrollTo(result, PositionAtCenter)
            self.setCurrentIndex(result)
            return True
        return False

    def _on_searchbox_return(self):
        """called when the user hits return in the search box"""
        self.enableSearchActions.emit(bool(self.search_text))
        self.on_table_search()

    def on_table_search(self, direction=1):
        """
        Tell the view to search for 'text'; depending on success, we
        will change the appearance of the search text and the status
        bar message
        """

        text = self.search_text

        if text:
            found = self.search(text, direction)

            if not found:
                if found is None:
                    # this means we DID find the text, but it was the
                    # same row that we started on
                    # TODO: don't hardcode these colors
                    self._searchbox.setStyleSheet(
                        'QLineEdit { color: gray }')
                    self.setStatusMessage.emit(
                        "No more results found")
                else:
                    # found was False
                    self._searchbox.setStyleSheet(
                        'QLineEdit { color: tomato }')
                    self.setStatusMessage.emit("No results found")
                return

        # text was found or was '': reset style sheet if one is present
        self._clear_searchbox_style()

    @pyqtSlot()
    def _clear_searchbox_style(self):
        if self._searchbox.styleSheet():
            self._searchbox.setStyleSheet('')
            self.setStatusMessage.emit('')

    #</editor-fold>

    ##=============================================
    ## "Public Slots"
    ##=============================================

    def load_data(self):
        """
        Load data from disk into the model and adjust the table for the
        new content.
        """
        self._model.load_data()

        for i in range(self._model.columnCount()):
            self.resizeColumnToContents(i)

        # set the current index to the first item in the
        # table WITHOUT selecting it; this allows searching
        # to work properly without first clicking on an item
        self._selection_model.setCurrentIndex(
            self._model.index(0),
            qISM.NoUpdate)

    def toggle_selection_checkstate(self):
        """
        Toggle the enabled-state of the currently selected mod(s)
        """
        # to keep things simple, we base the first toggle off of the
        # enabled state of the current index. E.g., even if it's the
        # only enabled mod in the selection, the first toggle will
        # still be a disable command. It's rough, but the user may
        # need to hit 'Space' **twice** to achieve their goal.  Might
        # lose a lot of people over this.

        current_is_enabled = bool(self.currentIndex().internalPointer().enabled)
        sel = self.selectedIndexes()

        # _text = ("Enable", "Disable")[currstate]
        _text = "Disable" if current_is_enabled else "Enable"
        # _checked = (Qt_Checked, Qt_Unchecked)[currstate]

        # splitting these up may help with some undo weirdness...

        if len(sel) > self._model.columnCount():
            # multiple rows selected

            # bind them all into one undo-action
            with undomacro(self.undo_stack, f"{_text} Mods"):

                # only use the indexes for the "enabled" column
                for index in (idx for idx in sel if idx.column() == COL_ENABLED):
                    is_enabled = bool(index.internalPointer().enabled)

                    # push each command to the stack (within the macro)
                    self._undo_stack.push(UndoCommand(
                        redo=partial(self._model.setData, index,
                                     # change them to opposite of curr.
                                     # index's enabled state
                                     not current_is_enabled, Qt.EditRole),
                        undo=partial(self._model.setData, index,
                                     # but return to original state of
                                     # this specific index
                                     is_enabled, Qt.EditRole)))
        else:
            # only one row selected

            # pull the right index out of it
            index = sel[COL_ENABLED]

            # push the command to the stack
            self._undo_stack.push(UndoCommand(
                text=f"{_text} Mod",
                redo=partial(self._model.setData, index,
                             not current_is_enabled, Qt.EditRole),
                undo=partial(self._model.setData, index,
                             current_is_enabled, Qt.EditRole)))

    def clear_missing_mods(self):
        """
         Remove all mods that are marked with the NOT FOUND error
         from the current profile's modlist

         :return:
         """

        # but first make sure there actually ARE any:
        if self._err_types & ModError.DIR_NOT_FOUND:

            # now simply push the a new clear-missing-mods undocmd
            # and let it take care of all the details
            self._undo_stack.push(
                clear_missing_mods.cmd(self._model))

    def revert_changes(self):
        """
        Revert the state of the table to that of the last save-point
        """
        self.LOGGER << "Reverting all user edits"

        m = self.model()

        m.beginResetModel()

        # block signals from the model while we undo all so that we
        # don't overwhelm the user's processor with full-auto-fire signals
        with blocked_signals(m):
            while self._undo_stack.canUndo() \
                    and not self._undo_stack.isClean():
                self._undo_stack.undo()

        # selection is likely worthless now
        self.clearSelection()

        # we have no selection, so disable the movement buttons
        self.enableModActions.emit(False)

        # now, with signals reenabled, reanalyse the error-types;
        m.check_mod_errors()

        # and finish the model reset
        m.endResetModel()


    def save_changes(self):
        """
        Save all changes made to the table since the last save-point
        (or app start) and set a new clean state in the undo stack
        :return:
        """
        self.LOGGER << "Saving user changes"
        self._model.save()
        self._undo_stack.setClean()

    ##=============================================
    ## "Move selection" action handlers

    def move_selection_to_top(self):
        self._reorder_selection(0, text="Move to Top")

    def move_selection_to_bottom(self):
        sel_rows = self._selected_row_numbers()

        # subtract the number of rows from the total row count to make
        # sure we don't try to move anything beyond the end of the list
        self._reorder_selection(self._model.rowCount() - len(sel_rows),
                                sel_rows, "Move to Bottom")

    def move_selection(self, distance):
        """
        :param distance: if positive, we're increasing the mod install ordinal--i.e. moving the mod further down the list.  If negative, we're decreasing the ordinal, and moving the mod up the list.
        """
        if distance != 0:
            rows = self._selected_row_numbers()
            self._reorder_selection(rows[0] + distance, rows)

    ##=============================================
    ## Internal slots
    ##=============================================

    @pyqtSlot(int)
    def _analyze_errors(self, err_types):
        """
        Determines whether to hide the Errors column, and emits the
        errorschanged signal if the type of errors present in the table
        changes.

        :param err_types:
        """
        self.LOGGER << f"_analyze_errors({err_types})"

        old_err_types = self._err_types

        if err_types:
            self.setColumnHidden(Column.ERRORS, False)
            self.resizeColumnToContents(Column.ERRORS)
        else:
            self.setColumnHidden(Column.ERRORS, True)

        self._err_types = err_types

        if old_err_types != err_types:
            self.errorsChanged.emit(err_types)

    # def on_rows_moved(self, parent, start, end, destination, row):
    # noinspection PyUnusedLocal
    def on_rows_moved(self, *args):
        """gets notified when endMoveRows() is called by the model"""
        # the arguments aren't important to us

        # NTS: although, maybe they should be? I guess that we could
        # check to see if the first/last items of the list are within
        # the destination area after moving (assuming we have a selection;
        # if we don't it wouldn't matter).
        # I don't really feel that would offer any benefit over the
        # current way we do it, though

        if self._selection_model.hasSelection():
            self._selection_moved()

    def _selection_moved(self):
        """
        Determines whether or not to enable the mod move-up/down buttons
        """
        # self.LOGGER << "selection moved"

        is_selected = self._selection_model.isSelected
        m = self._model

        # emit signal with info about whether the first/last
        # items of the list are in the current selection
        self.canMoveItems.emit(
            not is_selected(m.index(0,0)),
            not is_selected(m.index(m.rowCount()-1, 0))
        )

    def _selected_row_numbers(self):
        # we use set() first because Qt sends the row number once for
        # each column in the row.
        return sorted(set(idx.row() for idx in self.selectedIndexes()))

    def on_rows_dropped(self, start, end, dest):
        """
        Reacts to rowsDropped signal from model

        :param start:
        :param end:
        :param dest:
        :return:
        """
        count = end - start + 1

        # since we can't drop a selection on itself, we don't need
        # to worry about dest being between start and end
        if start < dest: # moving down
            # we need to account for the section we're dragging
            # being essentially "removed" from the list for now;
            # otherwise the section will end up shifted down from
            # where it should be
            dest -= count  # real dest

        self.move_rows(start, dest, count, text="Drag Rows")

    def _reorder_selection(self, dest, rows=None, text="Reorder"):
        """

        :param int dest: the destination row number
        :param list[int] rows: the (contigous section of) rows to shift.
            If None or not specified, will be derived from the current
            selection.
        :param text:
        """

        if rows is None:
            rows = self._selected_row_numbers()
        if rows:
            self.move_rows(rows[0], dest, len(rows), text)

    def move_rows(self, src, dest, count, text="Change order"):
        """
        Build a QUndoCommand that encapsulates moving a section of the
        mod table around, then push it to the undo stack to execute
        the operation.

        :param src:
        :param dest:
        :param count:
        :param text:
        """

        if dest != src:

            # yeesh that's a lotta junk. See the model for notes on
            # it...or don't, you'll be better off.
            first, last, \
            split, srcFirst, srcLast, dChild, \
            rsplit, rsrcFirst, rsrcLast, rdChild = \
                self._model.prepare_move(src, dest, count)

            # build partial funcs using this info
            forward_cmd = partial(self._model.do_move,
                                  first, last, split,
                                  srcFirst, srcLast, dChild,
                                  self.rootIndex())

            reverse_cmd = partial(self._model.do_move,
                                  first, last, rsplit,
                                  rsrcFirst, rsrcLast, rdChild,
                                  self.rootIndex())

            # now feed those funcs to a generic UndoCommand,
            # and push it to the undo stack
            self._undo_stack.push(UndoCommand(
                text=text,
                redo=forward_cmd,
                undo=reverse_cmd))

    def on_new_mod(self):
        """
        Called when a new mod is installed and added to the model.
        """

        # save the mod collection
        self._model.save()

        # drop the undostack
        self._undo_stack.clear()




class CheckBoxDelegate(QtWidgets.QStyledItemDelegate):
    """Custom delegate that intercepts when a user clicks on a the
    checkbox in the delegate's cell and wraps the model's setData()
    call in a QUndoCommand"""

    def __init__(self, parent, *args, **kwargs):
        # noinspection PyArgumentList
        super().__init__(parent, *args, **kwargs)

        # get the undo stack instance from the parent (the treeview)
        self._stack = parent.undo_stack # type: QtWidgets.QUndoStack



    def editorEvent(self, event, model, style_option, index):

        #TODO: see if we can get some sort of visual response when the mouse is pressed down on the checkbox (like a regular checkbox does, to show that it really does know that you're clicking on it)

        if event.type() == QEvent.MouseButtonRelease:
            # create a qundo command to wrap the setdata call

            # current enabled status of the mod at the given index
            is_enabled = bool(index.internalPointer().enabled)

            self._stack.push(
                UndoCommand(
                    text="Disable Mod" if is_enabled else "Enable Mod",
                    redo=partial(model.setData, index, not is_enabled, Qt.EditRole),
                    undo=partial(model.setData, index, is_enabled, Qt.EditRole)
                )
            )

        # return True to indicate that the event has been handled,
        # even if we didn't handle it (because we don't want any other
        # editor event stuff to happen)
        return True

# create similar delegate for the name-edit field
class LineEditDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, parent, *args, **kwargs):
        # noinspection PyArgumentList
        super().__init__(parent, *args, **kwargs)

        # get the undo stack instance from the parent (the treeview)
        self._stack = parent.undo_stack  # type: QtWidgets.QUndoStack


    def setModelData(self, editor, model, index):
        # editor is a qlineedit

        new_name=editor.text().strip()

        curr_name = index.internalPointer().name.strip()

        # make sure the name field isn't empty and that a change
        # did actually happen
        if new_name and new_name != curr_name:
            self._stack.push(
                UndoCommand(
                    text="Edit Mod Name",
                    redo=partial(model.setData, index, new_name, Qt.EditRole),
                    undo=partial(model.setData, index, curr_name, Qt.EditRole)
                )
            )



