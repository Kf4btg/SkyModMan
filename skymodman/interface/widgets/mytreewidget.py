from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QAction, QMenu
from PyQt5.QtCore import pyqtSignal, pyqtProperty, Qt, QModelIndex
from PyQt5.QtGui import QBrush, QIcon, QResizeEvent, QPalette
from PyQt5 import QtGui


from skymodman.utils import withlogger
from copy import deepcopy


# @withlogger
from skymodman.utils.debug import printattrs




@withlogger
class MyTreeWidget(QTreeWidget):

    tree_structure_changed = pyqtSignal()

    # noinspection PyArgumentList
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.action_set_toplevel = QAction("&Set as top level directory", self, triggered=self.change_toplevel_dir)
        self.action_unset_toplevel = QAction("&Unset top level directory", self, triggered=self.unset_toplevel_dir)

        self.action_create_directory = QAction("&Create directory", self, triggered=self.create_directory)

        self.action_rename = QAction("&Rename", self, triggered=self.rename_item)

        self.orig_root = None
        self.modified_tree = None
        self.current_root = None

        self.user_toplevel_dir = False
        self.dragitem = None # type: ArchiveItem
        self.dragitem_parent = None
        self.context_menu_item = None # type: ArchiveItem

    def init_tree(self, root):
        if self.orig_root is None:
            self.orig_root = root
            self.modified_tree = deepcopy(root)
            self.current_root = self.modified_tree
            root = self.modified_tree

        self.clear()
        self.create_tree(root, self.invisibleRootItem())
        self.tree_structure_changed.emit()

    def create_tree(self, dict_root, root_item):
        has_files = False
        # sort by name
        for k in sorted(list(dict_root.keys())):
            if k != "_files":
                r = FolderItem.create(root_item, k)

                # save the subtree this key refers to in the widget's userdata
                r.setData(0, Qt.UserRole, dict_root[k])
                self.create_tree(dict_root[k], r)
            else:
                has_files = True
        # show files after dirs
        if has_files:
            for f in sorted(dict_root["_files"]):
                ArchiveItem.create(root_item, f)

    def startDrag(self, actions):
        # get item being moved (should only be 1)
        self.dragitem = self.selectedItems()[0]

        # print("ditem:", self.dragitem.text(0))

        # have to save this before the drop occurs
        self.dragitem_parent = self.dragitem.parent()
        #
        # if self.dragitem_parent is not None:
        #     print("ditem_par:", self.dragitem_parent.text(0))
        # else:
        #     print("ditem_par:", self.dragitem_parent)

        super().startDrag(actions)

    def dropEvent(self, event):
        # fixme: dragging items around doesn't currently change the tree-datastructures that are used to build the visual tree; thus, when a new root is set (and the tree is rebuilt), all changes made via drag-and-drop are lost.
        target = self.itemAt(event.pos())

        if target and target.isfile:
            target = target.parent() # always target a directory

        if target is self.dragitem or target is self.dragitem_parent:
            event.ignore()
        else:

            super().dropEvent(event)

            key = self.dragitem.text(0)
            # keep everything sorted by name, with directories first.

            # if target is not None:
            #     print("target:", target.text(0))
            # else:
            #     print("target:", target)

            if target is None: # targeting root of tree
                self.invisibleRootItem().sortChildren(0, Qt.AscendingOrder)

                old_parent = self.dragitem_parent.data(0, Qt.UserRole)
                new_parent = self.current_root

            else: # some other directory
                target.sortChildren(0, Qt.AscendingOrder)

                old_parent = (self.dragitem_parent.data(0, Qt.UserRole)
                              if self.dragitem_parent # if none, dragitem was a top-level item
                              else self.current_root)

                new_parent = target.data(0, Qt.UserRole)

            # update modified-tree
            self._restructure_tree(key,
                                   old_parent,
                                   new_parent,
                                   self.dragitem.isfile)

            print(self.modified_tree.to_string(indent=2))

            self.tree_structure_changed.emit()

    def _restructure_tree(self, key, old_parent_tree, new_parent_tree, is_file):
        # print("op:", old_parent_tree.keys(), old_parent_tree.leaves)
        # print("np:", new_parent_tree.keys(), new_parent_tree.leaves)

        if is_file:
            old_parent_tree.remove_leaf(key)
            new_parent_tree.add_leaf(key)
        else:
            new_parent_tree[key] = old_parent_tree[key]
            del old_parent_tree[key]


    def dragMoveEvent(self, event):
        """
        Reimplemented to ignore drags to self or immediate parent

        :param PyQt5.QtGui.QDragMoveEvent.QDragMoveEvent event:
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
        except AttributeError:
            # this means we're hovering over empty space (the root)
            if src.parent() is None:
                # ignore drags to root if src is already on the top level
                event.ignore(self.visualItemRect(target))

        # check whether we unset the accept flag;
        # if not, call the super()
        if event.isAccepted():
            super().dragMoveEvent(event)


    def contextMenuEvent(self, event):
        """
        Reimplemented to show various options depending on location of click.

        :param PyQt5.QtGui.QContextMenuEvent.QContextMenuEvent event:
        :return:
        """
        menu=QMenu(self)

        # if they've set a new root dir, show option to unset
        if self.user_toplevel_dir:
            menu.addAction(self.action_unset_toplevel)

        # get item under cursor
        clikked = self.itemAt(event.pos())

        if not isinstance(clikked, ArchiveItem):
            self.context_menu_item = None
        else:
            self.context_menu_item = clikked

            if clikked.isdir:
                self.context_menu_item = clikked
                menu.addAction(self.action_set_toplevel)

            menu.addAction(self.action_rename)

        menu.addAction(self.action_create_directory)

        menu.exec_(event.globalPos())

    def change_toplevel_dir(self):
        self.user_toplevel_dir = True
        self.current_root = self.context_menu_item.data(0, Qt.UserRole)

        self.init_tree(self.current_root)

    def unset_toplevel_dir(self):
        self.user_toplevel_dir = False
        self.current_root = self.modified_tree
        self.init_tree(self.modified_tree)

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
    # noinspection PyShadowingBuiltins
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
        # noinspection PyTypeChecker,PyArgumentList
        i.setIcon(0, QIcon.fromTheme("text-x-plain"))
        return i

    def __lt__(self, other):
        if self.type() == other.type():
            return self.text(0) < other.text(0)

        return self.type() < other.type()


class FolderItem(ArchiveItem):

    highlightBrush = (QBrush(Qt.white), QBrush(Qt.darkCyan))

    # noinspection PyShadowingBuiltins
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
        # noinspection PyTypeChecker,PyArgumentList
        r.setIcon(0, QIcon.fromTheme("folder"))
        return r