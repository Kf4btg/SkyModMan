from PyQt5.QtCore import Qt, QModelIndex, QAbstractItemModel, pyqtSignal
from PyQt5.QtGui import QIcon

import os
from pathlib import Path

from skymodman.utils import withlogger, tree

# @withlogger
class FSItem:

    def __init__(self, path:str, name:str,  parent:'FSItem'= None, isdir = True, *args, **kwargs):
        """
        :param path: a relative path from an arbitray root to this file
        :param name: the name that will displayed for this file; usually just the basename
        :param parent: this Item's parent, if any. will be None for top-level items
        :param isdir: Is this a directory? If not, it will be marked as never being able to hold children
        """
        super(FSItem, self).__init__(*args, **kwargs)
        self._path = path
        self._lpath = path.lower() # used to case-insensitively compare two FSItems
        self._name = name
        self._parent = parent

        self.isdir = isdir
        if self.isdir:
            self._children = []
        else:
            self._children = None # type: list

        self._row=0

        self._hidden = False

    @property
    def path(self)->str: return self._path

    @property
    def lpath(self)->str:
        """All-lowercase version of this item's relative path"""
        return self._lpath

    @property
    def name(self)->str: return self._name

    @property
    def ppath(self)->Path:
        """The relative path of this item as a pathlib.Path object"""
        return Path(self._path)

    @property
    def row(self)->int:
        """Which row (relative to its parent) does this item appear on"""
        return self._row

    @row.setter
    def row(self, value:int): self._row = value

    @property
    def hidden(self):
        """Return whether this item is marked as hidden"""
        return self._hidden

    @hidden.setter
    def hidden(self, value):
        self._hidden = value

    @property
    def child_count(self):
        """Number of **direct** children"""
        try:
            return len(self._children)
        except TypeError: # _children is None
            return 0

    @property
    def parent(self):
        """Reference to the parent (containing directory) of this item,
        or None if this is the root item"""
        return self._parent

    def __getitem__(self, row:int):
        """Access children using list notation: thisitem[0]
        Returns none if given an invalid row number or childlist is None"""
        try:
            return self._children[row]
        except (IndexError, TypeError):
            return None

    @property
    def children(self):
        """Returns a list of this item's direct children"""
        return self._children

    def iterchildren(self, recursive = False):
        """
        Obtain an iterator over this FSItem's children
        :param recursive: If False or omitted, yield only this item's direct children. If true, yield each child followed by that child's children, if any
        """
        if recursive:
            for child in self._children:
                yield child
                if child.isdir:
                    yield from child.iterchildren(True)
        else:
            yield from self._children

    def append(self, child:'FSItem'):
        """Add a child FSItem to this instance. Also sets that child's 'row' attribute
        based on its position in the parent's list
        :param child:
        """
        # position after the end of the list, aka where the
        # child is about to be inserted
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
        # for de in os.scandir(join(rel_root, self.path)):
        #     # have to check this before creating the child
        #     # or (obviously) it won't be available during init
        #     isleaf = not isdir(de.path)
        #     child = self.__class__(relpath(de.path, rel_root), de.name, self, isleaf)
        #     # de.is_dir() does not work...something in the test
        #     # file about scandir needing to 'fill d_type', but
        #     # nothing in the docs about why it may not work...
        #     if not isleaf:
        #         child.loadChildren(rel_root)
        #     self.append(child)

        #Easier to use Path objects or even os.walk() than deal with all that crap,
        # and is_dir() not working eliminates what slight
        # performance benefit there would have been...

        rpath = Path(rel_root)
        path = rpath / self.path

        # sort by name  ### TODO: folders first?
        entries = sorted(list(path.iterdir()), key = lambda p: p.name)

        for e in entries: #type: Path
            rel = str(e.relative_to(rpath))
            # using type(self) here to make sure we get an instance of the subclass we're using
            # instead of the base FSItem
            child = type(self)(rel, e.name, self, e.is_dir())
            if e.is_dir():
                child.loadChildren(rel_root, filter)
            self.append(child)


    def __eq__(self, other:'FSItem'):
        """Return true when these 2 items refer to the same relative path.
        Case insensitive. Used to determine file conflicts."""
        return self.lpath == other.lpath


    def __str__(self):
        s="{_class}(name: '{name}', path: '{path}', isdir: {isdir}, hidden: {hidden})".format(
                _class=self.__class__.__name__,
                name=self._name,
                path=self._path,
                isdir= self.isdir,
                hidden=self._hidden)

        return s


