from PyQt5.QtCore import Qt, QModelIndex, QAbstractItemModel, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon
from typing import List
import itertools

import os
from pathlib import Path

from skymodman.utils import withlogger #, tree
# from skymodman.utils import humanizer

Qt_Checked = Qt.Checked
Qt_Unchecked = Qt.Unchecked
Qt_PartiallyChecked = Qt.PartiallyChecked
Qt_ItemIsTristate = Qt.ItemIsTristate
Qt_CheckStateRole = Qt.CheckStateRole


# @withlogger
# @humanizer.humanize
class FSItem:
    """
    Used to hold information about a real file on the filesystem, including references to its containing directory and any (if it is itself a directory) the files and folders contained within it.
    """

    #Since we may be creating LOTS of these things (some mods have gajiblions of files), we'll define
    # __slots__ to keep the memory footprint as low as possible
    __slots__=("_path", "_lpath", "_name", "_parent", "_isdir", "_children", "_childnames", "_row", "_hidden", "_level", "_hasconflict")

    def __init__(self, *, path, name, parent=None, isdir=True, **kwargs):
        """

        :param str path: a relative path from an arbitray root to this file
        :param str name: the name that will displayed for this file; usually just the basename
        :param parent: this Item's parent, if any. will be None for top-level items
        :param bool isdir: Is this a directory? If not, it will be marked as never being able to hold children
        """
        # noinspection PyArgumentList
        super().__init__(**kwargs)
        self._path = path
        self._lpath = path.lower() # used to case-insensitively compare two FSItems
        self._name = name
        self._parent = parent

        self._isdir = isdir
        if self._isdir:
            self._children = []
            self._childnames = []
        else:
            self._children = None #type: List[FSItem]
            self._childnames = None

        self._row=0

        self._hidden = False

        self._level = len(self.ppath.parts)

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
    def level(self):
        """How deep is this item from the root"""
        return self._level

    @property
    def isdir(self)->bool:
        """Whether this item represents a directory"""
        return self._isdir

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
        return len(self._children) if self._isdir else 0

    @property
    def parent(self):
        """Reference to the parent (containing directory) of this item,
        or None if this is the root item"""
        return self._parent

    def __getitem__(self, item):
        """Access children using list notation: thisitem[0] or thisitem["childfile.nif"]
        Returns none if given an invalid item number/name or childlist is None

        :param int|str item:
        """
        try:
            return self._children[item]
        except TypeError:
            try:
                return self._children[self._childnames.index(item)] # assume string name passed
            except (ValueError, AttributeError):
                return None

    @property
    def children(self):
        """Returns a list of this item's direct children"""
        return self._children

    def iterchildren(self, recursive = False):
        """
        Obtain an iterator over this FSItem's children
        :param recursive: If False or omitted, yield only this item's direct children. If true, yield each child followed by that child's children, if any

        :rtype: __generator[FSItem|QFSItem, Any, None]
        """
        if recursive:
            for child in self._children:
                yield child
                if child.isdir:
                    yield from child.iterchildren(True)
        else:
            yield from self._children

    def loadChildren(self, rel_root, namefilter = None):
        """
        Given a root, construct an absolute path from that root and
        this item's (relative) path. Then scan that path for entries, creating an
        FSItem for each file found and adding it to this item's list of children.
        If the entry found is a directory, then call the loadChildren() method
        of the new FSItem with the same root given here.

        :param str rel_root:
        # :param conflicts: a collection of filepaths (all relative to a mod's 'data' directory) that have been determined to exist in multiple mods; if the name of a loaded file is in this collection, it will be marked as "has_conflict"
        :param (str)->bool namefilter: if given and not none, each filename found will be passed to the `namefilter` callable. If the namefiter returns True, that file will NOT be added to the list of children
        """

        rpath = Path(rel_root)
        path = rpath / self.path

        nfilter = None
        if namefilter:
            nfilter = lambda p:not namefilter(p.name)

        # sort by name  ### TODO: folders first?
        entries = sorted(filter(nfilter, path.iterdir()), key=lambda p:p.name)
                         # , key = lambda p: p.name)
        for r,e in enumerate(sorted(entries, key=lambda p:p.is_file())): #type: int, Path
            rel = str(e.relative_to(rpath))

            # using type(self) here to make sure we get an instance of the subclass we're using
            # instead of the base FSItem
            child = type(self)(path=rel, name=e.name, parent=self, isdir=e.is_dir())
            if e.is_dir():
                child.loadChildren(rel_root, namefilter)
            child.row = r
            # if child.path in conflicts:
            #     child._hasconflict = True
            self._children.append(child)
            self._childnames.append(child.name)

    def __eq__(self, other):
        """Return true when these 2 items refer to the same relative path.
        Case insensitive. Used to determine file conflicts.

        :param FSItem other:
        """
        return self.lpath == other.lpath

    def __str__(self):
        return "\n  {0.__class__.__name__}(name: '{0._name}', " \
               "path: '{0._path}',\n" \
                "    row: {0._row}, " \
                "level: {0._level}, " \
               "isdir: {0._isdir}, " \
               "kids: {0.child_count}, " \
               "hidden: {0._hidden}" \
               ")".format(self)

