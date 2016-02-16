from functools import lru_cache

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QAbstractItemModel, QModelIndex, QMimeData

from skymodman.utils.archivefs import ArchiveFS, PureCIPath, CIPath
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

        # print([(i, p.str) for i,p in enumerate(self._fs.i2p_table)])

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

        # if not index.isValid():
        #     return self.root.dir_length()
        #
        # return inde
        # return self._fs.dir_length(index.internalId())


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
        if not parent.isValid():
            # I'm not sure this will ever happen, so let's watch for it:
            # edit: it happens...
            # self.LOGGER << "index: parent is invalid"
            parent = self.root
        else:
            parent = parent.internalPointer()


        try:
            # print(type(parent))
            # print(type(parent).FS)
            print("  parent:", "--", parent)
            dirlist = self._sorted_dirlist(parent)
            print(dirlist)
            child = dirlist[row]
            print("child:", child)
            # child = self._sorted_dirlist(parent)[row]
            # child = self._fs.listdir(parinode)[row]

            # using an int for the third argument makes it internalId(),
            # not internalPointer()
            return self.createIndex(row, col, child)
        except IndexError:
            return QModelIndex()

        # return QModelIndex()




    def parent(self, child_index=QModelIndex()):

        if not child_index.isValid():
            return QModelIndex()

        # get the parent path
        parent = child_index.internalPointer().sparent
        # parent = self._fs.pathfor(child_index.internalId()).parent

        # if parent is "/" return invalid index
        if parent == self.root:
            return QModelIndex()

        #now we need the parent's parent's path...
        grandpath = parent.sparent
        # ...to find index of parent within its directory (by sorted position)

        try:
            # parent_row = self._sorted_dirlist(self._fs.inodeof(grandpath)).index(parent)
            parent_row = self._sorted_dirlist(grandpath).index(parent)
        except ValueError:
            print("child:", self.path4index(child_index))
            print("parent:", parent)
            print("gp:", grandpath)
            print("dirlist:",
                  self._sorted_dirlist(grandpath))
            raise

        return self.createIndex(parent_row, 0, parent)


    def data(self, index, role=Qt.DisplayRole):
        """

        :param QModelIndex index:
        :param role:
        :return:
        """

        if role in (Qt.DisplayRole, Qt.DecorationRole, Qt.CheckStateRole):

            # inode=index.internalId()
            # path=self._fs.pathfor(inode)
            path = self.path4index(index)
            return {
                Qt.DisplayRole:
                    path.name,
                Qt.DecorationRole:
                    (FILE_ICON, FOLDER_ICON)[path.is_dir],
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
            return Qt.ItemIsEnabled

        if index.internalPointer().is_dir:
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
            self._unchecked ^= {index.internalPointer().inode}
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
        This is a single-selection model, so there should only be 1 row getting dragged.

        And what we're dragging around is simply a text version of the inode for the dragged file.
        :param indexes:
        :return:
        """
        mimedata = QMimeData()
        mimedata.setText(str(indexes[0].internalPointer().inode))
        return mimedata

    def dropMimeData(self, data, action, row, column, parent):

        if not parent.isValid():
            # dragging to root...maybe?
            # let's check and deal with it later
            self.logger << "drop-parent invalid"
            return False

        # fs = self._fs
        # par_inode = parent.internalId()
        par_path = parent.internalPointer()
        # src_inode = int(data.text())
        src_path = self._fs.pathfor(int(data.text()))
        orig_parent = src_path.sparent

        # if row < 0 and not self._isdir(par_inode):
        if row < 0 and par_path.is_file:
            # dropped directly on parent, and 'parent' is not a directory
            tpath = par_path.parent
            # tpath = fs.pathfor(par_inode).parent
            # tinode = fs.inodeof(tpath)
        else:
            # either dropped directly on parent or before row,col in parent,
            # tinode = par_inode
            # tpath = fs.pathfor(par_inode)
            tpath = par_path

        r = self.row4path(src_path)
        # src_parent, srcFirst, srcLast, destParent, int destChild
        self.beginMoveRows(self.index4path(orig_parent),
                           r, r, self.index4path(tpath),
                           self.future_row(src_path, tpath))

        print("beginmoverows:", ", ".join([orig_parent, r, r, tpath,
         self.future_row(src_path, tpath)]))

        # fs.move(src_path, fs.pathfor(par_inode))
        src_path.move(tpath)
        # fs.move(src_path, tpath)

        self.endMoveRows()

        self._invalidate_caches([self._sorted_dirlist])

        self._print_fstree()
        return True



        # print("dropped {}::{} on {}::{}".format(
        #     src_inode, src_path, par_inode, self._fs.pathfor(par_inode)
        # ))

        # if row < 0:

        # this apparently means "dropped directly on parent"
        # self.LOGGER << "Dropped directly on parent"
        # if fs.is_dir(par_inode):
        # tinode = par_inode
        # tpath = fs.pathfor(par_inode)
        # fs.move(src_path, fs.pathfor(par_inode))
        # else:
        # add as sibling

        # fs.move(src_path, fs.pathfor(par_inode).parent)

        # self._invalidate_caches([self._sorted_dirlist])
        # self._print_fstree()
        # return True
        # self.LOGGER << "dropped before r{}c{} in {}".format(row, column, self._fs.pathfor(par_inode))
        # dropped right before row & column in parent,
        # so assume parent is dir?
        # self.LOGGER << "dropMimeData: end, return False"
        # return False #?

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
            # parinode = self.root_inode
            # target = self.root_inode
            ## target is root directory, so return True so long as source
            ## was not already a top-level item.
            return dragged_inode not in self._fs.dir_inodes(self.root_inode)
        else:
            parpath = parent.internalPointer()

            if row < 0 and parpath.is_file():
                # dropped directly on parent, and 'parent' is not a directory
                target = parpath.sparent
                # pp = parent.parent()
                # target = self.path4index(pp)
                # target = pp.internal() if pp.isValid() else self.root_inode

            else:
                # either dropped directly on parent or before row,col in parent,
                # doesn't really matter, we just need to add to parent's list
                target = parpath

            # can't drop on self or on immediate parent
            if target == dragged_path or \
                dragged_inode in self._fs.dir_inodes(target):
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
        :rtype: list[PureCIPath]
        """
        # let the fs's sorting handle that.
        return sorted(dirpath.listdir())


        # dirs=[]
        # files=[]
        # for p in sorted(self._fs.listdir(inode)):
        #     if self._fs.is_dir(p):
        #         dirs.append(p)
        #     else:
        #         files.append(p)
        #
        # return dirs + files

    def future_row(self, path, newdir):
        """
        Determine where in the target directory 'newdir' `path` will appear if it is moved there.

        :param path:
        :param newdir:
        :return:
        """
        dirs = []
        files = []
        for p in self._fs.listdir(newdir):
            if self._fs.is_dir(p):
                dirs.append(p)
            else:
                files.append(p)

        newpath = PureCIPath(newdir, path.name)
        dirs.append(newpath) if self._fs.is_dir(path) else files.append(
            newpath)

        allfiles = sorted(dirs) + sorted(files)

        return allfiles.index(newpath)

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

    def _print_fstree(self):
        indent="  "
        for d,p,t in self._fs.itertree2(include_root=False):
            print(indent*d,
                  p.name,
                  {"d":"/", "f":""}[t],
                  sep="")


    ##===============================================
    ## Translation
    ##===============================================

    # def inode4index(self, index) -> int:
    #     """
    #     Gets the inode for the path represented by `index`
    #     :param QModelIndex index:
    #     :return: inode of the item
    #     """
    #     return index.internalId() if index.isValid() else self.root_inode


    def path4index(self, index) -> CIPath:
        """
        Gets a PureCIPath representation for the item represented by `index`
        :param QModelIndex index:
        :return: path to the item
        """
        return index.internalPointer() if index.isValid() else self.root

    def index4inode(self, inode):
        return self.index4path(self._fs.pathfor(inode))
        # if inode == self.root.inode:
        #     return QModelIndex()
        #
        # row = self.row4inode(inode)
        #
        # return self.createIndex(row, 0, self._fs.pathfor(inode))

    def index4path(self, path):
        if path == self.root:
            return QModelIndex()
        row = self.row4path(path)
        return self.createIndex(row, 0, path)

    def row4inode(self, inode):
        """
        Return the sorted position in the inode's parent directory where the inode's current path would appear
        :param inode:
        :return:
        """
        path = self._fs.pathfor(inode)
        return self.row4path(path)

    def row4path(self, path):
        """
        :param path:
        :return:
        """
        return self._sorted_dirlist(
            path.sparent
            # self._fs.inodeof(path.parent)
        ).index(path)