class QFSItem(FSItem):
    """FSITem subclass with Qt-specific functionality"""

    # now here's a hack...
    # this is changed by every child when recursively toggling check state;
    # thus its final value will the row of the final child accessed.
    last_row_touched = 0

    # noinspection PyTypeChecker
    def __init__(self, *args, **kwargs):
        super(QFSItem, self).__init__(*args, **kwargs)

        self._checkstate=Qt.Checked# tracks explicit checks
        self.flags = Qt.ItemIsUserCheckable | Qt.ItemIsEnabled
        if self.isdir:
            self.flags |= Qt.ItemIsTristate
            self.icon = QIcon.fromTheme("folder")
        else: #file
            self.flags |= Qt.ItemNeverHasChildren
            self.icon = QIcon.fromTheme("text-plain")

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
        # the "hidden" attribute on the baseclass is what will allow us to save
        # the lists of hidden files to disk, so be sure to set it here;
        # note: only explicitly unchecked items will be marked as hidden here;
        # checked and partially-checked directories will not be hidden
        self._hidden = state == Qt.Unchecked

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
        """
        Modify this item's flags to set it enabled or disabled based on value of boolean
        :param boolean:
        """
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
    #TODO: calculate and inform the user of any file-conflicts that will occur in their mod-setup to help them decide what needs to be hidden.
    # It will probably be necessary to do that asynchronously...somehow...

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
        :param path: the absolute filesystem path to the active mod's data folder
        """
        if path == self.rootpath: return

        self.logger.debug("rootpath = "+path)
        if os.path.exists(path):

            self.beginResetModel() # tells the view to get ready to redisplay its contents

            self.rootpath = path
            # name for this item is never actually seen
            self.rootitem = QFSItem("", "data", None)
            self.rootitem.loadChildren(self.rootpath)

            self.endResetModel()  # tells the view it should get new data from model & reset itself

            # emit notifier signal
            self.rootPathChanged.emit(path)

    def getItem(self, index:QModelIndex) -> QFSItem:
        """Extracts actual item from given index"""
        if index.isValid():
            item = index.internalPointer() #type:QFSItem
            if item: return item
        return self.rootitem

    def columnCount(self, *args, **kwargs) -> int:
        return 1

    def rowCount(self, index:QModelIndex=QModelIndex(), *args, **kwargs) -> int:
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
        """Flags are held at the item level; lookup and return them from the item referred to by the index"""
        item = self.getItem(index)
        return item.itemflags

    def data(self, _index:QModelIndex, role=Qt.DisplayRole):
        """
        We handle DisplayRole to return the filename, CheckStateRole to indicate whether the file has been hidden, and Decoration Role to return different icons for folders and files.
        """

        item = self.getItem(_index)

        if role == Qt.DisplayRole:
            return item.name
        elif role == Qt.CheckStateRole:
            # hides the complexity of the tristate workings
            return item.checkState
        elif role == Qt.DecorationRole:
            return item.icon

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
            # self.dumpsHidden()
            return True
        return super(ModFileTreeModel, self).setData(index, value, role)

    def dumpsHidden(self):
        """Return a string containing the hidden files of this mod in a form suitable
        for serializing to json"""

        hiddens = tree.Tree()
        for child in self.root_item.iterchildren(True): #type: QFSItem
            # skip any fully-checked items
            if child.checkState == Qt.Checked:
                continue

            elif child.checkState == Qt.Unchecked:
                pathparts = [os.path.basename(self.rootpath)]+list(child.ppath.parts[:-1])
                # add unchecked dirs, but do not descend
                if child.isdir:
                    tree.treeInsert(hiddens, pathparts) # todo: don't descend; just mark folder excluded, assume contents
                else:
                    tree.treeInsert(hiddens, pathparts, child.name)

        # return json.dumps(hiddens, indent=1)
        return tree.toString(hiddens)


if __name__ == '__main__':
    from skymodman.managers import ModManager



