from PyQt5.QtWidgets import QFileSystemModel
from PyQt5.QtCore import Qt, QModelIndex

import os

from skymodman.utils import withlogger

@withlogger
class ModFileTreeModel(QFileSystemModel):

    def __init__(self, manager: 'ModManager', *args, **kwargs):
        super(ModFileTreeModel, self).__init__(*args, **kwargs)

        self.manager = manager
        self.current_dir = ""
        self.rootPathChanged.connect(self.setCurrentDir)

        self.hiddenfiles = {}

    def setCurrentDir(self, newroot):
        self.current_dir = os.path.basename(newroot)

    def getRelPath(self, index:QModelIndex):
        return os.path.relpath(self.filePath(index), self.rootPath())

    def dirDataChanged(self, dirindex):
        """
        Emits data changed for the directory specified by the index and all its children.
        :param dirindex:
        """
        last = ""
        for r, d, f in os.walk(self.filePath(dirindex)):
            if f:
                last = os.path.join(r, f[-1])
            elif d:
                last = os.path.join(r, d[-1])
            else: last = r

        last_index = self.index(last)

        self.dataChanged.emit(dirindex, last_index)



    def data(self, index:QModelIndex, role=None):

        if role==Qt.CheckStateRole:
            if self.current_dir in self.hiddenfiles:
                # check if this file is hidden
                if self.getRelPath(index) in self.hiddenfiles[self.current_dir]:
                    return Qt.Unchecked
            return Qt.Checked


        return super(ModFileTreeModel, self).data(index, role)

    def setData(self, index:QModelIndex , value, role=None):

        if role==Qt.CheckStateRole:
            # name = str(index.data())
            name = self.getRelPath(index)

            # adding a file to hidden list
            if value == Qt.Unchecked:
                if not self.current_dir in self.hiddenfiles:
                    self.hiddenfiles[self.current_dir] = {}

                # append {str file_name: bool isdir}
                if self.hasChildren(index): # if this is a dir
                    self.hiddenfiles[self.current_dir].update({name: True})
                    # self.dataChanged.emit(index, index)
                    self.dirDataChanged(index)


                else:
                    self.hiddenfiles[self.current_dir].update({name: False})

                    self.dataChanged.emit(index, index)

                self.LOGGER.debug("{}".format(self.hiddenfiles))

                return True
            else: #rechecked an item
                del self.hiddenfiles[self.current_dir][name]
                if self.hasChildren(index):
                    self.dirDataChanged(index)

                else: self.dataChanged.emit(index, index)


                # check if any files here are left hidden
                if len(self.hiddenfiles[self.current_dir]) == 0:
                    del self.hiddenfiles[self.current_dir]

                self.LOGGER.debug("{}".format(self.hiddenfiles))
                return True

        return super(ModFileTreeModel, self).setData(index, value, role)

    def flags(self, index):
        default_flags = super(ModFileTreeModel, self).flags(index)

        flags = default_flags | Qt.ItemIsUserCheckable
        flags &= ~Qt.ItemIsSelectable

        if not flags & Qt.ItemNeverHasChildren:
            # file is directory
            flags |= Qt.ItemIsTristate

        if self.current_dir in self.hiddenfiles and \
            self.checkParents(index):
                # disable items below unchecked dirs
                flags &= ~Qt.ItemIsEnabled

        return flags

    def checkParents(self, index):
        """Checks to see if any of this item's parent directories (up to the current root path)
        are hidden.  Returns true if so, False otherwise"""

        while self.filePath(index.parent())!=self.rootPath():
            index = index.parent()
            if self.getRelPath(index) in self.hiddenfiles[self.current_dir]:
                return True
        return False










if __name__ == '__main__':
    from skymodman.managers import ModManager
