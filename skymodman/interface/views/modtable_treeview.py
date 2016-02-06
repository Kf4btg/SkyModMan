from PyQt5.QtWidgets import QHeaderView, QTreeView, QAbstractItemView, QMenu
from PyQt5.QtCore import Qt, pyqtSignal, QItemSelectionModel

from skymodman.constants import Column
from skymodman.utils import withlogger
from skymodman.thirdparty.undo import group

from skymodman.interface.models.modtable_treemodel import ModTable_TreeModel

Qt_Checked   = Qt.Checked
Qt_Unchecked = Qt.Unchecked
Qt_CheckStateRole = Qt.CheckStateRole

COL_ENABLED = Column.ENABLED.value


@withlogger
class ModTable_TreeView(QTreeView):

    enableModActions = pyqtSignal(bool)

    canMoveItems = pyqtSignal(bool, bool)

    def __init__(self, parent, *args, **kwargs):
        # noinspection PyArgumentList
        super().__init__(parent, *args, **kwargs)
        self._model  = None  # type: ModTable_TreeModel
        self._selection_model = None # type: QtCore.QItemSelectionModel
        self.handle_move_signals = True
        # self.LOGGER << "Init ModTable_TreeView"

    def _hideErrorColumn(self, hide):
        self.setColumnHidden(Column.ERRORS, hide)
        if not hide:
            self.resizeColumnToContents(Column.ERRORS)

    def setModel(self, model):
        super().setModel(model)
        self._model = model
        # keep a local reference to the selection model
        self._selection_model = self.selectionModel()
        # called from model's shiftrows() method
        self._model.notifyViewRowsMoved.connect(self.selectionChanged)
        # only show error col if there are errors
        self._model.hideErrorColumn.connect(self._hideErrorColumn)

        # some final UI adjustments
        self.setColumnHidden(Column.DIRECTORY,
                             True)  # hide directory column by default
        # stretch the Name section
        self.header().setSectionResizeMode(Column.NAME,QHeaderView.Stretch)

    def loadData(self):
        self._model.loadData()
        self.resizeColumnsToContents()

    def search(self, text, direction=1):
        """
        Query the model for the row containing the given text;
        if it is found, scroll to and select the row.
        :param text:
        :return:
        """
        cindex = self.currentIndex()
        result = self._model.search(text, cindex, direction)

        if result.isValid():
            if result==cindex:
                # this means that we're sitting on the only
                # row that matches the search; return None
                # to differentiate it.
                return None

            self._selection_model.select(result, QItemSelectionModel.ClearAndSelect)
            self.scrollTo(result, QAbstractItemView.PositionAtCenter)
            self.setCurrentIndex(result)
            return True
        return False

    def resizeColumnsToContents(self):
        for i in range(self._model.columnCount()):
            self.resizeColumnToContents(i)

    def revertChanges(self):
        self.LOGGER << "Reverting all user edits"
        self._model.revert_all()
        self.enableModActions.emit(False)

        # self.clearSelection()

    def saveChanges(self):
        self.LOGGER << "Saving user changes"
        self._model.save()

    def selectionChanged(self, selected=None, deselected=None):

        # None means the selection was _moved_, rather than changed
        if selected is None:
            # self.handle_move_signals will be false if there
            # is no selection and we're in an undo/redo cmd
            if self.handle_move_signals:
                self._selection_moved()
        else:
            # self.LOGGER << "selection changed"

            # enable/disable the button box
            if self._selection_model.hasSelection():

                self.enableModActions.emit(True)
                self._selection_moved()   # check for disable up/down buttons
            else:
                self.enableModActions.emit(False)

            super().selectionChanged(selected, deselected)

    def _selection_moved(self):
        """
        Determines whether or not to enable the mod move-up/down buttons
        :return:
        """
        # self.LOGGER << "selection moved"

        is_selected = self._selection_model.isSelected
        model = self._model
        self.canMoveItems.emit(
            not is_selected(model.index(0,0)),
            not is_selected(model.index(model.rowCount()-1, 0))
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
        # we check the hasSelection() result to see whether
        # whether we want to ignore notifications about row
        # movement sent by the model (which we would only be
        # interested in if the selection were being moved around)
        self.handle_move_signals = self._selection_model.hasSelection()
        self._model.undo()

        # and reset it afterwards
        self.handle_move_signals = True

    def redo(self):
        # see note above
        self.handle_move_signals = self._selection_model.hasSelection()
        self._model.redo()
        self.handle_move_signals = True

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

        mw = self.window() # mainwindow
        menu = QMenu(self)
        menu.addActions([mw.action_toggle_mod,
                         mw.action_uninstall_mod,
                         ])
        menu.exec_(event.globalPos())

    def toggleSelectionCheckstate(self):
        # to keep things simple, we base the first toggle off of the enabled state of the
        # current index.  E.g., even if it's the only enabled mod in the selection,
        # the first toggle will still be a disable command. It's rough, but the user may
        # need to hit 'Space' **twice** to achieve their goal.  Might lose a lot of people over this.
        currstate = self.currentIndex().internalPointer().enabled
        sel = self.selectedIndexes()

        # splitting these up may help with some undo weirdness...
        if len(sel) > self._model.columnCount(): # multiple rows selected
            with group(": {} Mods".format(["Enable", "Disable"][currstate])):

                for i in sel:
                    if i.column() == COL_ENABLED:
                        self._model.setData(i, [Qt_Checked, Qt_Unchecked][
                            currstate], Qt_CheckStateRole)
        else:
            # only one row
            self._model.setData(sel[COL_ENABLED], [Qt_Checked,
                                    Qt_Unchecked][currstate],
                                Qt_CheckStateRole)

if __name__ == '__main__':
    from PyQt5 import QtCore #, QtGui
