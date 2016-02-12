from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QAction, QMenu
from PyQt5.QtCore import pyqtSignal, pyqtProperty, Qt
from PyQt5.QtGui import QBrush, QIcon

from skymodman.utils import withlogger

@withlogger
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

        self.dragitem = None
        self.context_menu_item = None

    def startDrag(self, actions):
        # get item being moved (should only be 1)
        self.dragitem = self.selectedItems()[0]

        super().startDrag(actions)

    def dropEvent(self, event):
        super().dropEvent(event)

        target = self.itemAt(event.pos())
        if target is None or (target.isfile and target.parent() is None):
            self.invisibleRootItem().sortChildren(0, Qt.AscendingOrder)
        elif target.isdir:
            target.sortChildren(0, Qt.AscendingOrder)
        else:
            target.parent().sortChildren(0, Qt.AscendingOrder)

        self.tree_structure_changed.emit()

    def dragMoveEvent(self, event):
        """

        :param PyQt5.QtGui.QDragMoveEvent.QDragMoveEvent event:
        :return:
        """

        target = self.itemAt(event.pos())
        src = self.dragitem

        event.accept() # init flag to true

        try:
            if target.isfile:
                # target is a file, but is it a sibling?
                if target.parent() is src.parent():
                    event.ignore(self.visualItemRect(target))
            # also ignore drags to self, immediate parent
            elif target in [src, src.parent()]:
                event.ignore(self.visualItemRect(target))
        except AttributeError as e:
            # this means we're hovering over empty space (the root)
            # self.LOGGER << e
            if src.parent() is None:
                # ignore drags to root if src is already on the top level
                event.ignore(self.visualItemRect(target))

        # check whether we unset the accept flag;
        # if not, call the super()
        if event.isAccepted():
            super().dragMoveEvent(event)


    def contextMenuEvent(self, event):
        """

        :param PyQt5.QtGui.QContextMenuEvent.QContextMenuEvent event:
        :return:
        """
        menu=QMenu(self)
        # get item under cursor
        clikked = self.itemAt(event.pos())

        if not isinstance(clikked, ArchiveItem):
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
        if not curr:
            # if no selection, add as child of root
            parent = self.invisibleRootItem()
        else:
            # add newdir as child of current if current is directory;
            # otherwise add as sibling.
            parent = curr if curr.isdir else curr.parent()
            # expand to show new dir
            parent.setExpanded(True)

        newdir = FolderItem.create(parent,"")
        self.scrollToItem(newdir)

        self.editItem(newdir, 0)

    def rename_item(self):
        self.editItem(self.context_menu_item)
        self.tree_structure_changed.emit()



class ArchiveItem(QTreeWidgetItem):
    def __init__(self, *args, type=1002, **kwargs):
        # noinspection PyArgumentList
        super().__init__(*args, type=type, **kwargs)
        self.unchecked_brush = QBrush(Qt.gray)

    @property
    def isdir(self):
        return not self.flags() & Qt.ItemNeverHasChildren

    @property
    def isfile(self):
        return self.flags() & Qt.ItemNeverHasChildren

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

    def __lt__(self, other):
        if self.type() == other.type():
            return self.text(0) < other.text(0)

        return self.type() < other.type()


class FolderItem(ArchiveItem):

    highlightBrush = (QBrush(Qt.white), QBrush(Qt.darkCyan))

    def __init__(self, *args, type=1001, **kwargs):
        super().__init__(*args, type=type, **kwargs)
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