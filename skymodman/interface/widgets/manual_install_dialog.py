from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QTreeWidgetItem
from skymodman.interface.designer.uic.archive_structure_ui import Ui_mod_structure_dialog

_description = """Arrange the directory structure of the archive shown to the right into the proper structure for installation, then click "OK" to install the mod."""

_bad_package_desc = """This mod does not appear to have been packaged correctly. Please rearrange the directory structure to the right to place the game data on the top level of the mod, then click "OK" to continue."""




class ManualInstallDialog(QDialog, Ui_mod_structure_dialog):

    def __init__(self, structure_tree, bad_package = False, *args, **kwargs):
        """

        :param structure_tree: An 'autovivifying dict'--aka a tree as per the implementation in utils.tree--that has been constructed so as to represent the directory structure within a mod archive. Each dict key (other than the root) will be the name of a directory, and files will be listed under the "_files" special key.
        :param bad_package: If the dialog is being launched from the automated installer due to problems detected with an archive's structure, this flag will be True, and a helpful message should be shown in place of the normal description.

        :param args: passed to base class constructors
        :param kwargs: passed to base class constructors
        :return:
        """
        super().__init__(*args, **kwargs)

        self.setupUi(self)

        self.structure = structure_tree

        self.description.setText(_bad_package_desc
                                 if bad_package
                                 else _description)

        self.create_tree(self.structure, self.mod_structure_view.invisibleRootItem())

    def create_tree(self, dict_root, root_item):
        for k,v in dict_root.items():
            if k=="_files":
                for f in v:
                    i = QTreeWidgetItem(root_item)
                    i.setText(0,f)
                    i.setFlags(Qt.ItemIsEnabled |
                               Qt.ItemIsSelectable |
                               Qt.ItemIsDragEnabled |
                               Qt.ItemNeverHasChildren)
                    i.setIcon(0, QIcon.fromTheme("text-x-plain"))

            else:
                r=QTreeWidgetItem(root_item)
                r.setText(0,k)
                r.setFlags(Qt.ItemIsEnabled |
                           Qt.ItemIsSelectable |
                           Qt.ItemIsDragEnabled |
                           Qt.ItemIsDropEnabled)
                r.setIcon(0, QIcon.fromTheme("folder"))
                self.create_tree(v, r)

