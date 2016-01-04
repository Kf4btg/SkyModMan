from PyQt5 import QtCore, QtWidgets, Qt
from PyQt5.QtCore import Qt as _Qt
from typing import List

from skymodman import constants
from skymodman.utils import ModEntry


class ModTableModel(QtCore.QAbstractTableModel):

    def __init__(self, manager: 'ModManager', profile=None, *args):
        super(ModTableModel, self).__init__(*args)

        self.manager = manager
        self.profile = profile # which profile is currently providing the data

        self.data = [] # type: List[ModEntry]
        # self.columns = []
        self.columns = ["", "Name", "Mod ID", "Version"]
        self.visible_columns = []


    def rowCount(self, parent = QtCore.QModelIndex(), *args, **kwargs):
        return len(self.data)

    def columnCount(self, parent = QtCore.QModelIndex(), *args, **kwargs):
        return len(self.columns)

    def data(self, index: QtCore.QModelIndex, role=_Qt.DisplayRole):
        if role==_Qt.DisplayRole:
            return self.data[index.row()][index.column()]

    def headerData(self, row_or_col, orientation, role=_Qt.DisplayRole):
        if orientation == _Qt.Horizontal:
            return self.columns[row_or_col]
        else: # vertical header
            return self.data[row_or_col].order

    def flags(self, index: QtCore.QModelIndex):
        if index.column() == constants.COL_ENABLED:
            return _Qt.ItemIsEnabled | _Qt.ItemIsUserCheckable

        _flags = _Qt.NoItemFlags #start with nothing

        # if this row is enabled, start with the enabled flag
        if self.data[index.row()].enabled:
            _flags = _Qt.ItemIsEnabled

        # mod id and version are selectable
        if index.column() in [constants.COL_MODID, constants.COL_VERSION]:
            return _flags | _Qt.ItemIsSelectable

        # name is selectable and editable
        elif index.column() == constants.COL_NAME:
            return _flags | _Qt.ItemIsSelectable | _Qt.ItemIsEditable

    def loadData(self):
        self.data = list(self.manager.basicModInfo())


class ModTableView(QtWidgets.QTableView):
    def __init__(self, manager, *args, **kwargs):
        super(ModTableView, self).__init__(*args, **kwargs)

        self.setModel(ModTableModel(manager))
        self.horizontalHeader().setHighlightSections(False)

        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)




if __name__ == '__main__':
    from skymodman.managers import ModManager