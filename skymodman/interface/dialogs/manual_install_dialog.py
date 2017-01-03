from PyQt5 import QtWidgets
from PyQt5.QtCore import QModelIndex#, Qt, pyqtSlot
from PyQt5.QtGui import QKeySequence, QPalette
from PyQt5.QtWidgets import QDialog, QMenu, QInputDialog

from skymodman.interface.designer.uic.archive_structure_ui import Ui_mod_structure_dialog
from skymodman.interface.widgets.overlay_layout import Overlay, OverlayCenter
from skymodman.interface.models.archivefs_treemodel import ModArchiveTreeModel
from skymodman.log import withlogger
from skymodman.utils import icons

_description = "Arrange the directory structure of the archive shown" \
               " to the right into the proper structure for" \
               " installation, then click \"OK\" to install the mod."

_bad_package_desc = "This mod does not appear to have been packaged" \
                    " correctly. Please rearrange the directory" \
                    " structure to the right to place the game data" \
                    " on the top level of the mod, then click \"OK\"" \
                    " to continue."

_tree_tooltip = """Drag files and folders to rearrange.
Uncheck items to exclude them from installation.
Right click to set top-level directory or create a new folder."""


# noinspection PyUnusedLocal
@withlogger
class ManualInstallDialog(QDialog, Ui_mod_structure_dialog):

    def __init__(self, mod_fs, *args, **kwargs):
        """

        :param skymodman.utils.archivefs.ArchiveFS mod_fs: An
            instance of an ArchiveFS pseudo-filesystem.

        :param args: passed to base class constructors
        :param kwargs: passed to base class constructors
        :return:
        """
        super().__init__(*args, **kwargs)
        self.LOGGER << "init manual install dlg"

        self.setupUi(self)

        # self.resize(1200, self.height())

        self.structure = mod_fs
        self.num_to_copy = 0

        # create undo framework
        (self.undostack
         , self.action_undo
         , self.action_redo
         # , self.undoview
         ) = self.__setup_undo()

        # Create button overlay
        # self.main_overlay, self.tree_overlay, self.button_overlay = self.__setup_overlay()
        self.main_overlay = self.__setup_overlay()

        # initialize tree model from structure, give undostack ref
        self.modfsmodel = ModArchiveTreeModel(self)

        self.mod_structure_view.setModel(self.modfsmodel)
        self.mod_structure_view.customContextMenuRequested.connect(
            self.custom_context_menu)

        # set default for active_view
        self._active_view = self.mod_structure_view

        # self.mod_structure_column_view.setModel(self.modfsmodel)
        # self.mod_structure_column_view.owner = self
        # self.mod_structure_column_view.setResizeGripsVisible(False)

        # create custom context menu
        self.rclickmenu = self.__setup_context_menu()
        self.rclicked_inode = None

        ## connect actions
        self.__setup_actions()

        ## connect some more signals
        # noinspection PyUnresolvedReferences
        self.modfsmodel.rowsMoved.connect(self.check_top_level)
        # noinspection PyUnresolvedReferences
        self.modfsmodel.rowsInserted.connect(self.check_top_level)
        self.modfsmodel.folder_structure_changed.connect(self.check_top_level)


        self.mod_structure_view.setToolTip(_tree_tooltip)
        # self.mod_structure_column_view.setToolTip(_tree_tooltip)

        ## Hide the Trash folder
        self.mod_structure_view.setRowHidden(
            self.modfsmodel.row4path(self.modfsmodel.trash),
            self.mod_structure_view.rootIndex(), # should still be "/" at this point
            True)


        self._icon_ok = icons.get("status-ok")
        self._icon_notok = icons.get("status-bad")

        self.check_top_level()

        # self.mod_structure_column_view.setSelectionModel(self.mod_structure_view.selectionModel())

        # show colview by default while we're testing it
        # self.btn_colview.click()

    def __setup_undo(self):
        undostack = QtWidgets.QUndoStack()

        undoaction = undostack.createUndoAction(self, "Undo")
        undoaction.pyqtConfigure(shortcut=QKeySequence.Undo,
                                 icon=icons.get(
                                     "undo", scale_factor=0.85,
                                     offset=(0, 0.1)),
                                 # icon=QIcon.fromTheme("edit-undo"),
                                 # triggered=self.undo
                                 )

        redoaction = undostack.createRedoAction(self, "Redo")
        redoaction.pyqtConfigure(shortcut=QKeySequence.Redo,
                                 icon=icons.get(
                                     "redo", scale_factor=0.85,
                                     offset=(0, 0.1)),
                                 # icon=QIcon.fromTheme("edit-redo"),
                                 # triggered=self.redo
                                 )

        # undoview = QtWidgets.QUndoView(undostack)
        # undoview.show()
        # undoview.setAttribute(Qt.WA_QuitOnClose, False)

        return undostack, undoaction, redoaction #, None# undoview

    def __setup_overlay(self):
        tree_overlay = Overlay()
        tree_overlay.addWidget(self.view_switcher)

        ## set up stylesheet for buttons ##
        pal = QPalette()

        # get main text and highlight colors from palette
        txtcol = pal.color(QPalette.WindowText)
        txtcol.setAlphaF(0.5)

        # normal border is main text color @ 50% opacity
        border_color = f"rgba{str(txtcol.getRgb())}"
        # hovered border is palette highlight color
        # hover_border_color = "rgba{}".format(str(hlcol.getRgb()))

        # hovered btn-bg is highlight color @ 30% opacity
        hlcol = pal.color(QPalette.Highlight)
        hlcol.setAlphaF(0.3)
        hover_bg = f"rgba{str(hlcol.getRgb())}"

        btn_stylesheet = f"""QGroupBox {{
                                background: transparent;
                                padding: 6px;
                           }}
                           QToolButton {{
                               background: transparent;
                               border: 1px solid {border_color};
                               border-radius: 2px;
                           }}
                           QToolButton:checked {{
                                background: palette(midlight);
                            }}
                           QToolButton:hover {{
                               background: {hover_bg};
                               border: 1px solid palette(highlight);
                           }}
                           """

        ## create overlay for undo/redo buttons ##
        undo_overlay = Overlay("top", "right", btn_stylesheet)

        undo_overlay.addWidget(self.undo_btngroup)

        self.btn_undo.setDefaultAction(self.action_undo)
        self.btn_redo.setDefaultAction(self.action_redo)

        ## View switching buttons ##
        # chview_btngroup = QtWidgets.QButtonGroup(self.view_switcher)
        self.change_view_btngroup.setVisible(False)

        # chview_btngroup.addButton(self.btn_treeview)
        # chview_btngroup.setId(self.btn_treeview, 0)
        #
        # chview_btngroup.addButton(self.btn_colview)
        # chview_btngroup.setId(self.btn_colview, 1)

        # self.btn_treeview.setIcon(icons.get("view-tree"))
        # self.btn_colview.setIcon(icons.get("view-column"))

        # chview_btngroup.buttonClicked[int].connect(self.change_view)

        # and the overlay
        # chview_overlay = Overlay("bottom", "right", btn_stylesheet)
        # chview_overlay.addWidget(self.change_view_btngroup)

        ## create and populate main overlay ##
        main_overlay = OverlayCenter(self.fsview)
        main_overlay.addLayout(tree_overlay)
        main_overlay.addLayout(undo_overlay)
        # main_overlay.addLayout(chview_overlay)

        return main_overlay#, tree_overlay#, btn_overlay

    def __setup_context_menu(self):
        # here's the custom menu (actions will be made in/visible as required)
        rclickmenu = QMenu(self.mod_structure_view)

        rclickmenu.addActions(
            [self.action_unset_toplevel,
             self.action_set_toplevel,
             self.action_rename,
             self.action_delete,
             self.action_create_directory])

        return rclickmenu

    def __setup_actions(self):
        self.action_set_toplevel.triggered.connect(
            self.set_toplevel)
        self.action_unset_toplevel.triggered.connect(
            self.unset_toplevel)
        self.action_rename.triggered.connect(self.rename)
        self.action_create_directory.triggered.connect(self.create_dir)
        self.action_delete.triggered.connect(self.delete_file)


    def get_rclickmenu(self, for_view):
        # here's the custom menu (actions will be made in/visible
        # as required)
        rclickmenu = QMenu(for_view)

        rclickmenu.addActions(
            [self.action_unset_toplevel,
             self.action_set_toplevel,
             self.action_rename,
             self.action_delete,
             self.action_create_directory])

        return rclickmenu

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
        # self.mod_structure_column_view.setRootIndex(index)
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
        """
        self.LOGGER << "unset_toplevel()"
        self.fsroot = QModelIndex()


    def rename(self, *args):
        # self.LOGGER << "rename()"
        self.mod_structure_view.edit(
            self.modfsmodel.index4inode(self.rclicked_inode))

    def create_dir(self, *args):
        """
        Create a new directory as a sibling (if the clicked item was a
        file) or child (if it was a folder) of the target of the last
         context-menu event, and open its name-editor.
        :param args:
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

        # noinspection PyArgumentList,PyTypeChecker
        new_name = QInputDialog.getText(self, "New Folder",
                                        f"Create new folder in:\n{parent}",
                                        text=startname)[0]

        if new_name:
            fsmod.create_new_dir(parent, new_name)

    def show_context_menu(self, view, index, global_pos):
        topidx = self.fsroot # current root node

        if index.isValid():
            self.rclicked_inode = index.internalId()
        else:
            self.rclicked_inode = topidx.internalId()

        user_set_root, clicked_isdir, non_root = (topidx.isValid(),
                                                  self.modfsmodel._isdir(
                                                      self.rclicked_inode),
                                                  index.isValid()
                                                  )

        # adjust visible options #
        # ---------------------- #

        # show unset option if user has set custom root
        self.action_unset_toplevel.setVisible(user_set_root)

        # show set option if user clicked on directory (that is not the root)
        self.action_set_toplevel.setVisible(clicked_isdir and non_root)

        # show rename/delete options if user clicked on anything but root
        self.action_rename.setVisible(non_root)
        self.action_delete.setVisible(non_root)

        # always show create-dir option.
        # self.action_create_directory
        self.get_rclickmenu(view).exec_(global_pos)

    def custom_context_menu(self, position):
        clicked_index = self.mod_structure_view.indexAt(position)

        topidx = self.fsroot # current root node
        non_root = clicked_index.isValid()

        if non_root:
            self.rclicked_inode = clicked_index.internalId()
        else:
            self.rclicked_inode = topidx.internalId()

        user_set_root = topidx.isValid()
        clicked_isdir = self.modfsmodel._isdir(self.rclicked_inode)

        # user_set_root, clicked_isdir, non_root = (topidx.isValid(),
        #                             self.modfsmodel._isdir(self.rclicked_inode),
        #                             clicked_index.isValid()
        #                             )

        # adjust visible options #
        # ---------------------- #

        # show unset option if user has set custom root
        self.action_unset_toplevel.setVisible(user_set_root)

        # show set option if user clicked on directory (that is not the root)
        self.action_set_toplevel.setVisible(clicked_isdir and non_root)

        # show rename/delete options if user clicked on anything but root
        self.action_rename.setVisible(non_root)
        self.action_delete.setVisible(non_root)

        # always show create-dir option.
        # self.action_create_directory

        self.rclickmenu.exec_(self.mod_structure_view.mapToGlobal(position))

    # def check_top_level(self, parent=None, first=-1, last=-1,
    # dest=None, dest_row=-1):
    def check_top_level(self, *args):

        isvalid = self.modfsmodel.validate_mod_structure(self.fsroot)
        if isvalid:
            self.lbl_structure_icon.setPixmap(self._icon_ok.pixmap(22, 22))
        else:
            self.lbl_structure_icon.setPixmap(
                self._icon_notok.pixmap(22, 22))

        # print(isvalid)

    def delete_file(self):
        # so, in what myriad ways might this fail?
        self.modfsmodel.delete(self.rclicked_inode)

    # def undo(self):
    #     self.undostack.undo()
    # def redo(self):
    #     self.undostack.redo()

    # @pyqtSlot(int)
    # def change_view(self, widget_index):
    #     self.view_switcher.setCurrentIndex(widget_index)
    #     self._active_view = (self.mod_structure_view,
    #                          self.mod_structure_column_view
    # )[widget_index]

    def is_expanded(self, index):
        return self._active_view.isExpanded(index)

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


