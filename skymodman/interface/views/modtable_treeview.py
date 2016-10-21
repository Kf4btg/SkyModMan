from PyQt5 import QtWidgets, QtCore

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QItemSelectionModel as qISM

from skymodman.constants import Column, ModError
from skymodman.log import withlogger

# from skymodman.interface.models import ModTable_TreeModel
from skymodman.interface.ui_utils import undomacro, blocked_signals

qmenu = QtWidgets.QMenu

Qt_Checked   = Qt.Checked
Qt_Unchecked = Qt.Unchecked
Qt_CheckStateRole = Qt.CheckStateRole
PositionAtCenter = QtWidgets.QAbstractItemView.PositionAtCenter

COL_ENABLED = Column.ENABLED.value


@withlogger
class ModTable_TreeView(QtWidgets.QTreeView):

    enableModActions = pyqtSignal(bool)

    enableSearchActions = pyqtSignal(bool)
    """emitted to enable/disable the find-next/previous buttons"""

    canMoveItems = pyqtSignal(bool, bool)

    setStatusMessage = pyqtSignal(str)
    """emitted when the table would like to update the main window status bar"""

    # itemsLoaded = pyqtSignal(int)
    # """emitted with the number of items in the table after loading is finished"""

    # TODO: this could likely be more generic; it's meant to inform the main window to reanalyze which actions are active (in particular, the clear_missing_mods action)
    errorsChanged = pyqtSignal(int)

    def __init__(self, parent, *args, **kwargs):
        # noinspection PyArgumentList
        super().__init__(parent, *args, **kwargs)

        self._model  = None
        """:type: skymodman.interface.models.ModTable_TreeModel"""
        self._selection_model = None # type: qISM
        self.handle_move_signals = True
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
        ## setup search box ##

        self._searchbox = search_box

        # setup the animation to show/hide the search bar
        self.animate_show_search = QtCore.QPropertyAnimation(
            self._searchbox, b"maximumWidth")
        self.animate_show_search.setDuration(300)
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

        # called from model's shiftrows() method
        self._model.notifyViewRowsMoved.connect(self.selectionChanged)

        # only show error col if there are errors
        self._model.errorsAnalyzed.connect(self._analyze_errors)

        ## some final UI adjustments ##

        # hide directory column by default
        self.setColumnHidden(Column.DIRECTORY, True)

        # stretch the Name section
        self.header().setSectionResizeMode(Column.NAME,
                                           QtWidgets.QHeaderView.Stretch)

    def selectionChanged(self, selected=None, deselected=None):

        # None means the selection was _moved_, rather than changed
        if selected is None:
            # self.handle_move_signals will be false if there
            # is no selection and we're in an undo/redo cmd
            # if self.handle_move_signals:
            if self._selection_model.hasSelection():
                self._selection_moved()
        else:
            # self.LOGGER << "selection changed"

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

    ## XXX: What's the point of this??
    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)

    def contextMenuEvent(self, event):
        """

        :param QContextMenuEvent event:
        """

        mw = self.window()  # mainwindow

        menu = qmenu(self)
        menu.addActions([mw.action_toggle_mod,
                         mw.action_uninstall_mod,
                         ])

        if not self.isColumnHidden(Column.ERRORS):
            menu.addAction(mw.action_clear_missing)

        menu.exec_(event.globalPos())

    ##=============================================
    ## Searching
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

        # FIXME: selected row is off by 1
        # fixme: searching again always seem to return the
        # same index (I suspect this is directly related to
        # the off-by-1 error)

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
        # self.action_find_next.setEnabled(e)
        # self.action_find_previous.setEnabled(e)
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
                    # this means we DID find the text, but it was the same
                    # row that we started on
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

        # self.itemsLoaded.emit(self._model.rowCount())

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

        currstate = self.currentIndex().internalPointer().enabled
        sel = self.selectedIndexes()

        _text = ("Enable", "Disable")[currstate]
        _checked = (Qt_Checked, Qt_Unchecked)[currstate]

        # splitting these up may help with some undo weirdness...

        if len(sel) > self._model.columnCount():
            # multiple rows selected

            # bind them all into one undo-action
            with undomacro(self.undo_stack, ": {} Mods".format(_text)):
                for idx in filter(lambda i: i.column() == COL_ENABLED,
                                  sel):
                    # if i.column() == COL_ENABLED:
                    self._model.setData(idx, _checked,
                                        Qt_CheckStateRole)
        else:
            # only one row
            self._model.setData(sel[COL_ENABLED], _checked,
                                Qt_CheckStateRole)

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
    ## Action handlers

    def move_selection_to_top(self):
        self._tell_model_shift_rows(0, text="Move to Top")

    def move_selection_to_bottom(self):
        self._tell_model_shift_rows(self._model.rowCount() - 1,
                                    text="Move to Bottom")

    def move_selection(self, distance):
        """
        :param distance: if positive, we're increasing the mod install ordinal--i.e. moving the mod further down the list.  If negative, we're decreasing the ordinal, and moving the mod up the list.
        """
        if distance != 0:
            rows = self._selected_row_numbers()
            self._tell_model_shift_rows(rows[0] + distance, rows=rows)

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
        # self.setColumnHidden(Column.ERRORS, hide)
        # if not hide:
        #     self.resizeColumnToContents(Column.ERRORS)

        old_err_types = self._err_types

        if err_types:
            self.setColumnHidden(Column.ERRORS, False)
            self.resizeColumnToContents(Column.ERRORS)
        else:
            self.setColumnHidden(Column.ERRORS, True)

        self._err_types = err_types

        if old_err_types != err_types:
            self.errorsChanged.emit(err_types)

    def _selection_moved(self):
        """
        Determines whether or not to enable the mod move-up/down buttons
        """
        # self.LOGGER << "selection moved"

        is_selected = self._selection_model.isSelected
        model = self._model
        self.canMoveItems.emit(
            not is_selected(model.index(0,0)),
            not is_selected(model.index(model.rowCount()-1, 0))
        )

    def _selected_row_numbers(self):
        # we use set() first because Qt sends the row number once for
        # each column in the row.
        return sorted(set(
                [idx.row()
                 for idx in
                 self.selectedIndexes()]))

    def _tell_model_shift_rows(self, dest, *, rows=None, text="Reorder Mods"):
        """
        :param int dest: either the destination row number or a callable
            that takes the sorted list of selected rows as an argument
            and returns the destination row number.
        :param rows: the rows to shift. If None or not specified, will
            be derived from the current selection.
        :param text: optional text that will appear after 'Undo' or
            'Redo' in the Edit menu
        """
        if rows is None:
            rows = self._selected_row_numbers()
        if rows:
            self._model.shift_rows(rows[0],
                                   rows[-1],
                                   dest,
                                   parent=self.rootIndex(),
                                   undotext=text)

