# from os.path import splitext

# from PyQt5.QtCore import Qt
from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QDialog, QMenu, \
    QInputDialog  #, QTreeWidgetItem
from PyQt5 import QtWidgets

# from skymodman.constants import TopLevelDirs_Bain, TopLevelSuffixes
from skymodman.interface.designer.uic.archive_structure_ui import Ui_mod_structure_dialog
from skymodman.interface.models.archivefs_treemodel import ModArchiveTreeModel
from skymodman.utils import withlogger

# from skymodman.utils.tree import Tree

_description = """Arrange the directory structure of the archive shown to the right into the proper structure for installation, then click "OK" to install the mod."""

_bad_package_desc = """This mod does not appear to have been packaged correctly. Please rearrange the directory structure to the right to place the game data on the top level of the mod, then click "OK" to continue."""

_tree_tooltip = """Drag files and folders to rearrange.
Uncheck items to exclude them from installation.
Right click to set top-level directory or create a new folder."""

@withlogger
class ManualInstallDialog(QDialog, Ui_mod_structure_dialog):

    def __init__(self, mod_fs, *args, **kwargs):
        """

        :param skymodman.utils.archivefs.ArchiveFS mod_fs: An instance of an ArchiveFS pseudo-filesystem.

        :param args: passed to base class constructors
        :param kwargs: passed to base class constructors
        :return:
        """
        super().__init__(*args, **kwargs)
        self.LOGGER << "init manual install dlg"

        self.setupUi(self)

        self.structure = mod_fs
        # self.mod_data = Tree()
        self.num_to_copy = 0

        # self.valid_structure = True
        # self.data_root = self.structure.root

        self.undostack = QtWidgets.QUndoStack()

        self.undoaction = self.undostack.createUndoAction(self, "Undo")
        self.undoaction.pyqtConfigure(shortcut=QKeySequence.Undo,
                                      triggered=self.undo)

        self.redoaction = self.undostack.createRedoAction(self, "Redo")
        self.redoaction.pyqtConfigure(shortcut=QKeySequence.Redo,
                                      triggered=self.redo)

        self.undoview = QtWidgets.QUndoView(self.undostack)
        self.undoview.show()
        self.undoview.setAttribute(Qt.WA_QuitOnClose, False)

        self.modfsmodel = ModArchiveTreeModel(mod_fs, self.undostack)

        self.mod_structure_view.setModel(self.modfsmodel)
        self.mod_structure_view.customContextMenuRequested.connect(
            self.custom_context_menu)

        # here's the custom menu (actions will be made in/visible as required)
        self.rclickmenu = QMenu(self.mod_structure_view)

        self.rclickmenu.addActions([self.action_unset_top_level_directory,
                         self.action_set_as_top_level_directory,
                         self.action_rename,
                         self.action_delete,
                         self.action_create_directory])

        self.rclicked_inode = None

        ## conect actions
        self.action_set_as_top_level_directory.triggered.connect(
            self.set_toplevel)
        self.action_unset_top_level_directory.triggered.connect(
            self.unset_toplevel)
        self.action_rename.triggered.connect(self.rename)
        self.action_create_directory.triggered.connect(self.create_dir)
        self.action_delete.triggered.connect(self.delete_file)

        ## connect some more signals
        # self.modfsmodel.root_changed.connect(self.)

        # self.mod_structure_view.tree_structure_changed.connect(self.on_tree_change)

        # have the tree widget create the visible tree from the
        # data-tree stored in self.structure; this will trigger
        # the validation check and update the UI accordingly
        # self.mod_structure_view.init_tree(self.structure)

        self.mod_structure_view.setToolTip(_tree_tooltip)

        self.modfsmodel.rowsMoved.connect(self.check_top_level)
        self.modfsmodel.rowsInserted.connect(self.check_top_level)
        self.modfsmodel.folder_structure_changed.connect(self.check_top_level)

        ## Hide the Trash folder
        self.mod_structure_view.setRowHidden(
            self.modfsmodel.row4path(self.modfsmodel.trash),
            self.mod_structure_view.rootIndex(), # should still be "/" at this point
            True)




    @property
    def fsroot(self) -> QModelIndex:
        """
        Return the index of the current visible root
        """
        return self.mod_structure_view.rootIndex()

    @fsroot.setter
    def fsroot(self, index: QModelIndex):
        """
        Set the visible root to the path pointed to by `index`
        """
        self.mod_structure_view.setRootIndex(index)
        self.modfsmodel.root = index
        self.check_top_level()

    def set_toplevel(self, *args):
        """
        Set the visible root to the target of the last context-menu-event
        """
        self.LOGGER << "set_toplevel()"
        self.fsroot = self.modfsmodel.index4inode(self.rclicked_inode)


    def unset_toplevel(self, *args):
        """
        Reset the visible root to the default root for the fs.
        :param args:
        :return:
        """
        self.LOGGER << "unset_toplevel()"
        self.fsroot = QModelIndex()


    def rename(self, *args):
        # self.LOGGER << "rename()"
        self.mod_structure_view.edit(
            self.modfsmodel.index4inode(self.rclicked_inode))

    def create_dir(self, *args):
        """
        Create a new directory as a sibling (if the clicked item was a file) or child (if it was a folder) of the target of the last context-menu event, and open its name-editor.
        :param args:
        :return:
        """

        # self.LOGGER << "create_dir()"
        fsmod = self.modfsmodel

        if fsmod._isdir(self.rclicked_inode):
            parent = fsmod.inode2path(self.rclicked_inode)
        else:
            parent = fsmod.inode2path(self.rclicked_inode).parent

        startname = "New Folder"

        #make sure it's unique
        parent_ls = parent.ls(conv=str.lower)
        suffix = 0
        while startname.lower() in parent_ls:
            suffix+=1
            startname = "New Folder %d" % suffix

        new_name = QInputDialog.getText(self, "New Folder",
                                        "Create new folder in:\n{}".format(parent), text=startname)[0]

        if new_name:
            fsmod.create_new_dir(parent, new_name)


        # new_index = fsmod.create_new_dir(parent, new_name)

        #  immediately open the name-editor for the new directory
        # self.mod_structure_view.edit(new_index)


    def custom_context_menu(self, position):
        clicked_index = self.mod_structure_view.indexAt(position)

        topidx = self.fsroot # current root node

        if clicked_index.isValid():
            self.rclicked_inode = clicked_index.internalId()
        else:
            self.rclicked_inode = topidx.internalId()


        user_set_root, clicked_isdir, non_root = (topidx.isValid(),
                                    self.modfsmodel._isdir(self.rclicked_inode),
                                    clicked_index.isValid()
                                    )


        # adjust visible options #
        # ---------------------- #

        # show unset option if user has set custom root
        self.action_unset_top_level_directory.setVisible(user_set_root)

        # show set option if user clicked on directory (that is not the root)
        self.action_set_as_top_level_directory.setVisible(clicked_isdir and non_root)

        # show rename/delete options if user clicked on anything but root
        self.action_rename.setVisible(non_root)
        self.action_delete.setVisible(non_root)

        # always show create-dir option.
        # self.action_create_directory

        self.rclickmenu.exec_(self.mod_structure_view.mapToGlobal(position))

    def check_top_level(self):
        isvalid = self.modfsmodel.validate_mod_structure(self.fsroot)

        # print(isvalid)

    def delete_file(self):

        # so, in what myriad ways might this fail?
        self.modfsmodel.delete(self.rclicked_inode)

    def undo(self):
        # self.modfsmodel.undo()
        self.undostack.undo()
    def redo(self):
        # self.modfsmodel.redo()
        self.undostack.redo()



    #
    # def on_tree_change(self):
    #     self.valid_structure = self.analyze_tree()
    #     # ss=""
    #
    #     if self.valid_structure:
    #         ss = "QLabel {color: green} "
    #         self.description.setText(_description)
    #     else:
    #         ss = "QLabel {color: tomato} "
    #         self.description.setText(_bad_package_desc)
    #     self.setStyleSheet(ss)
    #
    # def analyze_tree(self):
    #     _tree = self.mod_structure_view
    #
    #     for i in range(_tree.topLevelItemCount()):
    #         tlitem = _tree.topLevelItem(i) # type: QTreeWidgetItem
    #         text = tlitem.text(0).lower()
    #         if text in TopLevelDirs_Bain or splitext(text)[
    #             -1].lstrip('.') in TopLevelSuffixes:
    #             return True
    #
    #     return False


    # def done(self, result):
    #     if result!=QDialog.Rejected:
    #         # todo: make sure the final selection of data to install is made available once the dialog closes, as well as the total number of files that need installing so that a progress dialog may be shown.
    #         self.num_to_copy = self.mod_data.count()
    #
    #     super().done(result)
