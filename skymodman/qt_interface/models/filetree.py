from PyQt5.QtWidgets import QFileSystemModel
from PyQt5.QtCore import Qt, QModelIndex

import os
from collections import defaultdict
from pathlib import Path

from skymodman.utils import withlogger


@withlogger
class FSItem:

    def __init__(self, path:str):
        self._path = path
        P = Path(path)

        self._isdir = P.is_dir()

        self._children = None

        self.parent = None
        self.row=0
        self.column=0



    @property
    def path(self):
        return Path(self._path)

@withlogger
class ModFileTreeModel(QFileSystemModel):

    def __init__(self, manager: 'ModManager', *args, **kwargs):
        super(ModFileTreeModel, self).__init__(*args, **kwargs)

        self.manager = manager
        self.current_dir = ""
        self.rootPathChanged.connect(self.setCurrentDir)

        self.hiddenfiles = defaultdict(dict)

    def setCurrentDir(self, newroot):
        # print("Rootpath changed: {}".format(newroot))
        self.current_dir = os.path.basename(newroot)

    def getRelPath(self, index:QModelIndex):
        # self.logger.debug(self.filePath(index))
        # self.logger.debug(self.rootPath())
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
        print("index ({},{})".format(index.row(), index.column()))
        print("children: {}".format(self.rowCount(index)))

        if role==Qt.CheckStateRole:
            # name = str(index.data())
            name = self.getRelPath(index)

            # adding a file to hidden list
            if value == Qt.Unchecked:
                # if not self.current_dir in self.hiddenfiles:
                #     self.hiddenfiles[self.current_dir] = {}

                # append {str file_name: bool isdir}
                if self.hasChildren(index): # if this is a dir
                    self.hiddenfiles[self.current_dir][name]=True
                    self.dirDataChanged(index)


                else:
                    self.hiddenfiles[self.current_dir][name]=False

                    self.dataChanged.emit(index, index)

                self.LOGGER.debug("{}".format(self.hiddenfiles))

                # return True
            else: #rechecked an item
                del self.hiddenfiles[self.current_dir][name]
                if self.hasChildren(index):
                    self.dirDataChanged(index)

                else: self.dataChanged.emit(index, index)


                # check if there are any remaining hidden files
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

        if self.current_dir in self.hiddenfiles:
            try:
                if self.checkParents(index):
                    # disable items below unchecked dirs
                    flags &= ~Qt.ItemIsEnabled
            except ValueError:
                self.logger.debug("current_dir: {}".format(self.current_dir))
                self.logger.debug("hiddenfile: {}".format(self.hiddenfiles))
                raise

        return flags

    def checkParents(self, index:QModelIndex):
        """Checks to see if any of this item's parent directories (up to the current root path)
        are hidden.  Returns true if so, False otherwise"""

        # print("checking parents of: {}".format(index.data()) )
        name = str(index.data())
        while self.filePath(index.parent())!=self.rootPath():
            index = index.parent()
            if self.getRelPath(index) in self.hiddenfiles[self.current_dir]:
                return True
        return False










if __name__ == '__main__':
    from skymodman.managers import ModManager
