from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QAction, QMenu
from PyQt5.QtCore import pyqtSignal, pyqtProperty, Qt
from PyQt5.QtGui import QBrush

class MyTreeWidget(QTreeWidget):

    tree_structure_changed = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.action_set_toplevel = QAction("&set top level directory", self, triggered=self.mark_toplevel_dir)
        self.action_set_toplevel.setCheckable(True)
        # self.action_set_toplevel.triggered.connect(
        #     self.mark_toplevel_dir)

        self.user_toplevel_dir = None

        self.action_create_directory = QAction("&create directory", self)

    def mark_toplevel_dir(self):
        curr = self.currentItem()

        curr.isTopDir = not curr.isTopDir

        if curr.isTopDir:
            if self.user_toplevel_dir is not None:
                self.user_toplevel_dir.isTopDir = False
            self.user_toplevel_dir = curr
        else:
            # this means curr was already topdir
            self.user_toplevel_dir = None

        self.tree_structure_changed.emit()

    def dropEvent(self, event):
        super().dropEvent(event)

        self.tree_structure_changed.emit()

    def contextMenuEvent(self, event):
        menu=QMenu(self)

        curr = self.currentItem() # type: ArchiveItem

        # for directories:
        if not curr.flags() & Qt.ItemNeverHasChildren:
            menu.addAction(self.action_set_toplevel)
            self.action_set_toplevel.setChecked(curr.isTopDir)

        menu.addAction(self.action_create_directory)
        menu.exec_(event.globalPos())

class ArchiveItem(QTreeWidgetItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unchecked_brush = QBrush(Qt.gray)

    def data(self, col, role):
        if role == Qt.ForegroundRole and self.checkState(
            col) == Qt.Unchecked:
            return self.unchecked_brush

        return super().data(col, role)

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
            if role==Qt.BackgroundRole:
                return self.highlightBrush[1]
            if role == Qt.CheckStateRole:
                return Qt.Checked
            if role==Qt.ForegroundRole:
                return QTreeWidgetItem.data(self, col, role)
        return super().data(col, role)

    def setData(self, col, role, data):
        super().setData(col, role, data)

        if role==Qt.CheckStateRole and not self._istop:
            self._change_children_checkstate(data)

    def _change_children_checkstate(self, state):
        for i in range(self.childCount()):
            self.child(i).setCheckState(0, state)


