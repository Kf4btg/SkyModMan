from PyQt5.QtWidgets import QHeaderView, QTreeView, QAbstractItemView, QMenu
from PyQt5.QtCore import Qt, pyqtSignal

from skymodman.constants import Column
from skymodman.thirdparty.undo import group
from skymodman.utils import withlogger

from skymodman.qt_interface.models.modtable_tree import ModTable_TreeModel

Qt_Checked   = Qt.Checked
Qt_Unchecked = Qt.Unchecked
Qt_CheckStateRole = Qt.CheckStateRole

COL_ENABLED = Column.ENABLED.value


@withlogger
class ModTable_TreeView(QTreeView):

    enableModActions = pyqtSignal(bool)

    canMoveItems = pyqtSignal(bool, bool)

    def __init__(self, *, parent, manager, **kwargs):
        # noinspection PyArgumentList
        super().__init__(parent, **kwargs)
        self.manager = manager #type: ModManager
        self._parent = parent # type: ModManagerWindow
        self._model  = None  # type: ModTable_TreeModel
        self._selection_model = None # type: QtCore.QItemSelectionModel
        self.LOGGER << "Init ModTable_TreeView"

    def initUI(self, grid):
        self.setRootIsDecorated(False) # no collapsing
        self.setObjectName("mod_table")
        grid.addWidget(self, 1, 0, 1, 5)

        self.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)

        self.setModel(ModTable_TreeModel(parent=self, manager=self.manager))
        self.setColumnHidden(Column.DIRECTORY, True) # hide directory column by default
        # h=self.header() #type:QHeaderView
        self.header().setStretchLastSection(False) # don't stretch the last section...
        self.header().setSectionResizeMode(Column.NAME, QHeaderView.Stretch)  # ...stretch the Name section!

        self._selection_model = self.selectionModel()  # keep a local reference to the selection model
        self._model.notifyViewRowsMoved.connect(self._selection_moved) # called from model's shiftrows() method
        self._model.hideErrorColumn.connect(self._hideErrorColumn) # only show error col if there are errors

    def _hideErrorColumn(self, hide):
        self.setColumnHidden(Column.ERRORS, hide)
        if not hide:
            self.resizeColumnToContents(Column.ERRORS)

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
    from PyQt5 import QtCore #, QtGui

    # QModelIndex
    # from PyQt5.QtGui import QDragEnterEvent, QContextMenuEvent