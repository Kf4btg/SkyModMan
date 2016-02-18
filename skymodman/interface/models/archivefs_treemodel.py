from functools import lru_cache

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QAbstractItemModel, QModelIndex, QMimeData

from skymodman.utils.archivefs import ArchiveFS, PureCIPath, CIPath
from skymodman.utils import archivefs
from skymodman.utils import withlogger



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
        self._currentroot = self._fs.rootpath

        # noinspection PyTypeChecker,PyArgumentList
        self.FOLDER_ICON = QtGui.QIcon.fromTheme(
            "folder")  # type: QtGui.QIcon
        # noinspection PyTypeChecker,PyArgumentList
        self.FILE_ICON = QtGui.QIcon.fromTheme(
            "text-plain")  # type: QtGui.QIcon

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
        return self.path4index(index).dir_length()

    def columnCount(self, *args, **kwargs):
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

        parentpath = self.path4index(parent)

        try:
            child = self._sorted_dirlist(parentpath)[row]

            # print("index(): creating index({0}, {1}, {2.inode}) for {2}".format(row, col, child))

            # using an int for the third argument makes it internalId(),
            # not internalPointer()
            return self.createIndex(row, col, child.inode)
        except IndexError:
            self.LOGGER << "index({}, {}, {}): IndexError".format(row, col, parent.internalId())
            # self.LOGGER << self._sorted_dirlist(parentpath)
            return QModelIndex()

    def parent(self, child_index=QModelIndex()):

        if not child_index.isValid():
            return QModelIndex()

        # get the parent path
        parent = self.index2path(child_index).sparent

        # if parent is "/" return invalid index
        if parent == self.root:
            return QModelIndex()

        try:
            parent_row = self.row4path(parent)
        except ValueError:
            print("child:", self.index2path(child_index))
            print("parent:", parent)
            raise

        return self.createIndex(parent_row, 0, parent.inode)


    def data(self, index, role=Qt.DisplayRole):
        """

        :param QModelIndex index:
        :param role:
        :return:
        """

        if role in {Qt.DisplayRole, Qt.DecorationRole, Qt.CheckStateRole}:

            path = self.path4index(index)

            return {
                Qt.DisplayRole:
                    path.name,
                Qt.DecorationRole:
                    (self.FILE_ICON, self.FOLDER_ICON)[path.is_dir],
                Qt.CheckStateRole:
                    (Qt.Unchecked, Qt.Checked)[
                        path == self.root or
                        path.inode not in self._unchecked]
            }[role]


    def flags(self, index):
        """
        Return different values for directories and files
        :param index:
        :return:
        """
        if not index.isValid():
            return Qt.ItemIsEnabled | Qt.ItemIsDropEnabled

        if self._isdir(index.internalId()):
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
        if not index.isValid():
            self.LOGGER << "setData: invalid index"
            return False

        if role == Qt.CheckStateRole:
            # toggles the inode's membership in the set;
            # just ignore whatever `value` is
            self._unchecked ^= {index.internalId()}
            self.dataChanged.emit(index, index, [role])
            return True

        elif role == Qt.EditRole:
            value = value.strip()
            if not value: return False

            currpath = self.index2path(index)

            if value == currpath.name: return False

            # try:
            self._fs.chname(currpath, value)
            # except Error_EEXIST

            self._invalidate_caches(self._sorted_dirlist)

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
        This is a single-selection model, so there should only be 1 row getting dragged.

        And what we're dragging around is simply a text version of the inode for the dragged file.
        :param indexes:
        :return:
        """
        mimedata = QMimeData()
        mimedata.setText(str(indexes[0].internalId()))
        return mimedata

    def dropMimeData(self, data, action, row, column, parent):

        if not parent.isValid():
            # canDropMimeData should prevent any top-level items
            # being droppable on root, so--in theory--we can just
            # accept any drop action on the root level.
            target_path = self.root
        else:
            par_path = self.index2path(parent)
            if row < 0 and par_path.is_file:
                # dropped directly on parent, and 'parent' is not a directory
                target_path = par_path.sparent
            else:
                # either dropped directly on parent or before row,col in parent,
                target_path = par_path

        src_path = self._fs.pathfor(int(data.text()))
        orig_parent = src_path.sparent

        r = self.row4path(src_path)
        # src_parent, srcFirst, srcLast, destParent, int destChild
        self.beginMoveRows(self.index4path(orig_parent),
                           r, r,
                           self.index4path(target_path),
                           self.future_row(src_path, target_path))

        # self.logger.debug(
        #     "beginmoverows:", ", ".join(
        #         [orig_parent.str,
        #          str(r),
        #          str(r),
        #          tpath.str,
        #          str(self.future_row(src_path, tpath))]))

        src_path.move(target_path)

        ## need to do this BEFORE endmoverows (which calls index()) to
        ## prevent inconsistent state and possible crash
        self._invalidate_caches(self._sorted_dirlist)

        self.endMoveRows()

        self._print_fstree()
        return True

    def canDropMimeData(self, data, action, row, col, parent):
        """

        :param QMimeData data:
        :param Qt.DropAction action:
        :param int row:
        :param int col:
        :param QModelIndex parent:
        :return:
        """

        dragged_inode = int(data.text())
        dragged_path = self._fs.pathfor(dragged_inode)

        if not parent.isValid():
            ## target is root directory, so return True so long as source
            ## was not already a top-level item.
            return dragged_path not in self.root
            # return dragged_inode not in self._fs.dir_inodes(self.root_inode)
        else:
            parpath = self.index2path(parent)

            if row < 0 and parpath.is_file:
                # dropped directly on parent, and 'parent' is not a directory
                target = parpath.sparent
            else:
                # either dropped directly on parent or before row,col in parent,
                # doesn't really matter, we just need to add to parent's list
                target = parpath

            # can't drop on self or on immediate parent
            if target == dragged_path or dragged_path in target:
                # or on child directory...do I need to check for that one? how?
                return False

        # now that we've gone through all that, leave the rest of the decision
            # up to the super class
        return super().canDropMimeData(data, action, row, col, parent)


    ##===============================================
    ## Utilities
    ##===============================================

    @lru_cache()
    def _sorted_dirlist(self, dirpath):
        """
        retrieve the sorted version of a directory's entries. Sub-folders will be listed before files

        :param CIPath dirpath:
        :rtype: list[CIPath]
        """
        # let the fs's sorting handle that.
        return sorted(dirpath.listdirpaths())


    class _FakeCIPath(PureCIPath):
        """
        Just exists so that we can figure out the comparison below. Implements only the methods necessary for passing the checks in __lt__
        """

        def __new__(cls, *args, original, targetdir, **kwargs):
            self = cls._from_parts(args, init=False)

            self.original = original
            self.sparent = targetdir


            self.__lt__ = original.__lt__

            return self

        @property
        def inode(self):
            return self.original.inode

        @property
        def _accessor(self):
            return self.original._accessor

        @property
        def is_dir(self):
            return self.original.is_dir


    def future_row(self, path, newdir):
        """
        Determine where in the target directory 'newdir' `path` will appear if it is moved there.

        :param path:
        :param newdir:
        :return:
        """

        targetlist = newdir.listdirpaths()

        newpath = self._FakeCIPath(newdir, path.name, original=path, targetdir=newdir)

        targetlist.append(newpath)

        return sorted(targetlist).index(newpath)

    @lru_cache(None)
    def _isdir(self, inode):
        return self._fs.is_dir(inode)

    def _invalidate_caches(self, *which):
        """
        Clear all or specified lru_caches
        :param which: if which is None, then which is actually all. Otherwise, it should be a list of functions that have caches attached
        """
        if not which:
            which = self._caches

        for c in which:
            c.cache_clear()

    def _print_fstree(self):
        indent="  "
        for d, fstat in self._fs.itertree(self.root,
                                          include_root=False,
                                          verbose=True):
            print(indent*d,
                  fstat.st_name,
                  {"d":"/", "f":""}[fstat.st_type],
                  sep="")


    ##===============================================
    ## Translation
    ##===============================================

    def path4index(self, index) -> CIPath:
        """
        Gets a PureCIPath representation for the item represented by `index`
        :param QModelIndex index:
        :return: path to the item
        """
        # return index.internalPointer() if index.isValid() else self.root
        return self._fs.pathfor(index.internalId()
                                ) if index.isValid() else self.root

    def index2path(self, index):
        """
        Like path4index, but has no check for index.isValid()
        :param index:
        :return:
        """
        return self._fs.pathfor(index.internalId())

    def index4inode(self, inode):
        return QModelIndex() \
            if inode == self.root_inode \
            else self.createIndex(self.row4inode(inode), 0, inode)

    def index4path(self, path):
        return QModelIndex() \
            if path==self.root \
            else self.createIndex(self.row4path(path), 0, path.inode)

    def row4inode(self, inode):
        """
        Return the sorted position in the inode's parent directory where the inode's current path would appear
        :param inode:
        :return:
        """
        return self.row4path(self._fs.pathfor(inode))

    def row4path(self, path):
        """
        :param path:
        :return:
        """
        return self._sorted_dirlist(
            path.sparent
        ).index(path)

