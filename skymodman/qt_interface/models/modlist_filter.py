from PyQt5.QtCore import QSortFilterProxyModel
#(Qt,
# pyqtSignal,
# pyqtSlot,
# QSortFilterProxyModel)


class ActiveModsListFilter(QSortFilterProxyModel):
    """Simple extension of QSortFilterProxyModel that allows us to only show mods marked as 'enabled' in the mods list"""

    def __init__(self, parent):
        self._parent = parent
        super().__init__(parent)

        self._onlyactive = True


    @property
    def onlyShowActive(self):
        return self._onlyactive

    @onlyShowActive.setter
    def onlyShowActive(self, enable):
        """
        Enable or disable the display of inactive/disabled mods.

        :param bool enable:
        """
        self.setOnlyShowActive(enable)

    # pyqtSlot(bool)
    def setOnlyShowActive(self, enabled):
        self._onlyactive = enabled
        self.invalidateFilter()

    def resetInternalData(self):
        self._onlyactive = True
        # self.invalidateFilter()
        super().resetInternalData()


    def filterAcceptsRow(self, row, parent):
        """

        :param int row: row in the source
        :param PyQt5.QtCore.QModelIndex parent: parent of row in the source
        :return: whether or not we allow the row to show. Y'know.
        """

        if self._onlyactive and not self.sourceModel()[row].enabled:
            return False

        return super().filterAcceptsRow(row, parent)




