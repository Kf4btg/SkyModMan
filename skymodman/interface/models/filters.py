from PyQt5.QtCore import QSortFilterProxyModel, QModelIndex


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
        Rejects the row if the mod for that row is disabled and
        "OnlyShowActive" is set to True. Also rejects the row if the mod
        could not be found on disk

        :param int row: row in the source
        :param PyQt5.QtCore.QModelIndex parent: parent of row in the source
        :return: whether or not we allow the row to show. Y'know.
        """

        mod = self.sourceModel()[row]

        if self._onlyactive and not mod.enabled:
            return False

        if self.sourceModel().mod_missing(mod): return False

        return super().filterAcceptsRow(row, parent)



class FileViewerTreeFilter(QSortFilterProxyModel):
    """
    This uses the results from a db query to basically ignore the filter on directories
        and make sure any directory which contains a matching file is shown in the tree.
        A directory with no matching files will be hidden.
    """

    def __init__(self,  parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._parent = parent
        self._filtertext = ''

        self.matchingfiles = []

    def setMatchingFiles(self, matches):
        self.matchingfiles = matches

    def setFilterWildcard(self, text):
        self._filtertext = text
        super().setFilterWildcard(text)

    def filterAcceptsRow(self, row, parent):
        """
        This uses the results from a db query to basically ignore the
        filter on directories and make sure any directory which contains
        a matching file is shown in the tree.
        A directory with no matching files will be hidden.

        :param int row:
        :param QModelIndex parent: parent of row in the source
        :return:
        """
        if not self._filtertext: # empty string
            return True

        # no matches
        if not self.matchingfiles: return False

        if not parent.isValid():
            item=self.sourceModel().rootitem[row]
        else:
            item = parent.internalPointer()[row]
        if item.isdir:
            if any(f.startswith(item.lpath) for f in self.matchingfiles):
                return True

        return super().filterAcceptsRow(row, parent)


