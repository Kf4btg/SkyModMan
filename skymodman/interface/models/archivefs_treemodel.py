from functools import lru_cache

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QAbstractItemModel, QModelIndex, QMimeData

from skymodman.utils.archivefs import ArchiveFS, PureCIPath
from skymodman.utils import withlogger

# noinspection PyTypeChecker,PyArgumentList
FOLDER_ICON = QtGui.QIcon.fromTheme("folder")
# noinspection PyTypeChecker,PyArgumentList
FILE_ICON = QtGui.QIcon.fromTheme("text-x-plain")

@withlogger
class ModArchiveTreeModel(QAbstractItemModel):

    DIRFLAGS = (Qt.ItemIsEnabled
                | Qt.ItemIsEditable
                | Qt.ItemIsSelectable
                | Qt.ItemIsDragEnabled
                | Qt.ItemIsDropEnabled
                | Qt.ItemIsUserCheckable
                | Qt.ItemIsTristate)

    FILEFLAGS = (Qt.ItemIsEnabled
                 | Qt.ItemIsSelectable
                 | Qt.ItemIsEditable
                 | Qt.ItemIsDragEnabled
                 | Qt.ItemNeverHasChildren
                 | Qt.ItemIsUserCheckable)


    folder_structure_changed = pyqtSignal()

    def __init__(self, mod_fs, *args, **kwargs):
        """

        :param ArchiveFS mod_fs:
        """
        super().__init__(*args, **kwargs)

        self._fs = mod_fs # type: ArchiveFS
        self._backupfs = mod_fs.mkdupefs()

        self._currentroot_inode = ArchiveFS.ROOT_INODE
        self._currentroot = self._fs.root

        # set of unchecked inodes
        self._unchecked=set()

        # just tracking any functions with lru_caches
        self._caches=[self._sorted_dirlist,
                      self._isdir]

    @property
    def root_inode(self):
        return self._currentroot_inode

    @property
    def root(self):
        return self._currentroot

    ##===============================================
    ## Required Qt Abstract Method Overrides
    ##===============================================

    def rowCount(self, index=QModelIndex(), *args, **kwargs):
        """

        :param index:
        :return: Number of filesystem entries contained by the directory pointed to by `index`
        """
        # super().rowCount(parent, *args, **kwargs)
        # need to return len of dir-inodes list for index
        return len(self._fs.dir_length(self.inode4index(index)))

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        """
        Just one column
        ... for now? todo: maybe add a type column. And/Or a size column?
        """
        return 1

    def index(self, row, col, parent=QModelIndex(), *args, **kwargs) -> QModelIndex:
        """
        Retrieve a QModelIndex for the `row`'th item under the the directory pointed to by `parent`
        :param row:
        :param col:
        :param parent:
        """

        parinode = self.inode4index(parent)

        try:
            chinode = self._sorted_dirlist(parinode)[row]
            return self.createIndex(row, col, chinode)
        except IndexError:
            return QModelIndex()

        # return QModelIndex()

    def parent(self, child_index=QModelIndex()):
        if not child_index.isValid(): return QModelIndex()

        # get the parent path
        parent = self._fs.pathfor(child_index.internalPointer()).parent

        # if parent is "/" return invalid index
        if not parent or parent == self.root:
            return QModelIndex()

        #now we need the parent's parent's path...
        grandpath = parent.parent
        # ...to find index of parent within its directory (by sorted position)
        parent_row = self._sorted_dirlist(self._fs.inodeof(grandpath)).index(parent)

        return self.createIndex(parent_row, 0, parent)


    def data(self, index, role=Qt.DisplayRole):
        """

        :param QModelIndex index:
        :param role:
        :return:
        """
        try:
            inode=self.inode4index(index)
            path=self._fs.pathfor(inode)
            return {
                Qt.DisplayRole:
                    path.name,
                Qt.DecorationRole:
                    (FILE_ICON, FOLDER_ICON)[self._fs.is_dir(path)],
                Qt.CheckStateRole:
                    (Qt.Unchecked, Qt.Checked)[
                        inode == self._currentroot_inode or
                        inode not in self._unchecked]
            }[role]
        except KeyError as ke:
            self.LOGGER << ke

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled

        inode=self.inode4index(index)

        if self._isdir(inode):
            return self.DIRFLAGS
        return self.FILEFLAGS

    # noinspection PyUnresolvedReferences
    def setData(self, index, value, role=None):
        """

        :param QModelIndex index:
        :param value:
        :param role:
        :return:
        """
        if not index.isValid(): return False

        if role == Qt.CheckStateRole:
            inode=self.inode4index(index)

            # toggles the inode's membership in the set;
            # just ignore whatever `value` is
            self._unchecked ^= {inode}
            self.dataChanged.emit(index, index, [role])
            return True

        elif role == Qt.EditRole:
            value = value.strip()
            if not value: return False

            currpath = self.path4index(index)

            if value == currpath.name: return False

            # try:
            self._fs.chname(currpath, value)
            # except Error_EEXIST

            self.dataChanged.emit(index, index)
            return True

        return super().setData(index, value, role)

    ##===============================================
    ## Drag and Drop
    ##===============================================

    def supportedDropActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        return ['text/plain']

    def mimeData(self, indexes):
        """
        This is a single-selection model, so there should only be 1 row getting dragged. And what we're dragging around is simply a text version of the inode for the dragged file.
        :param indexes:
        :return:
        """
        inode = indexes[0].internalPointer()
        mimedata = QMimeData()
        mimedata.setText(str(inode))
        return mimedata

    def dropMimeData(self, data, action, row, column, parent):

        if not parent.isValid():
            # dragging to root...maybe?
            # let's check and deal with it later
            self.logger << "drop-parent invalid"
            return False

        fs = self._fs
        par_inode = parent.internalPointer()
        src_inode = int(data.text())
        src_path = fs.pathfor(src_inode)

        if row == column == -1:
            # this apparently means "dropped directly on parent"
            if fs.is_dir(par_inode):
                fs.move(src_path, fs.pathfor(par_inode))
            else:
                # add as sibling
                fs.move(src_path, fs.pathfor(par_inode).parent)
            return True

        elif row>=0 or column>=0:
            # dropped right before row & column in parent,
            # so assume parent is dir?
            fs.move(src_path, fs.pathfor(par_inode))
            return True

        return False #?



    ##===============================================
    ## Utilities
    ##===============================================

    @lru_cache()
    def _sorted_dirlist(self, inode):
        """
        retrieve the sorted version of a directory's entries. Sub-folders will be listed before files

        :param int inode:
        :rtype: list[PureCIPath]
        """
        dirs=[]
        files=[]
        for p in sorted(self._fs.listdir(inode)):
            if self._fs.is_dir(p):
                dirs.append(p)
            else:
                files.append(p)

        return dirs + files

    @lru_cache(None)
    def _isdir(self, inode):
        return self._fs.is_dir(inode)

    def _invalidate_caches(self, which=None):
        """
        Clear all or specified lru_caches
        :param which: if which is None, then which is actually all. Otherwise, it should be a list of functions that have caches attached
        """
        if which is None:
            which = self._caches

        for c in which:
            c.cache_clear()


    ##===============================================
    ## Translation
    ##===============================================

    def inode4index(self, index) -> int:
        """
        Gets the inode for the path represented by `index`
        :param QModelIndex index:
        :return: inode of the item
        """

        if index.isValid():
            inode=index.internalPointer()
            if inode: return inode
        return self.root_inode

    def path4index(self, index) -> PureCIPath:
        """
        Gets a PureCIPath representation for the item represented by `index`
        :param QModelIndex index:
        :return: path to the item
        """

        if index.isValid():
            path = self._fs.pathfor(index.internalPointer())
            if path: return path
        return self.root

