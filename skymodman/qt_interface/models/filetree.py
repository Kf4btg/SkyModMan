from PyQt5.QtWidgets import QFileSystemModel
from PyQt5.QtCore import Qt, QModelIndex, QAbstractItemModel, pyqtSignal

import os
from os.path import exists, basename, join, dirname, split, relpath, commonpath
from collections import defaultdict
from pathlib import Path

from skymodman.utils import withlogger


def tree(): return defaultdict(tree)

@withlogger
class FSItem:

    def __init__(self, path:str, name:str,  parent:'FSItem'= None, *args, **kwargs):
        """
        :param path: a relative path from an arbitray root to this file
        :param name: the name that will displayed for this file; usually just the basename
        :param parent: this Item's parent, if any. will be None for top-level items
        """
        super(FSItem, self).__init__(*args, **kwargs)
        self._path = path
        self._name = name

        # P = Path(path)
        # self._isdir = P.is_dir()

        self.leaf = False

        self._parent = parent

        self._children = []

        self._row=0

        self._hidden = False

    @property
    def path(self)->str: return self._path

    @property
    def name(self)->str: return self._name

    @property
    def ppath(self)->Path: return Path(self._path)

    @property
    def row(self)->int: return self._row

    @row.setter
    def row(self, value:int): self._row = value

    @property
    def hidden(self):
        return self._hidden

    @hidden.setter
    def hidden(self, value):
        self._hidden = value

    @property
    def child_count(self):
        """Number of direct children"""
        return len(self._children)

    @property
    def parent(self): return self._parent

    def __getitem__(self, row:int):
        """Access children using list notation: thisitem[0]
        Returns none if given an invalid row number"""
        try:
            return self._children[row]
        except IndexError:
            return None

    @property
    def children(self):
        return self._children

    def iterchildren(self, recursive = False):
        """
        Iterator over this FSItem's children
        :param recursive: If False or omitted, just yield this item's direct children. If true, yield each child followed by that child's children
        """
        if recursive:
            for child in self._children:
                yield child
                yield from child.children(True)
        else:
            yield from self._children

    def append(self, child:'FSItem'):
        """Add a child FSItem to this instance
        :param child:
        """
        child.row = len(self._children)
        self._children.append(child)

    def loadChildren(self, rel_root, filter = None):
        """
        Given a root, construct an absolute path from that root and
        this item's (relative) path. Then scan that root for entries, creating an
        FSItem for any files found and adding that item to the list of children.
        If the entry found is a directory, then call the loadChildren() method
        of the new FSItem with the same root given here.
        :param rel_root:
        :param filter:
        :return:
        """
        # print(join(rel_root, self.path))
        for de in os.scandir(join(rel_root, self.path)):
            child = self.__class__(relpath(de.path, rel_root), de.name, self)
            # print(type(child))
            # print(child.name)
            if de.is_dir():
                child.loadChildren(rel_root)
            else:
                child.leaf = True
            self.append(child)


class QFSItem(FSItem):
    """FSITem subclass with Qt-specific functionality"""
    # CHECKSTATES = (UNCHECKED, CHECKED, PARTIALCHECK) = list(range(3))

    # now here's a hack...
    # this is changed by every child when recursively toggling check state
    last_row_touched = 0

    def __init__(self, *args, **kwargs):
        super(QFSItem, self).__init__(*args, **kwargs)

        self._checkstate=Qt.Checked# tracks explicit checks
        self.flags = Qt.ItemIsUserCheckable | Qt.ItemIsEnabled
        self.pflags = ["Check=16", "Enable=32"]
        if not self.leaf:
            self.flags |= Qt.ItemIsTristate
            self.pflags += ["3state=64"]
        else:
            self.pflags += ["NoKids=128"]
            self.flags |= Qt.ItemNeverHasChildren

    @property
    def itemflags(self):
        # print(self.pflags)
        return self.flags

    @itemflags.setter
    def itemflags(self, value):
        self.flags = value

    # @property
    # def hidden(self):
    #     return super(QFSItem, self).hidden

    # @FSItem.hidden.setter
    # def hidden(self, value):
    #     FSItem.hidden.fset(self, value)

    @property
    def checkState(self):
        if not self.child_count:
            return self._checkstate

        return self.childrenCheckState()
        # ccs = self.childrenCheckState()
        # if ccs == Qt.Checked

    @checkState.setter
    def checkState(self, state):
        # state propagation for dirs:
        # (only dirs can have the tristate flag turned on)
        if self.flags & Qt.ItemIsTristate and state != Qt.PartiallyChecked:
            # propagate a check-or-uncheck down the line:
            for c in self.iterchildren():
                # using a class variable, track which items were changed
                QFSItem.last_row_touched = c.row
                # this will trigger any child dirs to do the same
                c.checkState = state
                c.setEnabled(state == Qt.Checked)

        self._checkstate = state

    def childrenCheckState(self):
        """  Calculates the checked state of the item based on the checked state
          of its children. E.g. if all children checked => this item is also
          checked; if some children checked => this item is partially checked;
          if no children checked => this item is unchecked."""
        checkedkids = False
        uncheckedkids = False

        # check child checkstates;
        # break when answer can be determined;
        # shouldn't need to be recursive if check state is properly
        # propagated and set for all descendants
        for c in self.iterchildren():
            s = c.checkState
            # if any child is partially checked, so will this be
            if s == Qt.PartiallyChecked: return Qt.PartiallyChecked
            elif s == Qt.Unchecked:
                uncheckedkids = True
            else:
                checkedkids = True

            # if we've found both kinds, return partial
            if checkedkids and uncheckedkids:
                return Qt.PartiallyChecked

        return Qt.Unchecked if uncheckedkids else Qt.Checked


    def setEnabled(self, boolean):
        if boolean:
            self.flags |= Qt.ItemIsEnabled
        else:
            self.flags &= ~Qt.ItemIsEnabled





