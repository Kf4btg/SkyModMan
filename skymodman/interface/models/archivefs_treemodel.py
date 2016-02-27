from functools import lru_cache, partial

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, QAbstractItemModel, QModelIndex, QMimeData

from skymodman.constants import OverwriteMode
from skymodman import exceptions
from skymodman.utils.archivefs import ArchiveFS, PureCIPath, CIPath
from skymodman.utils import archivefs, icons, withlogger
from skymodman.interface.widgets.file_exists_dialog import FileExistsDialog


class UndoCmd(QtWidgets.QUndoCommand):
    def __init__(self, type, *args, call_before_redo=None, call_before_undo=None, call_after_redo=None, call_after_undo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = type

        self.begin_redo = call_before_redo
        self.begin_undo = call_before_undo
        self.end_redo = call_after_redo
        self.end_undo = call_after_undo

class TrashCommand(UndoCmd):

    def __init__(self, path, trash_path, *args, **kwargs):
        """

        :param CIPath path:
        :param CIPath trash_path:
        :param dict trash_info:
        """
        super().__init__("trash", "Delete {}".format(path.name), *args, **kwargs)

        self.inode = path.inode
        self.orig_name = path.name
        self.orig_location = PureCIPath(path.parent)
        self.pathfor = type(trash_path).FS.pathfor

        self.trash = trash_path

        self.end = self.end_redo

    @property
    def path(self) -> CIPath:
        return self.pathfor(self.inode)

    def redo(self):
        ## move to trash
        self.begin_redo()
        prefix = 0
        gettname = ("{}_" + self.orig_name).format
        trashname = gettname(prefix)

        tlist = self.trash.ls(conv=str.lower)
        while trashname.lower() in tlist:
            prefix += 1
            trashname = gettname(prefix)

        self.path.rename(self.trash / trashname)

        self.end()

    def undo(self):
        # restore to original location
        self.begin_undo()
        self.path.rename(self.orig_location / self.orig_name)
        self.end()

class MoveCommand(UndoCmd):
    """
    Command for moving a path `source_path` to a different folder `target_path`.
    """

    def __init__(self, source_path,
                 target_path, overwrite=OverwriteMode.PROMPT,
                 *args, **kwargs):
        """

        :param CIPath source_path:
        :param int src_row:
        :param PureCIPath target_dir:
        :param int target_row:
        :param call_begin:
        :param call_end:
        """
        super().__init__("move", "Move {}".format("folder" if source_path.is_dir else "file"), *args, **kwargs)

        print("MoveCommand(", source_path,",", target_path, ")")

        self.getpath = type(source_path).FS.get_path

        # self._name = source_path.name

        # ofile = PureCIPath(source_path)
        self.ow = overwrite

        # tdir = PureCIPath(target_dir)

        self.end=self.end_redo

        self.do_redo = partial(self._domove,
                               str(source_path),
                               str(target_path))
        self.do_undo = partial(self._domove,
                               str(target_path),
                               str(source_path))

    def redo(self):
        self.begin_redo() # emits beginMoveRows
        self.do_redo()
        self.end() # emits endMoveRows

    def undo(self):
        self.begin_undo()
        self.do_undo()
        self.end()

    def _domove(self, src, dest):
        self.getpath(src).rename(dest, self.ow)
        # print("_domove", srcdir, trgdir, sep=", ")
        # src = self.mkpath(srcdir, self._name)
        # except (Error_EEXIST, Error_ENOTEMPTY):
        #     self._on_collision(src, self.mkpath(trgdir, self._name))
        # except Error_ENOTEMPTY:
            # self._prompt_merge(src, self.mkpath(trgdir, self._name))

    # def _on_collision(self, src, target):
    #     d = FileExistsDialog(target, src.is_dir)
    #     if d.exec_():
    #         name = d.new_name
    #         ow = d.overwrite
    #
    #
    #     # print("collision", src, target, sep=", ")
    #     src.replace(target)
    #     # self.mkpath.FS.merge(src, target)
    #
    # def _prompt_merge(self, src, target):
    #     self.mkpath.FS.merge(src, target)




class RenameCommand(UndoCmd):
    def __init__(self, path, new_name, *args, **kwargs):
        super().__init__("rename", "Rename {}".format(path.name), *args, **kwargs)

        self.end = self.end_redo
        self.inode = path.inode

        self.old_name = path.name
        self.new_name = new_name

        self.getpath = type(path).FS.pathfor

    @property
    def path(self):
        return self.getpath(self.inode)

    def redo(self):
        self.begin_redo()
        self.path.chname(self.new_name)
        self.end()

    def undo(self):
        self.begin_undo()
        self.path.chname(self.old_name)
        self.end()

class InsertDirectoryCommand(UndoCmd):
    def __init__(self, dir_path, *args, **kwargs):
        super().__init__("mkdir", "Create Directory", *args, **kwargs)

        self._path = PureCIPath(dir_path)

        self._mkdir = type(dir_path).FS.mkdir
        self._rmdir = type(dir_path).FS.rmdir

    def redo(self):
        self.begin_redo()
        self._mkdir(self._path)
        self.end_redo()

    def undo(self):
        self.begin_undo()
        self._rmdir(self._path)
        self.end_undo()


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

    # noinspection PyTypeChecker,PyArgumentList
    def __init__(self, owner, *args, **kwargs):
        """

        :param ArchiveFS mod_fs:
        :param undostack: QUndoStack instance that any actions performed by the model will be pushed to.
        """
        super().__init__(*args, **kwargs)

        self._fs = owner.structure # type: ArchiveFS
        self._backupfs = self._fs.mkdupefs()

        self._currentroot_inode = ArchiveFS.ROOT_INODE
        self._currentroot = self._fs.rootpath
        self._realroot = self._fs.rootpath

        # Have to keep these in the init() so that they're not
        # garbage collected (which apparently seems to delete them
        # from the entire application...)
        # color = QtGui.QPalette().color(QtGui.QPalette.WindowText)
        self.FOLDER_ICON = icons.get("folder")
        self.FOLDER_OPEN = icons.get("folder-open")
        self.FILE_ICON = icons.get("file")


        # self.FOLDER_ICON = QtGui.QIcon.fromTheme(
        #     "folder")  # type: QtGui.QIcon
        # self.FILE_ICON = QtGui.QIcon.fromTheme(
        #     "text-plain")  # type: QtGui.QIcon

        # set of unchecked inodes
        self._unchecked=set()

        # just tracking any functions with lru_caches
        self._caches=[self._sorted_dirlist,
                      self._isdir]

        # create a 'Trash' folder to use for deletions (and easy restorations)
        self._fs.mkdir("/.trash")
        self.trash = self._fs.get_path("/.trash")

        self.undostack = owner.undostack # type: QtWidgets.QUndoStack

        self._owner = owner

    @property
    def root(self):
        """Return absolute path of the directory that is currently set as the "visible" root of the fs"""
        return self._currentroot

    @root.setter
    def root(self, index):
        """
        Set root item to path derived from `index`
        :param index:
        """
        self._currentroot_inode = index.internalId()
        self._currentroot = self._fs.pathfor(self._currentroot_inode)

    @property
    def root_inode(self):
        return self._currentroot_inode

    @property
    def has_modified_root(self):
        """Returns true if the user has set a new top-level directory"""
        return self._currentroot_inode != 0

    ##===============================================
    ## Required Qt Abstract Method Overrides
    ##===============================================

    def rowCount(self, index=QModelIndex(), *args, **kwargs):
        """

        :param index:
        :return: Number of filesystem entries contained by the directory pointed to by `index`
        """
        try:
            return len(self.path4index(index))
        except archivefs.Error_ENOTDIR:
            # I feel like this shouldn't happen since all file-items have
            # the flag Qt.ItemNeverHasChildren...but it happens, anyway
            return 0

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
        except IndexError as e:
            print("index({}, {}, {}({})): IndexError({})".format(row, col, parentpath, parent.internalId(), e))
            print(self._sorted_dirlist(parentpath))
            # self.LOGGER << "index({}, {}, {}): IndexError".format(row, col, parent.internalId())
            # self.LOGGER << self._sorted_dirlist(parentpath)
            return QModelIndex()

    def parent(self, child_index=QModelIndex()):
        """Get the parent QModelIndex for `child_index`"""

        if not child_index.isValid():
            return QModelIndex()

        # get the parent path
        parent = self.index2path(child_index).sparent

        # if parent is "/" return invalid index
        if parent == self._realroot:
            return QModelIndex()

        # try:
        parent_row = self.row4path(parent)
        # except ValueError:
        #     print("child:", self.index2path(child_index))
        #     print("parent:", parent)
        #     raise

        return self.createIndex(parent_row, 0, parent.inode)

    def flags(self, index):
        """
        Return different values for directories and files
        :param index:
        :return:
        """
        if not index.isValid():
            # the root of the tree (all the empty space below the final item)
            # should be able to accept sub-folders dragged to it
            return Qt.ItemIsEnabled | Qt.ItemIsDropEnabled

        if self._isdir(index.internalId()):
            return self.DIRFLAGS
        return self.FILEFLAGS

    def data(self, index, role=Qt.DisplayRole):
        """

        :param QModelIndex index:
        :param int role:
        """

        if role in {Qt.DisplayRole, Qt.DecorationRole, Qt.CheckStateRole, Qt.EditRole}:

            path = self.path4index(index)

            return {
                Qt.DisplayRole:
                    path.name,
                Qt.EditRole: path.name, # make sure editor keeps current text when opened
                Qt.DecorationRole:
                    self.FILE_ICON if path.is_file else (
                        self.FOLDER_ICON,
                        # self.FOLDER_OPEN)[self.],
                        self.FOLDER_OPEN)[self._owner.is_expanded(index)],
                    # (self.FILE_ICON, self.FOLDER_ICON)[path.is_dir],
                Qt.CheckStateRole:
                    (Qt.Unchecked, Qt.Checked)[
                        path == self.root or
                        path.inode not in self._unchecked]
            }[role]

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
            # noinspection PyUnresolvedReferences
            self.dataChanged.emit(index, index, [role])

            return True

        elif role == Qt.EditRole:
            value = value.strip()
            if not value: return False

            currpath = self.index2path(index)
            parent = currpath.parent

            if value == currpath.name: return False

            ## Create a `Rename` command and push to undo stack
            src_row = self.row4path(currpath)
            trg_row = self.future_row_after_rename(currpath, value)

            call_after_redo = self._end_move
            # need to figure out which action (redo/undo) will move the item
            # down in its parent list; target-row must be adjusted for that case
            if src_row != trg_row:
                redo_md = src_row < trg_row

                print(src_row, "<", trg_row, "=", redo_md)

                call_before_redo = partial(self._begin_move,  # 1 if redo is move-down
                                           src_row, trg_row + redo_md,
                                           parent, parent)

                call_before_undo = partial(self._begin_move, # 1 if undo is move down
                                           trg_row, src_row + (not redo_md),
                                           parent, parent)
            else:
                # there is no movement; item will have same index in parent
                # after move as it had before move
                call_before_redo = call_before_undo = lambda: None
                # and the end callable() must be different, as well
                call_after_redo=partial(self._end_rename, index.internalId())

            self.undostack.push(
                RenameCommand(
                    currpath, value,
                    call_before_redo = call_before_redo,
                    call_before_undo = call_before_undo,
                    call_after_redo  = call_after_redo
                )
            )
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

    def dropMimeData(self, mimedata, action, row, column, parent):

        if not parent.isValid():
            # canDropMimeData should prevent any top-level items
            # being droppable on root, so--in theory--we can just
            # accept any drop action on the root level.
            target_path = self._realroot
        else:
            par_path = self.index2path(parent)
            if row < 0 and par_path.is_file:
                # dropped directly on parent, and 'parent' is not a directory
                target_path = par_path.sparent
            else:
                # either dropped directly on parent or before row,col in parent,
                target_path = par_path

        src_path = self._fs.pathfor(int(mimedata.text()))

        self.move_to_dir(src_path, target_path)
        # self._print_fstree()
        return True

    def canDropMimeData(self, mimedata, action, row, col, parent):
        """

        :param QMimeData mimedata:
        :param Qt.DropAction action:
        :param int row:
        :param int col:
        :param QModelIndex parent:
        :return:
        """

        # print("canDropMimeData({}, {}, {}, {}, {})".format(mimedata, action, row, col, parent.internalId()))

        dragged_inode = int(mimedata.text())
        dragged_path = self._fs.pathfor(dragged_inode)

        if not parent.isValid():
            # print("parent invalid")
            ## target is (the real) root directory, so return True so long as source
            ## was not already a top-level item.
            return dragged_path not in self._realroot
            # return dragged_inode not in self._fs.dir_inodes(self.root_inode)
        else:
            # print("parent valid")
            parpath = self.index2path(parent)

            if row < 0 and parpath.is_file:
                # print("row < 0 & {} is_file".format(parpath))
                # dropped directly on parent, and 'parent' is not a directory
                target = parpath.sparent
            else:
                # either dropped directly on parent or before row,col in parent,
                # doesn't really matter, we just need to add to parent's list
                target = parpath

            # print("dragged =", dragged_path)
            # print("target =", target)

            # can't drop on self or on immediate parent
            if target == dragged_path or dragged_path in target or dragged_path in target.parents:
                # print("returning false")
                return False

        return True
        # print("calling super()")
        # now that we've gone through all that, leave the rest of the decision
            # up to the super class
        # return super().canDropMimeData(mimedata, action, row, col, parent)

    ##===============================================
    ## Path modification
    ##===============================================

    def _begin_move(self, src_row, trg_row, src_parent_path, trg_parent_path):
        """
        Call before an operation that moves a path to a new location.

        :param src_row: Original location within its original parent directory
        :param trg_row: Where it will be placed within the target directory
        :param src_parent_path: The path's original parent
        :param trg_parent_path: The target directory of the move
        """
        print("begin move:", src_row, trg_row, src_parent_path, "=>", trg_parent_path)
        self.beginMoveRows(self.index4path(src_parent_path),
                           src_row, src_row,
                           self.index4path(trg_parent_path),
                           trg_row)

    def _end_move(self):
        """Call after any move operation."""
        self._invalidate_caches(self._sorted_dirlist)
        self.endMoveRows()

    def _end_rename(self, changed_inode):
        """
        Only call this when the renaming of an item does not result in a change to its sorted location within the parent directory.
        :param changed_inode:
        """
        self._invalidate_caches(self._sorted_dirlist)

        idx = self.index4inode(changed_inode)

        # noinspection PyUnresolvedReferences
        self.dataChanged.emit(idx, idx)
        self.folder_structure_changed.emit()

    def _begin_insert(self, parent, row):
        """Call before inserting a new item into directory `parent` at row `row`"""
        # beginInsertRows(parent, first, last)
        self.beginInsertRows(self.index4path(parent), row, row)

    def _end_insert(self):
        """Call after an insertion (new file) operation"""
        # self._fs.mkdir(PureCIPath(parent, name))
        self._invalidate_caches(self._sorted_dirlist)
        self.endInsertRows()

    def _begin_remove(self, parent, row):
        """Call before removing a path from the filesystem; the path to be removed is located at `row` in directory `parent`."""
        self.beginRemoveRows(self.index4path(parent), row, row)

    def _end_remove(self):
        """Call after removing a path from the filesystem."""
        self._invalidate_caches(self._sorted_dirlist)
        self.endRemoveRows()

    def move_to_dir(self, src_path, target_dir):
        """Move the file located at src_path from its current location to within `target_dir`"""


        trg_path = PureCIPath(target_dir, src_path.name)

        self._prepare_move(src_path, trg_path)

    do_op = {
        # do nothing on IGNORE
        OverwriteMode.IGNORE:  lambda s, ss, d: None,
        # merge on MERGE (should only be possible to get MERGE when both src and dest are dirs)
        OverwriteMode.MERGE:   lambda self, s, d: self._begin_merge(s, d),
        OverwriteMode.REPLACE: lambda self, s, d: self._replace(s, d),
        OverwriteMode.PROMPT:  lambda self, s, d: self._move_item(s, d)
    }

    def _prepare_move(self, src_path, dest_path,
                      merging=False, use_mode=OverwriteMode.PROMPT):
        """
        Catch a potential name conflict here and begin merge macro if necessary.
        :param src_path:
        :param dest_path:
        """
        print("_prepare_move:", src_path, dest_path, merging, use_mode)

        if self._fs.exists(dest_path):
            dest_path = self._fs.get_path(dest_path) # get the CIPath version

            if merging:
                if dest_path.is_dir and src_path.is_dir:
                    # skip matching dirs while merging; their contents are
                    # coming up in the list and will be handled appropriately
                    raise exceptions.MergeSkipDir
                elif dest_path.has_children and not src_path.is_dir:
                    # trying to overwrite non-empty dir with file--no can do
                    dlg = FileExistsDialog(dest_path, False,
                                           in_merge_op=merging)
                    if dlg.exec_():
                        # rename should be only option
                        assert dlg.overwrite == OverwriteMode.PROMPT
                        self._move_item(src_path, dlg.new_dest)
                    else:
                        raise exceptions.CancelMerge

                else:
                    # dest is file/empty dir, src is whatever
                    if use_mode & OverwriteMode.REPLACE:
                        self._replace(src_path, dest_path)
                    elif use_mode & OverwriteMode.IGNORE:
                        return None



            dlg = FileExistsDialog(dest_path, src_path.is_dir, in_merge_op=merging)
            if dlg.exec_():
                new_dest = dlg.new_dest # could be same as old dest
                self.do_op[dlg.overwrite](self, src_path, new_dest)
                if merging and dlg.apply_to_all:
                    return dlg.overwrite
        else:
            self._move_item(src_path, dest_path)

        # redundant...but explicit.
        return None

    def _move_item(self, src_path, dest_path, ovwrt = OverwriteMode.PROMPT):
        print("_move_item:", src_path, dest_path, ovwrt)
        src_row = self.row4path(src_path)
        trg_row = self.future_row_after_move(src_path,
                                             self._fs.get_path(dest_path.parent))

        self.undostack.push(
            MoveCommand(src_path, dest_path,
                        call_before_redo=partial(
                            self._begin_move,
                            src_row, trg_row,
                            src_path.parent, dest_path.parent),
                        call_before_undo=partial(
                            self._begin_move,
                            trg_row, src_row,
                            dest_path.parent, src_path.parent),
                        call_after_redo=self._end_move,
                        overwrite=ovwrt
                        ))

    def _replace(self, src, dest):
        """
        Combines a Delete and a Move Command into a single undo action (macro)
        :param src: path to eventually move to destination.
        :param dest: path to be removed and replaced.
        """

        self.undostack.beginMacro("Replace {}".format(dest.name))

        self.delete(self._fs.inodeof(dest))

        self._move_item(src, dest)

        self.undostack.endMacro()

    def _begin_merge(self, src, dst):
        # todo: perform as many move, merge, & replace operations as necessary
        # within the macro to fully merge the directories. IF any further conflicts
        # arise during the process, keep prompting the user for each one unless
        # they check the 'apply to all' box in the conflict-dialog. If the user
        # cancels the operation during the run, only the files moved before that
        # point will be included in the macro.

        print("_begin_merge:", src, dst)
        self.undostack.beginMacro("Merge directories")

        src_dst_pairs = [(sc, dst / sc.relative_to(src)) for sc
                         in self._fs.itertree(src)]

        mode = OverwriteMode.PROMPT
        dirs2delete = list() # list of (hopefully) emptied dirs to remove
        for ps, pd in src_dst_pairs:
            if not ps.exists():
                # this might happen if a directory is moved in full before its
                # contents are encountered in the list
                continue
            # if self._fs.exists(pd) and pd.is_dir and ps.is_dir:
                # skip the matching dirs; their contents are coming up in the list
                # and will be handled appropriately
                # dirs2delete.append(ps)
                # continue
            try:
                stickymode = self._prepare_move(ps, pd, True, mode)

                if stickymode is not None:
                    mode = stickymode
            except exceptions.CancelMerge:
                break
            except exceptions.MergeSkipDir:
                dirs2delete.append(ps)


        # any non-empty directories will be left in place
        for d2d in dirs2delete[::-1]:
            if d2d.is_empty:
                self.delete(d2d.inode)

        if src.is_empty:
            self.delete(src.inode)

        self.undostack.endMacro()


    def create_new_dir(self, parent, name):
        """Create a new directory named `name` inside directory `parent`"""
        new_pos = self.future_row_after_create(name, parent, True)
        self.undostack.push(
            InsertDirectoryCommand(
                parent / name,
                call_before_redo = partial(
                    self._begin_insert,
                    parent, new_pos),
                call_before_undo = partial(
                    self._begin_remove,
                    parent, new_pos),
                call_after_redo = self._end_insert,
                call_after_undo = self._end_remove,
            )
        )

    def delete(self, inode, force=False):
        """
        Actually "move to trash", but delete is shorter
        :param inode:
        :param force:
        """
        ## note: this function is largely redundant with move_to_dir()
        getting_trashed = self._fs.pathfor(inode)
        if getting_trashed in {self.root, self._realroot}:
            return False

        src_row = self.row4path(getting_trashed)
        trg_row = self.future_row_after_move(getting_trashed,
                                             self.trash)

        self.undostack.push(
            TrashCommand(
                getting_trashed,
                self.trash,
                call_before_redo=partial(
                    self._begin_move,
                    src_row, trg_row,
                    getting_trashed.parent,
                    self.trash
                ),
                call_before_undo=partial(
                    self._begin_move,
                    trg_row, src_row,
                    self.trash,
                    getting_trashed.parent,
                ),
                call_after_redo=self._end_move,
            )
        )
        return True

    ##===============================================
    ## Utilities
    ##===============================================

    def validate_mod_structure(self, root_index):
        """
        Check if the directory-tree - as rooted at the path specified by root_index - has valid game_data on its top level.
        :param root_index:
        :return:
        """
        return self._fs.fsck_quick(self.path4index(root_index))

    @lru_cache()
    def _sorted_dirlist(self, dirpath):
        """
        retrieve the sorted version of a directory's entries. Sub-folders will be listed before files

        :param CIPath dirpath:
        :rtype: list[CIPath]
        """
        # let the fs's sorting handle that.
        # use _fs instead of path.listdir() incase dirpath is PureCIPath
        return sorted(self._fs.listdir(dirpath))

    def future_row_after_rename(self, current_path, new_name):
        """ Determine updated row for current_path after it has been renamed to `new_name`
        :param current_path:
        :param new_name:
        :return:
        """
        # get *copy* of file list for current directory, and remove the current path
        flist = self._sorted_dirlist(current_path.parent).copy()
        flist.remove(current_path)

        return self._get_insertion_index(current_path.with_name(new_name), None,
                                         path_is_folder=current_path.is_dir,
                                         use_list=flist)

    def future_row_after_move(self, path, target_dir):
        """
        Determine where in the  directory 'target_dir' `path` will appear if it is moved there.

        :param path:
        :param target_dir:
        :return:
        """
        return self._get_insertion_index(
            PureCIPath(target_dir, path.name),
            target_dir, path.is_dir)

    def future_row_after_create(self, file_name, target_dir, isfolder=False):
        """
         Return the index in target_dir's child list where a file with name `file_name` would be inserted after creation.
         :param file_name:
         :param target_dir:
         :param isfolder: whether the file to be created will be a folder
         :return:
         """
        return self._get_insertion_index(
            PureCIPath(target_dir, file_name),
            target_dir, isfolder)

    def _get_insertion_index(self, path, target_dir, path_is_folder=False, use_list=None):
        """
        Return the index in `target_dir`'s child list where `path` would be inserted.
        :param path:
        :param target_dir:
        :param use_list: if provided, will be used instead of `target_dir`'s contents list for determining insertion point.
        """
        # print("_get_insertion_index({}, {}, {}, {})".format(path, target_dir, path_is_folder, use_list))

        i = -1
        path=PureCIPath(path)
        # return first index where either:
        #    a) path is a folder and the target is not;
        # or b) path and target are the same type (folder|file) && path < p
        # XXX: should we do a binary search here? Or is that unnecessary?

        if use_list is None:
            use_list = self._sorted_dirlist(target_dir)

        for i, p in enumerate(use_list):
            if path_is_folder == p.is_dir:
                if path < p: return i

            # we know that only one of them is a folder; if it's path, return i
            elif path_is_folder: return i

        # if no insertion point found, insert after end
        return i+1

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
        for d, fstat in self._fs.lstree(self._realroot,
                                          include_root=False,
                                          verbose=True):
            print(indent*d,
                  fstat.st_name,
                  {"d":"/", "f":""}[fstat.st_type],
                  sep="")

    # just some convenience functions
    def index_is_dir(self, index):
        return self._isdir(index.internalId())
    def index_is_root(self, index):
        return self._currentroot_inode == index.internalId()
    def inode2path(self, inode):
        """
        convenience function meant to be called from an external source.
        """
        return self._fs.pathfor(inode)

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
        """
        return self._fs.pathfor(index.internalId())

    def index4inode(self, inode):
        # print("index4inode({})".format(inode))
        return QModelIndex() \
            if inode == ArchiveFS.ROOT_INODE \
            else self.createIndex(self.row4inode(inode), 0, inode)

    def index4path(self, path):
        # print("index4path({})".format(path))
        return QModelIndex() \
            if path == self._realroot \
            else self.createIndex(self.row4path(path), 0, self._fs.inodeof(path))

    def row4inode(self, inode):
        """
        Return the sorted position in the inode's parent directory where the inode's current path would appear
        :param inode:
        """
        return self.row4path(self._fs.pathfor(inode))

    def row4path(self, path):
        # print("row4path({})".format(path))
        return self._sorted_dirlist(
            path.parent
        ).index(path)

    ## Convenience functions for using strings
    def index4strpath(self, path):
        return self.index4path(self._fs.get_path(path))

    def row4strpath(self, path):
        return self.row4path(self._fs.get_path(path))
