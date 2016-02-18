# from os.path import splitext

# from PyQt5.QtCore import Qt
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

        :param structure_tree: An 'autovivifying dict'--aka a tree as per the implementation in utils.tree--that has been constructed so as to represent the directory structure within a mod archive. Each dict key (other than the root) will be the name of a directory, and files will be listed under the "_files" special key.
        :param bad_package: If the dialog is being launched from the automated installer due to problems detected with an archive's structure, this flag will be True, and a helpful message should be shown in place of the normal description.

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


        # self.mod_structure_view.tree_structure_changed.connect(self.on_tree_change)

        # have the tree widget create the visible tree from the
        # data-tree stored in self.structure; this will trigger
        # the validation check and update the UI accordingly
        # self.mod_structure_view.init_tree(self.structure)

        self.mod_structure_view.setToolTip(_tree_tooltip)


    def set_toplevel(self, *args):
        self.LOGGER << "set_toplevel()"

    def unset_toplevel(self, *args):
        self.LOGGER << "unset_toplevel()"

    def rename(self, *args):
        self.LOGGER << "rename()"

    def create_dir(self, *args):
        self.LOGGER << "create_dir()"

    def custom_context_menu(self, position):
        # menu = QMenu(self.mod_structure_view)
        # menu = self._getrclickmenu()

        fsmod = self.modfsmodel
        clicked_index = self.mod_structure_view.indexAt(position)
        self.rclicked_inode = clicked_index.internalId()

        user_root, isdir, isroot = (fsmod.has_modified_root,
                                    fsmod.index_is_dir(clicked_index),
                                    fsmod.index_is_root(clicked_index))


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


        # has_user_root, clicked_isdir, clicked_not_root = \
        #     self.modfsmodel.get_state_for_contextmenu(
        #     )

        # if has_user_root:
        #     menu.addAction(self.action_unset_top_level_directory)
        #
        # if clicked_not_root:
        #     if clicked_isdir:
        #         menu.addAction(self.action_set_as_top_level_directory)
        #     menu.addAction(self.action_rename)
        #
        # menu.addAction(self.action_create_directory)
        #
        # menu.exec_(self.mod_structure_view.mapToGlobal(position))



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
