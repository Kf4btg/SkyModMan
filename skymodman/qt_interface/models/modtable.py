from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtCore import Qt, pyqtSignal
from typing import List

from skymodman import constants
from skymodman.utils import ModEntry, withlogger

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
        return self.name == other.name and self.enabled == other.enabled




@withlogger
class ModTableModel(QtCore.QAbstractTableModel):

    COLUMNS = (COL_ENABLED, COL_NAME, COL_MODID, COL_VERSION, COL_ORDER) = list(range(5))

    VISIBLE_COLS = [COL_ENABLED, COL_NAME, COL_MODID, COL_VERSION]

    DBLCLICK_COLS = [COL_MODID, COL_VERSION]

    headers = ["", "Name", "Mod ID", "Version"]

    tableDirtyStatusChange = pyqtSignal(bool)

    def __init__(self, parent, manager: 'ModManager', *args):
        super(ModTableModel, self).__init__(parent, *args)
        self._table = parent
        self.manager = manager

        self.mods = [] # type: List[QModEntry]
        self.vheader_field = self.COL_ORDER
        self.visible_columns = []

        self.modified_rows = {}

        self.LOGGER.debug("init ModTableModel")

    def rowCount(self, parent = QtCore.QModelIndex(), *args, **kwargs):
        return len(self.mods)

    def columnCount(self, parent = QtCore.QModelIndex(), *args, **kwargs):
        return len(self.VISIBLE_COLS)

    def data(self, index: QtCore.QModelIndex, role=Qt.DisplayRole):
        col = index.column()
        if role == Qt.DisplayRole and col != constants.COL_ENABLED:
            return self.mods[index.row()][col]
        elif role == Qt.CheckStateRole and col == constants.COL_ENABLED:
            return self.mods[index.row()].checkState

    def setData(self, index, value, role=None):
        """Here is where we need to track changes to items to allow undo"""
        if role==Qt.CheckStateRole and index.column() == constants.COL_ENABLED:
            self.toggleEnabledState(index.row())
            return True

        elif role == Qt.EditRole and index.column() == constants.COL_NAME:
            row = index.row()
            mod = self.mods[row]

            # don't bother recording if there was no change
            if value == mod.name: return False
            # and don't allow empty names
            if value == "": return False

            newmod = mod._replace(name=value)

            need_notify = self.onModDataEdit(row, mod, newmod)

            self.dataChanged.emit(index, index)

            if need_notify is not None:
                self.tableDirtyStatusChange.emit(need_notify)





        
        return super(ModTableModel, self).setData(index, value, role)

    def onModDataEdit(self, row:int, current:QModEntry, edited: QModEntry):
        """checks if the new value of the mod matches the value of the mod
         at the time of the last save"""

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







    def headerData(self, row_or_col, orientation, role=Qt.DisplayRole):
        # self.logger.debug("Loading header data for {}:{}:{}".format(row_or_col, orientation, role))
        if role==Qt.DisplayRole:

            if orientation == Qt.Horizontal:
                return self.headers[row_or_col]

            else: # vertical header
                return self.mods[row_or_col].order

        return super(ModTableModel, self).headerData(row_or_col, orientation, role)

    def flags(self, index: QtCore.QModelIndex):
        if index.column() == self.COL_ENABLED:
            return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable

        _flags = Qt.NoItemFlags #start with nothing

        # if this row is enabled, start with the enabled flag
        if self.mods[index.row()].enabled:
            _flags = Qt.ItemIsEnabled

        # mod id and version are selectable
        if index.column() in [self.COL_MODID, self.COL_VERSION]:
            return _flags | Qt.ItemIsSelectable

        # name is selectable and editable
        elif index.column() == self.COL_NAME:
            return _flags | Qt.ItemIsSelectable | Qt.ItemIsEditable

        return _flags
    

    def rowDataChanged(self, row):
        """Emits data changed for every item in this table row"""
        idx_start = self.index(row, 0)
        idx_end = self.index(row, self.columnCount())
        self.dataChanged.emit(idx_start, idx_end)
    

    def loadData(self):
        self.beginResetModel()
        self.mods = [QModEntry._make(e) for e in self.manager.basicModInfo()]
        self.endResetModel()
    #
    # def on_click(self, index):
    #     """let clicking anywhere on the checkbox-field change its check-status"""
    #     if index.column() == self.COL_ENABLED:
    #         self.toggleEnabledState(index.row())


    def on_doubleClick(self, index:QtCore.QModelIndex):
        if not index.isValid() or index.column() not in self.DBLCLICK_COLS: return

        self.toggleEnabledState(index.row())

    def toggleEnabledState(self, row: int):
        mod = self.mods[row]
        newmod = mod._replace(enabled=int(not mod.enabled))

        need_notify = self.onModDataEdit(row, mod, newmod)

        self.rowDataChanged(row)

        if need_notify is not None:
            self.tableDirtyStatusChange.emit(need_notify)

        # emit data changed for all fields in this row
        # idx_start = self.index(row, 0)
        # idx_end = self.index(row, self.columnCount())
        # self.dataChanged.emit(idx_start, idx_end)


@withlogger
class ModTableView(QtWidgets.QTableView):
    def __init__(self, parent, manager, *args, **kwargs):
        super(ModTableView, self).__init__(parent, *args, **kwargs)
        self.manager = manager
        self._model = None #type: ModTableModel
        self.LOGGER.debug("Init ModTableView")


    def initUI(self, grid):
        self.LOGGER.debug("init ModTable UI")
        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.setObjectName("mod_table")
        grid.addWidget(self, 6, 0, 1, 8) # from old qtdesigner file

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
        
    # def edit(self, index, trigger=None, event=None):
    #     if index.column() == constants.COL_NAME:
    #         return super(ModTableView, self).edit(index, trigger, event)
    #     else:
    #         return False


if __name__ == '__main__':
    from skymodman.managers import ModManager