# @humanizer.humanize
class QFSItem(FSItem):
    """FSITem subclass with Qt-specific functionality"""

    # now here's a hack...
    # this is changed by every child when recursively toggling check state;
    # thus its final value will be the final child accessed.
    last_child_seen = None


    # Since the base class has __slots__, we need to define them here, too, or we'll lose all the benefits.
    # __slots__=FSItem.__slots__+("_checkstate", "flags", "icon")
    __slots__=("_checkstate", "flags", "icon")

    # noinspection PyTypeChecker,PyArgumentList
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._checkstate=Qt_Checked# tracks explicit checks
        self.flags = Qt.ItemIsUserCheckable | Qt.ItemIsEnabled
        if self.isdir:
            self.flags |= Qt_ItemIsTristate
            self.icon = QIcon.fromTheme("folder")
        else: #file
            self.flags |= Qt.ItemNeverHasChildren
            self.icon = QIcon.fromTheme("text-plain")

    @property
    def itemflags(self):
        """Initial flags for all items are Qt.ItemIsUserCheckable and Qt.ItemIsEnabled
        Non-directories receive the Qt.ItemNeverHasChildren flag, and dirs get
        Qt_ItemIsTristate to allow the 'partially-checked' state"""
        return self.flags

    @itemflags.setter
    def itemflags(self, value):
        self.flags = value

    @property
    def checkState(self):
        # if not self.isdir:
        if self.isdir and self.child_count>0:
            return self.childrenCheckState()

        return self._checkstate

    # So, I think the protocol here is, when a directory is un/checked,
    # set the checkstates of all that directory's children to match.
    # here's the python translation of the c++ code from qtreewidget.cpp:

    # Superfancy typechecker doesn't know what its talking about...
    # noinspection PyUnresolvedReferences
    @checkState.setter
    def checkState(self, state):
        QFSItem.last_child_seen = self  # using a class variable, track which items were changed

        # state propagation for dirs:
        # (only dirs can have the tristate flag turned on)
        if self.flags & Qt_ItemIsTristate:
            # propagate a check-or-uncheck down the line:
            for c in self.iterchildren():

                QFSItem.last_row_touched = c.row  # using a class variable, track which items were changed

                # this will trigger any child dirs to do the same
                c.checkState = state
                # c.setEnabled(state == Qt_Checked)

        self._checkstate = state

        # the "hidden" attribute on the baseclass is what will allow us to save
        # the lists of hidden files to disk, so be sure to set it here;
        # note: only explicitly unchecked items will be marked as hidden here;
        # checked and partially-checked directories will not be hidden
        self._hidden = state == Qt_Unchecked

        # add final check for if this was the last unhidden file in a directory:

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
            if s == Qt_PartiallyChecked: return Qt_PartiallyChecked
            elif s == Qt_Unchecked:
                uncheckedkids = True
            else:
                checkedkids = True

            # if we've found both kinds, return partial
            if checkedkids and uncheckedkids:
                return Qt_PartiallyChecked

        return Qt_Unchecked if uncheckedkids else Qt_Checked


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

    def __init__(self, *, manager, parent, **kwargs):
        """

        :param ModManager manager:
        :param kwargs: anything to pass on to base class
        :return:
        """
        # noinspection PyArgumentList
        super().__init__(parent=parent,**kwargs)
        self._parent = parent
        self.manager = manager
        self.rootpath = None #type: str
        self.modname = None #type: str
        self.rootitem = None #type: QFSItem

    @property
    def root_path(self):
        return self.rootpath

    @property
    def root_item(self):
        return self.rootitem

    @property
    def current_mod(self):
        return self.modname

    def setRootPath(self, path):
        """
        Using this instead of a setter just for API-similarity with
        QFileSystemModel. That's the same reason rootPathChanged is emitted
        at the end of the method, as well.

        :param str path: the absolute filesystem path to the active mod's data folder
        """
        if path == self.rootpath: return

        if os.path.exists(path):

            self.beginResetModel() # tells the view to get ready to redisplay its contents

            self.rootpath = path
            self.modname = os.path.basename(path)
            # name for this item is never actually seen
            self.rootitem = QFSItem(path="", name="data", parent=None)
            self.rootitem.loadChildren(self.rootpath, namefilter=lambda n: n.lower()=='meta.ini')

            # now mark hidden files
            hfiles = list(self.manager.hiddenFiles(for_mod=self.modname))
            for c in self.rootitem.iterchildren(True):
                if c.lpath in hfiles:
                    c.checkState = Qt_Unchecked

            self.endResetModel()  # tells the view it should get new data from model & reset itself

            # emit notifier signal
            self.rootPathChanged.emit(path)

    def getItem(self, index) -> QFSItem:
        """Extracts actual item from given index

        :param QModelIndex index:
        """
        if index.isValid():
            item = index.internalPointer()
            if item: return item
        return self.rootitem

    def itemFromPath(self, path_parts):
        """

        :param path_parts: a tuple where each element is an element in the filesystem path
         leading from the root item to the item
        :return: the item
        """
        item = self.rootitem
        for p in path_parts:
            item = item[p]

        return item

    def columnCount(self, *args, **kwargs) -> int:
        """Dir/File Name(+checkbox), path to file, file conflicts """
        # return 2
        return 3

    def rowCount(self, index=QModelIndex(), *args, **kwargs) -> int:
        """Number of children contained by the item referenced by `index`

        :param QModelIndex index:
        """
        # return 0 until we actually have something to show
        if not self.rootitem: return 0
        return self.getItem(index).child_count

    def headerData(self, section, orient, role=None):
        """Just one column, 'Name'. super() call should take care of the
        size hints &c.

        :param int section:
        :param orient:
        :param role:
        """
        if orient == Qt.Horizontal and role==Qt.DisplayRole:
            return ["Name", "Path", "Conflicts"][section]
            # return "Name"
        return super().headerData(section, orient, role)

    def index(self, row, col, parent=QModelIndex(), *args, **kwargs) -> QModelIndex:
        """

        :param int row:
        :param int col:
        :param QModelIndex parent:
        :return: the QModelIndex that represents the item at (row, col) with respect
                 to the given  parent index. (or the root index if parent is invalid)
        """

        parent_item = self.rootitem
        if parent.isValid():
            parent_item = parent.internalPointer()

        child = parent_item[row]
        if child:
            return self.createIndex(row, col, child)

        return QModelIndex()

    def getIndexFromItem(self, item) -> QModelIndex:
        return self.createIndex(item.row, 0, item)

    # noinspection PyArgumentList
    @pyqtSlot('QModelIndex',name="parent", result = 'QModelIndex')
    def parent(self, child_index=QModelIndex()):
        if not child_index.isValid(): return QModelIndex()

        # get the parent FSItem from the reference stored in each FSItem
        parent = child_index.internalPointer().parent

        if not parent or parent is self.rootitem:
            return QModelIndex()

        # Every FSItem has a row attribute which we use to create the index
        return self.createIndex(parent.row, 0, parent)

    # noinspection PyArgumentList
    @pyqtSlot(name='parent', result='QObject')
    def parent_of_self(self):
        return self._parent

    def flags(self, index):
        """Flags are held at the item level; lookup and return them from the item referred to by the index

        :param QModelIndex index:
        """
        # item = self.getItem(index)
        return self.getItem(index).itemflags

    def data(self, index, role=Qt.DisplayRole):
        """
        We handle DisplayRole to return the filename, CheckStateRole to indicate whether the file has been hidden, and Decoration Role to return different icons for folders and files.

        :param QModelIndex index:
        :param role:
        """

        item = self.getItem(index)

        if index.column() == 1:
            if role == Qt.DisplayRole: #second column is path
                return item.parent.path + "/"

        elif index.column()==2: # third column is conflicts
            if role == Qt.DisplayRole \
                    and self.modname in self.manager.DB.mods_with_conflicts \
                    and item.lpath in self.manager.DB.conflicts:
                return "Yes"


        else:
            if role == Qt.DisplayRole:
                return item.name
            elif role == Qt_CheckStateRole:
                # hides the complexity of the tristate workings
                return item.checkState
            elif role == Qt.DecorationRole:
                return item.icon

    # noinspection PyTypeChecker
    def setData(self, index, value, role=Qt_CheckStateRole):
        """Only the checkStateRole can be edited in this model.
        Most of the machinery for that is in the QFSItem class

        :param QModelIndex index:
        :param value:
        :param role:
        """
        if not index.isValid(): return

        item = self.getItem(index)
        if role==Qt_CheckStateRole:

            item.checkState = value #triggers cascade if this a dir

            # if this item is the last checked/unchecked item in a dir,
            # make sure the change is propagated up through the parent
            # hierarchy, to make sure that no folders remain checked
            # when none of their descendants are.
            ancestor = self._getHighestAffectedAncestor(item, value)

            if ancestor is not item:
                index1 = self.getIndexFromItem(ancestor)
            else:
                index1 = index

            # using the "last_child_seen" value--which SHOULD be the most
            # "bottom-right" child that was just changed--to feed to
            # datachanged saves a lot of individual calls. Hopefully there
            # won't be any concurrency issues to worry about later on.
            self._sendDataThroughProxy(index1, self.getIndexFromItem(QFSItem.last_child_seen))
            # self.logger << "Last row touched: {}".format(QFSItem.last_row_touched)

            # self.dumpsHidden()
            self.commit() # update the db with which files are now hidden

            return True
        return super().setData(index, value, role)

    def _getHighestAffectedAncestor(self, item, value):
        if item.parent and item.parent.childrenCheckState() == value:
            return self._getHighestAffectedAncestor(item.parent, value)
        else:
            return item

    # noinspection PyUnresolvedReferences
    def _sendDataThroughProxy(self, index1, index2, *args):
        proxy = self._parent.model()
        """:type: PyQt5.QtCore.QSortFilterProxyModel.QSortFilterProxyModel"""

        proxy.dataChanged.emit(proxy.mapFromSource(index1), proxy.mapFromSource(index2), *args)

    def saveHidden(self):
        self.manager.DB.saveHiddenFiles(self.manager.active_profile.hidden_files)

    # def dumpsHidden(self):
    #     """Return a string containing the hidden files of this mod in a form suitable
    #     for serializing to json"""
    #
    #     hiddens = tree.Tree()
    #     for child in self.root_item.iterchildren(True): #type: QFSItem
    #         # skip any fully-checked items
    #         if child.checkState == Qt_Checked:
    #             continue
    #
    #         elif child.checkState == Qt_Unchecked:
    #             pathparts = [os.path.basename(self.rootpath)]+list(child.ppath.parts[:-1])
    #             # add unchecked dirs, but todo: do not descend
    #             if child.isdir:
    #                 tree.treeInsert(hiddens, pathparts) # todo: don't descend; just mark folder excluded, assume contents
    #             else:
    #                 tree.treeInsert(hiddens, pathparts, child.name)
    #
    #     # return json.dumps(hiddens, indent=1)
    #     return tree.toString(hiddens)

    def commit(self):
        """Commit changes to database"""
        directory = os.path.basename(self.rootpath)
        ffalse = itertools.filterfalse

        dbconn = self.manager.DB.conn
        # here's a list of the CURRENTLY hidden filepaths for this mod, as known to the database
        nowhiddens = [r["filepath"] for r in
                      dbconn.execute("SELECT * FROM hiddenfiles WHERE directory=?",
                                     (directory, ))]

        # let's forget all that silly complicated stuff and do this:
        hiddens, unhiddens = self._getHiddenStates(len(nowhiddens)>0)

        if nowhiddens:
            # to remove will be empty if either of now/un-hiddens is empty
            toremove = list(filter(unhiddens.__contains__, nowhiddens))

            # don't want to add items twice, so remove any already in db
            # (not quite sure how that would happen...but let's play it safe for now)
            toadd = list(ffalse(nowhiddens.__contains__, hiddens))
        else:
            toremove = []
            toadd = hiddens

        # self.LOGGER << len(toremove)
        # limit the size of the query strings we send to the DB
        maxatonce=900 # max number of vars for sqlite query is 999
        if toremove:
            q = """DELETE FROM hiddenfiles WHERE directory = "{}" AND filepath IN ({})"""

            sections, remainder = divmod(len(toremove),maxatonce)
            for i in range(sections):
                s=maxatonce*i
                query = q.format(directory, ", ".join(['?']*maxatonce))

                self.manager.DB.update_(query,toremove[s:s+maxatonce])

            if remainder:
                query = q.format(directory, ", ".join(['?']*remainder))

                self.manager.DB.update_(query, toremove[sections*maxatonce:])

        if toadd:
            self.manager.DB.updatemany_("INSERT INTO hiddenfiles values (?, ?)", ((directory,a) for a in toadd))


        self.saveHidden()
            # with self.manager.DB.conn:
        #     for r in self.manager.DB.conn.execute("select * from hiddenfiles"): #type: Row
        #         print(r["directory"]," | ", r["filepath"])

    def _getHiddenStates(self, track_unhidden = True):
        """Maybe straightforward is better than stupidly complex. Who'd have thought.

        :param bool track_unhidden: whether we care about tracking unhidden files; For example, if the hiddenfiles database table has no entries for this mod, we wouldn't care because there's nothing to reset
        """
        hBasket=[]   #holds hidden files
        uhBasket=[]  #holds non-hidden files

        def _(base):
            for child in base.iterchildren():
                cs = child.checkState
                if cs==Qt_PartiallyChecked:
                    # this is a directory, we need to go deeper
                    _(child)

                elif cs==Qt_Unchecked:
                    if child.isdir:
                        # if we found an unchecked folder, just add all its children
                        hBasket.extend(c.lpath for c in child.iterchildren(True) if not c.isdir)
                    else:
                        hBasket.append(child.lpath)

                elif track_unhidden:
                    if child.isdir:
                        uhBasket.extend(c.lpath for c in child.iterchildren(True) if not c.isdir)
                    else:
                        uhBasket.append(child.lpath)


        _(self.root_item)
        return hBasket, uhBasket


if __name__ == '__main__':
    from skymodman.managers import ModManager
    # noinspection PyUnresolvedReferences
    from sqlite3 import Row




