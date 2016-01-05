from PyQt5 import QtCore, QtWidgets, Qt, QtGui
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtCore import Qt as _Qt
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
        return _Qt.Checked if self.enabled else _Qt.Unchecked




@withlogger
class ModTableModel(QtCore.QAbstractTableModel):

    COLUMNS = (COL_ENABLED, COL_NAME, COL_MODID, COL_VERSION, COL_ORDER) = list(range(5))

    VISIBLE_COLS = [COL_ENABLED, COL_NAME, COL_MODID, COL_VERSION]

    DBLCLICK_COLS = [COL_MODID, COL_VERSION]

    headers = ["", "Name", "Mod ID", "Version"]

    def __init__(self, parent, manager: 'ModManager', *args):
        super(ModTableModel, self).__init__(parent, *args)
        self._table = parent
        self.manager = manager

        self.mods = [] # type: List[QModEntry]
        # self.columns = []
        self.vheader_field = self.COL_ORDER
        self.visible_columns = []

        self.LOGGER.debug("init ModTableModel")


        # for i in range(len(self.columns)):
        #     self.setHeaderData(i, _Qt.Horizontal, self.columns[i])


    def rowCount(self, parent = QtCore.QModelIndex(), *args, **kwargs):
        return len(self.mods)

    def columnCount(self, parent = QtCore.QModelIndex(), *args, **kwargs):
        return len(self.VISIBLE_COLS)

    def data(self, index: QtCore.QModelIndex, role=_Qt.DisplayRole):
        col = index.column()
        if role == _Qt.DisplayRole and col != constants.COL_ENABLED:
            return self.mods[index.row()][col]
        elif role == _Qt.CheckStateRole and col == constants.COL_ENABLED:
            return self.mods[index.row()].checkState

    def setData(self, index, value, role=None):
        if role==_Qt.CheckStateRole and index.column() == constants.COL_ENABLED:
            self.toggleEnabledState(index.row())
            # modrow = self.mods[index.row()]
            # self.mods[index.row()] = modrow._replace(enabled=int(not modrow.enabled))
            # self.dataChanged.emit(index, index, [_Qt.DisplayRole, role])
            return True
        return False



    def headerData(self, row_or_col, orientation, role=_Qt.DisplayRole):
        # self.logger.debug("Loading header data for {}:{}:{}".format(row_or_col, orientation, role))
        if role==_Qt.DisplayRole:

            if orientation == _Qt.Horizontal:
                return self.headers[row_or_col]

            else: # vertical header
                return self.mods[row_or_col].order

        return super(ModTableModel, self).headerData(row_or_col, orientation, role)

    def flags(self, index: QtCore.QModelIndex):
        if index.column() == self.COL_ENABLED:
            return _Qt.ItemIsEnabled | _Qt.ItemIsUserCheckable

        _flags = _Qt.NoItemFlags #start with nothing

        # if this row is enabled, start with the enabled flag
        if self.mods[index.row()].enabled:
            _flags = _Qt.ItemIsEnabled

        # mod id and version are selectable
        if index.column() in [self.COL_MODID, self.COL_VERSION]:
            return _flags | _Qt.ItemIsSelectable

        # name is selectable and editable
        elif index.column() == self.COL_NAME:
            return _flags | _Qt.ItemIsSelectable | _Qt.ItemIsEditable

        return _flags

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

        # idx = self.index(index.row(), constants.COL_ENABLED)
        # self.dataChanged.emit(idx, idx, [_Qt.DisplayRole, _Qt.CheckStateRole])

    def toggleEnabledState(self, row: int):
        mod = self.mods[row]
        self.mods[row] = mod._replace(enabled=int(not mod.enabled))
        # idx = self.index(index, constants.COL_ENABLED)

        # self.dataChanged.emit(idx, idx, [_Qt.DisplayRole, _Qt.CheckStateRole])

        # emit data changed for all fields in this row
        idx_start = self.index(row, 0)
        idx_end = self.index(row, self.columnCount())
        self.dataChanged.emit(idx_start, idx_end)


@withlogger
class ModTableView(QtWidgets.QTableView):
    def __init__(self, parent, manager, *args, **kwargs):
        super(ModTableView, self).__init__(parent, *args, **kwargs)
        self.manager = manager
        self._model = None #type: ModTableModel
        self.LOGGER.debug("Init ModTableView")
        # self.setModel(ModTableModel(self, manager))




    def initUI(self, grid):
        self.LOGGER.debug("init ModTable UI")
        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.setObjectName("mod_table")
        grid.addWidget(self, 6, 0, 1, 8)

        self.setModel(ModTableModel(self, self.manager))
        hheader = self.horizontalHeader()  # type: QHeaderView
        hheader.setHighlightSections(False)
        hheader.setSectionResizeMode(constants.COL_NAME, QHeaderView.Stretch)
        hheader.setDefaultAlignment(_Qt.AlignLeft)

        # f = hheader.font() #type: QtGui.QFont
        # f = QtGui.QFont('cursive')
        # f.setPointSize(12)
        # f.setCapitalization(QtGui.QFont.SmallCaps)
        # hheader.setFont(f)
        # self.setFont(QtGui.QFont('serif', 12))

        vheader = self.verticalHeader()  # type: QHeaderView
        vheader.setFont(QtGui.QFont('mono', 10))
        vheader.setDefaultAlignment(_Qt.AlignRight)

        self.doubleClicked.connect(self._model.on_doubleClick)


    def setModel(self, model):
        super(ModTableView, self).setModel(model)
        self._model = model

    def loadData(self):
        self._model.loadData()
        self.resizeColumnsToContents()



# self.mod_table = QtWidgets.QTableView(self.installed_mods_tab)
# self.mod_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
# self.mod_table.setDragDropOverwriteMode(False)
# self.mod_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
# self.mod_table.setObjectName("mod_table")
# self.mod_table.horizontalHeader().setVisible(False)
# self.mod_table.horizontalHeader().setHighlightSections(False)
# self.mod_table.horizontalHeader().setSortIndicatorShown(False)
# self.mod_table.horizontalHeader().setStretchLastSection(True)
# self.mod_table.verticalHeader().setVisible(False)
# self.gridLayout_2.addWidget(self.mod_table, 6, 0, 1, 8)





if __name__ == '__main__':
    from skymodman.managers import ModManager