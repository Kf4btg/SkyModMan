from os.path import splitext

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QTreeWidgetItem

from skymodman.constants import TopLevelDirs_Bain, TopLevelSuffixes
from skymodman.interface.widgets.mytreewidget import ArchiveItem, FolderItem
from skymodman.interface.designer.uic.archive_structure_ui import Ui_mod_structure_dialog
from skymodman.utils.tree import Tree

_description = """Arrange the directory structure of the archive shown to the right into the proper structure for installation, then click "OK" to install the mod."""

_bad_package_desc = """This mod does not appear to have been packaged correctly. Please rearrange the directory structure to the right to place the game data on the top level of the mod, then click "OK" to continue."""

_tree_tooltip = """Drag files and folders to rearrange.
Uncheck items to exclude them from installation.
Right click to set top-level directory or create a new folder."""




class ManualInstallDialog(QDialog, Ui_mod_structure_dialog):

    def __init__(self, structure_tree, *args, **kwargs):
        """

        :param structure_tree: An 'autovivifying dict'--aka a tree as per the implementation in utils.tree--that has been constructed so as to represent the directory structure within a mod archive. Each dict key (other than the root) will be the name of a directory, and files will be listed under the "_files" special key.
        :param bad_package: If the dialog is being launched from the automated installer due to problems detected with an archive's structure, this flag will be True, and a helpful message should be shown in place of the normal description.

        :param args: passed to base class constructors
        :param kwargs: passed to base class constructors
        :return:
        """
        super().__init__(*args, **kwargs)
        # from pprint import pprint
        # pprint(structure_tree)

        self.setupUi(self)

        self.structure = structure_tree
        self.mod_data = Tree()
        self.num_to_copy = 0

        self.create_tree(self.structure, self.mod_structure_view.invisibleRootItem())

        self.valid_structure = True
        self.data_root = self.structure
        # validate tree structure
        self.on_tree_change()

        self.mod_structure_view.tree_structure_changed.connect(self.on_tree_change)

        self.mod_structure_view.setToolTip(_tree_tooltip)


    def create_tree(self, dict_root, root_item):
        has_files = False
        # sort by name
        for k in sorted(list(dict_root.keys())):
            if k != "_files":
                r = FolderItem(root_item)
                r.setText(0, k)
                r.setFlags(Qt.ItemIsEnabled |
                           Qt.ItemIsSelectable |
                           Qt.ItemIsDragEnabled |
                           Qt.ItemIsDropEnabled |
                           Qt.ItemIsUserCheckable |
                           Qt.ItemIsTristate)
                r.setCheckState(0, Qt.Checked)
                r.setIcon(0, QIcon.fromTheme("folder"))

                # store the sub tree in this item's user-data
                r.setData(0, Qt.UserRole, dict_root[k])
                self.create_tree(dict_root[k], r)
            else:
                has_files=True
        # show files after dirs
        if has_files:
            for f in dict_root["_files"]:
                i = ArchiveItem(root_item)
                i.setText(0,f)
                i.setFlags(Qt.ItemIsEnabled |
                           Qt.ItemIsSelectable |
                           Qt.ItemIsDragEnabled |
                           Qt.ItemNeverHasChildren |
                           Qt.ItemIsUserCheckable)
                i.setCheckState(0,Qt.Checked)
                i.setIcon(0, QIcon.fromTheme("text-x-plain"))


    def on_tree_change(self):
        self.valid_structure = self.analyze_tree()
        ss=""

        if self.valid_structure:
            ss+="QLabel {color: green} "

            self.description.setText(_description)
        else:
            ss += "QLabel {color: tomato} "
            self.description.setText(_bad_package_desc)
        self.setStyleSheet(ss)


    def analyze_tree(self):
        _tree = self.mod_structure_view

        # if the user has not defined a new root
        if _tree.user_toplevel_dir is None:
            for i in range(_tree.topLevelItemCount()):
                tlitem = _tree.topLevelItem(i) # type: QTreeWidgetItem
                text = tlitem.text(0).lower()
                if text in TopLevelDirs_Bain or splitext(text)[-1].lstrip('.') in TopLevelSuffixes:
                    return True

        else: # user-defined root
            for i in range(_tree.user_toplevel_dir.childCount()):
                tlitem = _tree.user_toplevel_dir.child(i)
                text = tlitem.text(0).lower()
                if text in TopLevelDirs_Bain or splitext(text)[
                    -1].lstrip('.') in TopLevelSuffixes:
                    return True
        return False


    def done(self, result):
        if result!=QDialog.Rejected:
            self.num_to_copy = self.mod_data.count()

        super().done(result)

