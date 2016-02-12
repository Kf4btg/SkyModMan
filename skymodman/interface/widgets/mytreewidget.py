from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QAction, QMenu
from PyQt5.QtCore import pyqtSignal, pyqtProperty, Qt
from PyQt5.QtGui import QBrush, QIcon


class MyTreeWidget(QTreeWidget):

    tree_structure_changed = pyqtSignal()

    # noinspection PyArgumentList
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.action_set_toplevel = QAction("&set top level directory", self, triggered=self.mark_toplevel_dir)
        self.action_set_toplevel.setCheckable(True)

        self.user_toplevel_dir = None

        self.action_create_directory = QAction("&create directory", self, triggered=self.create_directory)

        self.action_rename = QAction("&rename", self, triggered=self.rename_item)

        self.context_menu_item = self.invisibleRootItem()



    def dropEvent(self, event):
        super().dropEvent(event)

        self.tree_structure_changed.emit()

    def contextMenuEvent(self, event):
        """

        :param PyQt5.QtGui.QContextMenuEvent.QContextMenuEvent event:
        :return:
        """
        menu=QMenu(self)
        # curr = self.currentItem() # type: ArchiveItem
        clikked = self.itemAt(event.pos())

        if not clikked or not isinstance(clikked, ArchiveItem):
            self.context_menu_item = None
        else:
            self.context_menu_item = clikked

            if clikked.isdir:
                self.context_menu_item = clikked
                menu.addAction(self.action_set_toplevel)
                # noinspection PyUnresolvedReferences
                self.action_set_toplevel.setChecked(clikked.isTopDir)

            menu.addAction(self.action_rename)

        menu.addAction(self.action_create_directory)

        menu.exec_(event.globalPos())

    def mark_toplevel_dir(self):
        # curr = self.currentItem()
        curr = self.context_menu_item

        curr.isTopDir = not curr.isTopDir

        if curr.isTopDir:
            if self.user_toplevel_dir is not None:
                self.user_toplevel_dir.isTopDir = False
            self.user_toplevel_dir = curr
        else:
            # this means curr was already topdir
            self.user_toplevel_dir = None

        self.tree_structure_changed.emit()

    def create_directory(self):
        curr = self.context_menu_item
        # selected = self.selectedItems()
        if not curr:
            # if no selection, add as child of root
            parent = self.invisibleRootItem()
        else:
            parent = curr if curr.isdir else curr.parent()
            # curr = self.currentItem()
            # if curr not in selected:
            #     curr = selected[0]

            # add newdir as child of current if current is directory;
            # otherwise add as sibling.

        newdir = FolderItem.create(parent,"")

        self.editItem(newdir, 0)

    def rename_item(self):
        # curr=self.currentItem() #type: # QTreeWidgetItem
        # self.editItem(self.currentItem())
        self.editItem(self.context_menu_item)
        # self.openPersistentEditor(self.currentItem(), 0)








class ArchiveItem(QTreeWidgetItem):
    def __init__(self, *args, **kwargs):
        # noinspection PyArgumentList
        super().__init__(*args, **kwargs)
        self.unchecked_brush = QBrush(Qt.gray)

    @property
    def isdir(self):
        return not self.flags() & Qt.ItemNeverHasChildren

    def data(self, col, role):
        if role == Qt.ForegroundRole and self.checkState(
            col) == Qt.Unchecked:
            return self.unchecked_brush

        return super().data(col, role)


    @classmethod
    def create(cls, parent, text):
        i = cls(parent)
        i.setText(0, text)
        i.setFlags(Qt.ItemIsEnabled
                   | Qt.ItemIsSelectable
                   | Qt.ItemIsEditable
                   | Qt.ItemIsDragEnabled
                   | Qt.ItemNeverHasChildren
                   | Qt.ItemIsUserCheckable)
        i.setCheckState(0, Qt.Checked)
        i.setIcon(0, QIcon.fromTheme("text-x-plain"))
        return i

class FolderItem(ArchiveItem):

    highlightBrush = (QBrush(Qt.white), QBrush(Qt.darkCyan))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._istop = False

    @pyqtProperty(bool)
    def isTopDir(self):
        return self._istop

    @isTopDir.setter
    def isTopDir(self, value):
        self._istop = value

    def data(self, col, role):

        if self._istop:
            if role == Qt.CheckStateRole:
                return Qt.Checked
            if role == Qt.BackgroundRole:
                return self.highlightBrush[1]
            if role == Qt.ForegroundRole:
                return QTreeWidgetItem.data(self, col, role)
        return super().data(col, role)

    def setData(self, col, role, data):
        super().setData(col, role, data)

        if role==Qt.CheckStateRole and not self._istop:
            self._change_children_checkstate(data)

    def _change_children_checkstate(self, state):
        for i in range(self.childCount()):
            self.child(i).setCheckState(0, state)


    @classmethod
    def create(cls, parent, text):
        r = cls(parent)
        r.setText(0, text)
        r.setFlags(Qt.ItemIsEnabled
                   | Qt.ItemIsEditable
                   | Qt.ItemIsSelectable
                   | Qt.ItemIsDragEnabled
                   | Qt.ItemIsDropEnabled
                   | Qt.ItemIsUserCheckable
                   | Qt.ItemIsTristate)
        r.setCheckState(0, Qt.Checked)
        r.setIcon(0, QIcon.fromTheme("folder"))
        return r