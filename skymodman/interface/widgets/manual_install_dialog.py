# from os.path import splitext

# from PyQt5.QtCore import Qt
from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import QDialog, QMenu  #, QTreeWidgetItem

from skymodman.constants import TopLevelDirs_Bain, TopLevelSuffixes
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

        self.modfsmodel = ModArchiveTreeModel(mod_fs)

        self.mod_structure_view.setModel(self.modfsmodel)
        self.mod_structure_view.customContextMenuRequested.connect(
            self.custom_context_menu)

        # here's the custom menu (actions will be made in/visible as required)
        self.rclickmenu = QMenu(self.mod_structure_view)

        self.rclickmenu.addActions([self.action_unset_top_level_directory,
                         self.action_set_as_top_level_directory,
                         self.action_rename,
                         self.action_create_directory])

        self.rclicked_inode = None

        ## conect actions
        self.action_set_as_top_level_directory.triggered.connect(
            self.set_toplevel)
        self.action_unset_top_level_directory.triggered.connect(
            self.unset_toplevel)
        self.action_rename.triggered.connect(self.rename)
        self.action_create_directory.triggered.connect(self.create_dir)

        ## connect some more signals
        # self.modfsmodel.root_changed.connect(self.)

        # self.mod_structure_view.tree_structure_changed.connect(self.on_tree_change)

        # have the tree widget create the visible tree from the
        # data-tree stored in self.structure; this will trigger
        # the validation check and update the UI accordingly
        # self.mod_structure_view.init_tree(self.structure)

        self.mod_structure_view.setToolTip(_tree_tooltip)

    def top_index(self):
        return self.mod_structure_view.rootIndex()



    def set_toplevel(self, *args):
        self.LOGGER << "set_toplevel()"

        self.mod_structure_view.setRootIndex(self.modfsmodel.index4inode(self.rclicked_inode))

        # self.modfsmodel.change_root(self.rclicked_inode)


    def unset_toplevel(self, *args):
        self.LOGGER << "unset_toplevel()"

        self.mod_structure_view.setRootIndex(QModelIndex())


    def rename(self, *args):
        # self.LOGGER << "rename()"
        self.mod_structure_view.edit(
            self.modfsmodel.index4inode(self.rclicked_inode))

    def create_dir(self, *args):

        # fixme: for some reason, the item that gets the editor focus after the directory is created is not always the just-created directory...it also appears that the new folder is not always inserted at the correct sorted-insertion location--however, these two issues do not always overlap...because that would make sense, and we can't have that.

        # self.LOGGER << "create_dir()"
        fsmod = self.modfsmodel

        print(self.rclicked_inode)

        if fsmod._isdir(self.rclicked_inode):
            parent = fsmod.inode2path(self.rclicked_inode)
        else:
            parent = fsmod.inode2path(self.rclicked_inode).parent


        # new_folder = parent / "New Folder"
        new_name = "New Folder"

        suffix = 1
        while new_name in parent.listdir():
            new_name = "New Folder %d" % suffix
            suffix+=1

        new_index = fsmod.create_new_dir(parent, new_name)

        # and immediately open the name-editor for the new directory
        self.mod_structure_view.edit(new_index)


    def custom_context_menu(self, position):
        fsmod = self.modfsmodel
        clicked_index = self.mod_structure_view.indexAt(position)

        topidx = self.top_index()

        if clicked_index.isValid():
            self.rclicked_inode = clicked_index.internalId()
        else:
            self.rclicked_inode = topidx.internalId()


        user_root, isdir, isroot = (topidx.isValid(),
                                    fsmod.index_is_dir(clicked_index),
                                    clicked_index == topidx
                                    )


        # adjust visible options

        # show unset option if user has set custom root
        self.action_unset_top_level_directory.setVisible(user_root)

        # show set option if user clicked on directory (that is not the root)
        self.action_set_as_top_level_directory.setVisible(isdir and not isroot)

        # show rename option if user clicked on anything but root
        self.action_rename.setVisible(not isroot)

        # always show create-dir option.
        # self.action_create_directory

        self.rclickmenu.exec_(self.mod_structure_view.mapToGlobal(position))


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
