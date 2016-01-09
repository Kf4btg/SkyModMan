from PyQt5.QtCore import Qt, QModelIndex, QAbstractItemModel, pyqtSignal

import os
from os.path import join, relpath
from pathlib import Path

from skymodman.utils import withlogger


# @withlogger
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

        self.leaf = False

        self._parent = parent

        self._children = []

        self._row=0

        #TODO: make sure that this actually isn't used anywhere and remove it
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
    def parent(self):
        """Reference to the parent (containing directory) of this item,
        or None if this is the root item"""
        return self._parent

    def __getitem__(self, row:int):
        """Access children using list notation: thisitem[0]
        Returns none if given an invalid row number"""
        try:
            return self._children[row]
        except IndexError:
            return None

    @property
    def children(self):
        """Returns a list of this item's direct children"""
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
        """Add a child FSItem to this instance. Also sets that child's 'row' attribute
        based on its position in the parent's list
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
        :param filter: When implemented, will allow name-filtering to exclude some
        files from the results
        :return:
        """
        # TODO: sort the list of children after retrieving. (using the alphabet or something)

        for de in os.scandir(join(rel_root, self.path)):
            child = self.__class__(relpath(de.path, rel_root), de.name, self)
            if de.is_dir():
                child.loadChildren(rel_root)
            else:
                child.leaf = True
            self.append(child)


class QFSItem(FSItem):
    """FSITem subclass with Qt-specific functionality"""

    # now here's a hack...
    # this is changed by every child when recursively toggling check state;
    # thus its final value will the row of the final child accessed.
    last_row_touched = 0

    def __init__(self, *args, **kwargs):
        super(QFSItem, self).__init__(*args, **kwargs)

        self._checkstate=Qt.Checked# tracks explicit checks
        self.flags = Qt.ItemIsUserCheckable | Qt.ItemIsEnabled
        if not self.leaf:
            self.flags |= Qt.ItemIsTristate
        else:
            self.flags |= Qt.ItemNeverHasChildren

    @property
    def itemflags(self):
        """Initial flags for all items are Qt.ItemIsUserCheckable and Qt.ItemIsEnabled
        Non-directories receive the Qt.ItemNeverHasChildren flag, and dirs get
        Qt.ItemIsTristate to allow the 'partially-checked' state"""
        return self.flags

    @itemflags.setter
    def itemflags(self, value):
        self.flags = value

    @property
    def checkState(self):
        if not self.child_count:
            return self._checkstate

        return self.childrenCheckState()

    # So, I think the protocol here is, when a directory is un/checked,
    # set the checkstates of all that directory's children to match.
    # here's the python translation of the c++ code from qtreewidget.cpp:
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
          if no children checked => this item is unchecked.

          Note: both the description above and the algorithm below were 'borrowed' from the Qt code for QTreeWidgetItem"""
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



@withlogger
class ModFileTreeModel(QAbstractItemModel):
    """
    A custom model that presents a view into the actual files saved within a mod's folder.
    It is vastly simplified compared to the QFileSystemModel, and only supports editing
    the state of the checkbox on each file or folder (though there is some neat trickery
    that propagates a check-action on a directory to all of its descendants)
    """

    rootPathChanged = pyqtSignal(str)

    def __init__(self, manager, parent, *args, **kwargs):
        super(ModFileTreeModel, self).__init__(parent, *args, **kwargs)
        self.manager = manager
        self.rootpath = None #type: str
        self.rootitem = None #type: QFSItem

    @property
    def root_path(self):
        return self.rootpath

    @property
    def root_item(self):
        return self.rootitem

    def setRootPath(self, path:str):
        """
        Using this instead of a setter just for API-similarity with
        QFileSystemModel. That's the same reason rootPathChanged is emitted
        at the end of the method, as well.
        :param path:
        :return:
        """
        if path == self.rootpath: return

        self.logger.debug("rootpath = "+path)
        if os.path.exists(path):
            self.beginResetModel()
            self.rootpath = path
            # name for this item is never actually seen
            self.rootitem = QFSItem("", "datafolder", None)
            self.rootitem.loadChildren(self.rootpath)
            self.endResetModel()
            # enit notifier signal
            self.rootPathChanged.emit(path)

    def getItem(self, index:QModelIndex) -> QFSItem:
        """Extracts actual item from given index"""
        if index.isValid():
            item = index.internalPointer() #type:QFSItem
            if item: return item
        return self.rootitem

    def columnCount(self, *args, **kwargs):
        return 1

    def rowCount(self, index:QModelIndex=QModelIndex(), *args, **kwargs):
        """Number of children contained by the item referenced by `index`"""
        # return 0 until we actually have something to show
        if not self.rootitem: return 0
        return self.getItem(index).child_count

    def headerData(self, section, orient, role=None):
        """Just one column, 'Name'. super() call should take care of the
        size hints &c."""
        if orient == Qt.Horizontal and role==Qt.DisplayRole:
            return "Name"
        return super(ModFileTreeModel, self).headerData(section, orient, role)

    def index(self, row:int, col:int, parent:QModelIndex=QModelIndex(), *args, **kwargs):
        """
        Create or find the QModelIndex that represents the item at (row, col) with respect
         to the given  parent index. (or the root index if parent is invalid)
        :param row:
        :param col:
        :param parent:
        :return:
        """

        parent_item = self.rootitem
        if parent.isValid():
            parent_item = parent.internalPointer()

        child = parent_item[row]
        if child:
            return self.createIndex(row, col, child)

        return QModelIndex()

    def parent(self, child_index:QModelIndex=QModelIndex()):
        if not child_index.isValid(): return QModelIndex()

        # get the parent FSItem from the reference stored in each FSItem
        parent = child_index.internalPointer().parent

        if not parent or parent is self.rootitem:
            return QModelIndex()

        # Every FSItem has a row attribute which we use to create the index
        return self.createIndex(parent.row, 0, parent)

    def flags(self, index:QModelIndex):
        """Flags are held at the item level; lookup and return them from the item referred to be the index"""
        item = self.getItem(index)
        return item.itemflags

    def data(self, _index:QModelIndex, role=Qt.DisplayRole):
        """For our purposes, only the file name and the checkbox state concern us"""

        item = self.getItem(_index)

        if role == Qt.DisplayRole:
            return item.name
        elif role == Qt.CheckStateRole:
            # hides the complexity of the tristate workings
            return item.checkState

        # apparently the "base implementation" just calls data() again...
        # leading to the lovely recursive loop that had me tearing my
        # hair out. But implicitly returning None for all other roles
        # doesn't seem to be causing a problem.
        # return super(ModFileTreeModel, self).data(_index, role)

    def setData(self, index, value, role:int=Qt.CheckStateRole):
        """Only the checkStateRole can be edited in this model.
        Most of the machinery for that is in the QFSItem class"""
        if not index.isValid(): return

        item = self.getItem(index)
        if role==Qt.CheckStateRole:
            item.checkState = value
            last_index = self.index(QFSItem.last_row_touched, 0, index)

            # using the "last_row_touched" value--which SHOULD be the most
            # "bottom-right" child idx that was just changed--to feed to
            # datachanged saves a lot of individual calls. Hopefully there
            # won't be any concurrency issues to worry about later on.
            self.dataChanged.emit(index, last_index)
            return True
        return super(ModFileTreeModel, self).setData(index, value, role)



if __name__ == '__main__':
    from skymodman.managers import ModManager