# class Flogger:
#     def debug(self, msg):
#         print(msg)
#     def info(self, msg):
#         print(msg)

@withlogger
class ModFileTreeModel(QAbstractItemModel):

    rootPathChanged = pyqtSignal(str)

    def __init__(self, manager, parent, *args, **kwargs):
        super(ModFileTreeModel, self).__init__(parent, *args, **kwargs)
        self.manager = manager
        self.rootpath = None #type: str
        self.rootitem = None #type: QFSItem
        # self.logger = Flogger()
        # self.LOGGER = self.logger

    @property
    def root_path(self):
        return self.rootpath

    @property
    def root_item(self):
        return self.rootitem



    def setRootPath(self, path):
        if path == self.rootpath: return

        self.logger.debug("rootpath = "+path)


        if os.path.exists(path):
            self.beginResetModel()
            self.rootpath = path
            self.rootitem = QFSItem("", "datafolder", None)
            self.rootitem.loadChildren(self.rootpath)
            self.endResetModel()

    def getItem(self, index:QModelIndex) -> QFSItem:
        """Extracts actual item from given index"""
        # self.logger.debug("\n    index {},{}".format(index.row(), index.column()))
        if index.isValid():
            item = index.internalPointer() #type:QFSItem
            # print(item._name)
            if item: return item
        return self.rootitem

    def columnCount(self, *args, **kwargs):
        return 1

    def rowCount(self, index:QModelIndex=QModelIndex(), *args, **kwargs):
        """Number of children contained by the item referenced by `index`"""
        if not self.rootitem: return 0
        # if not index.isValid(): return 0
        # item = self.getItem(index)
        # self.logger.debug("{} : {}".format(item.name,item.child_count))

        return self.getItem(index).child_count
        # if not index.isValid():
        #     return self.rootitem.child_count
        # return index.internalPointer().child_count()

    def headerData(self, section, orient, role=None):
        if orient == Qt.Horizontal and role==Qt.DisplayRole:
            return "Name"
        return super(ModFileTreeModel, self).headerData(section, orient, role)

    def index(self, row:int, col:int, parent:QModelIndex=QModelIndex(), *args, **kwargs):

        parent_item = self.rootitem
        if parent.isValid():
            parent_item = parent.internalPointer()

        child = parent_item[row]
        if child:
            return self.createIndex(row, col, child)

        return QModelIndex()

    def parent(self, child_index:QModelIndex=QModelIndex()):
        if not child_index.isValid(): return QModelIndex()

        parent = child_index.internalPointer().parent

        if not parent or parent is self.rootitem:
            return QModelIndex()

        return self.createIndex(parent.row, 0, parent)

    def flags(self, index:QModelIndex):
        # flags = Qt.ItemIsUserCheckable

        item = self.getItem(index)
        # self.logger.debug("i:"+item.name)
        # self.logger.debug(int(item.itemflags))
        return item.itemflags

        # if not item.hidden:
        #     flags |= Qt.ItemIsEnabled
        #
        # if item.child_count: #directories
        #     flags |= Qt.ItemIsTristate
        #
        #
        # if item.leaf:
        #     flags |= Qt.ItemNeverHasChildren

    def data(self, _index:QModelIndex, role=Qt.DisplayRole):
        # if not index.isValid(): return None

        item = self.getItem(_index)
        # print ("--"+item.name)

        if role == Qt.DisplayRole:
            # self.logger.debug("Qt.DisplayRole")
            return item.name
        elif role == Qt.CheckStateRole:
            # self.logger.debug("Qt.CheckStateRole")
            return item.checkState # hides the complexity of the tristate workings
        # self.logger.debug("role: {}".format(role))
        # return super(ModFileTreeModel, self).data(_index, role)

    def setData(self, index, value, role:int=Qt.CheckStateRole):
        if not index.isValid(): return

        item = self.getItem(index)
        if role==Qt.CheckStateRole:
            item.checkState = value
            last_index = self.index(QFSItem.last_row_touched, 0, index)

            self.dataChanged.emit(index, last_index)
            return True
        return super(ModFileTreeModel, self).setData(index, value, role)

            # So, I think the protocol here is, when a directory is un/checked,
            # set the checkstates of all that directory's children to match.


            # here's the ppython translation of the c++ code from qtreewidget.cpp:

            # (item.itemflags & Qt.ItemIsTristate) means we have a directory, and
            # 3state checkmarks are currently enabled (only dirs have the 3state flag)
            # if item.itemflags & Qt.ItemIsTristate and value != Qt.PartiallyChecked:
            #     for c in item.children(): # for each child
            #         f = item.itemflags # ... I don't think this "little hack" is needed in our case
            #         item.itemflags &= ~Qt.ItemIsTristate  # "a little hack to avoid multiple dataChanged signals"
            #         c.checkState = value
            #         item.itemflags = f


            # if value == Qt.Unchecked: # hiding a file
            #     item.hidden = True
            #     if item.leaf: # a file, no kids
            #         self.dataChanged.emit(index, index)
            #     else:
            #         # todo: propagate
            #         self.dataChanged.emit(index, index)







@withlogger
class ModQFSTreeModel(QFileSystemModel):

    def __init__(self, manager: 'ModManager', *args, **kwargs):
        super(ModQFSTreeModel, self).__init__(*args, **kwargs)

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


        return super(ModQFSTreeModel, self).data(index, role)

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

        return super(ModQFSTreeModel, self).setData(index, value, role)

    def flags(self, index):
        default_flags = super(ModQFSTreeModel, self).flags(index)

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
