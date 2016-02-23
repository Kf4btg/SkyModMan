# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'skymodman/interface/designer/ui/archive_structure.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_mod_structure_dialog(object):
    def setupUi(self, mod_structure_dialog):
        mod_structure_dialog.setObjectName("mod_structure_dialog")
        mod_structure_dialog.resize(600, 400)
        self.gridLayout = QtWidgets.QGridLayout(mod_structure_dialog)
        self.gridLayout.setObjectName("gridLayout")
        self._buttonbox = QtWidgets.QDialogButtonBox(mod_structure_dialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self._buttonbox.sizePolicy().hasHeightForWidth())
        self._buttonbox.setSizePolicy(sizePolicy)
        self._buttonbox.setLayoutDirection(QtCore.Qt.LeftToRight)
        self._buttonbox.setOrientation(QtCore.Qt.Vertical)
        self._buttonbox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self._buttonbox.setCenterButtons(True)
        self._buttonbox.setObjectName("_buttonbox")
        self.gridLayout.addWidget(self._buttonbox, 4, 0, 1, 1, QtCore.Qt.AlignHCenter)
        spacerItem = QtWidgets.QSpacerItem(20, 55, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        self.gridLayout.addItem(spacerItem, 3, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(20, 55, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        self.gridLayout.addItem(spacerItem1, 5, 0, 1, 1)
        self.undo_btngroup = QtWidgets.QGroupBox(mod_structure_dialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.undo_btngroup.sizePolicy().hasHeightForWidth())
        self.undo_btngroup.setSizePolicy(sizePolicy)
        self.undo_btngroup.setFlat(True)
        self.undo_btngroup.setObjectName("undo_btngroup")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.undo_btngroup)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.btn_undo = QtWidgets.QToolButton(self.undo_btngroup)
        icon = QtGui.QIcon.fromTheme("edit-undo")
        self.btn_undo.setIcon(icon)
        self.btn_undo.setObjectName("btn_undo")
        self.horizontalLayout.addWidget(self.btn_undo)
        self.btn_redo = QtWidgets.QToolButton(self.undo_btngroup)
        icon = QtGui.QIcon.fromTheme("edit-redo")
        self.btn_redo.setIcon(icon)
        self.btn_redo.setObjectName("btn_redo")
        self.horizontalLayout.addWidget(self.btn_redo)
        self.gridLayout.addWidget(self.undo_btngroup, 1, 0, 1, 1)
        self.description = QtWidgets.QLabel(mod_structure_dialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.description.sizePolicy().hasHeightForWidth())
        self.description.setSizePolicy(sizePolicy)
        self.description.setMinimumSize(QtCore.QSize(155, 0))
        self.description.setScaledContents(False)
        self.description.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.description.setWordWrap(True)
        self.description.setObjectName("description")
        self.gridLayout.addWidget(self.description, 0, 0, 1, 1)
        self.fsview = QtWidgets.QWidget(mod_structure_dialog)
        self.fsview.setObjectName("fsview")
        self.gridLayout.addWidget(self.fsview, 0, 1, 6, 3)
        self.view_switcher = QtWidgets.QStackedWidget(mod_structure_dialog)
        self.view_switcher.setObjectName("view_switcher")
        self.page_tree_view = QtWidgets.QWidget()
        self.page_tree_view.setObjectName("page_tree_view")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.page_tree_view)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.mod_structure_view = QtWidgets.QTreeView(self.page_tree_view)
        self.mod_structure_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.mod_structure_view.setEditTriggers(QtWidgets.QAbstractItemView.EditKeyPressed)
        self.mod_structure_view.setDragEnabled(True)
        self.mod_structure_view.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.mod_structure_view.setHeaderHidden(True)
        self.mod_structure_view.setObjectName("mod_structure_view")
        self.mod_structure_view.header().setDefaultSectionSize(0)
        self.gridLayout_2.addWidget(self.mod_structure_view, 0, 0, 1, 1)
        self.view_switcher.addWidget(self.page_tree_view)
        self.page_col_view = QtWidgets.QWidget()
        self.page_col_view.setObjectName("page_col_view")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.page_col_view)
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.mod_structure_column_view = ResizingColumnView(self.page_col_view)
        self.mod_structure_column_view.setEditTriggers(QtWidgets.QAbstractItemView.EditKeyPressed)
        self.mod_structure_column_view.setDragEnabled(True)
        self.mod_structure_column_view.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.mod_structure_column_view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.mod_structure_column_view.setResizeGripsVisible(False)
        self.mod_structure_column_view.setObjectName("mod_structure_column_view")
        self.gridLayout_3.addWidget(self.mod_structure_column_view, 0, 0, 1, 1)
        self.view_switcher.addWidget(self.page_col_view)
        self.gridLayout.addWidget(self.view_switcher, 0, 4, 6, 1)
        self.change_view_btngroup = QtWidgets.QGroupBox(mod_structure_dialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.change_view_btngroup.sizePolicy().hasHeightForWidth())
        self.change_view_btngroup.setSizePolicy(sizePolicy)
        self.change_view_btngroup.setFlat(True)
        self.change_view_btngroup.setObjectName("change_view_btngroup")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.change_view_btngroup)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.btn_treeview = QtWidgets.QToolButton(self.change_view_btngroup)
        icon = QtGui.QIcon.fromTheme("view-list-tree")
        self.btn_treeview.setIcon(icon)
        self.btn_treeview.setCheckable(True)
        self.btn_treeview.setChecked(True)
        self.btn_treeview.setObjectName("btn_treeview")
        self.horizontalLayout_2.addWidget(self.btn_treeview)
        self.btn_colview = QtWidgets.QToolButton(self.change_view_btngroup)
        icon = QtGui.QIcon.fromTheme("view-column")
        self.btn_colview.setIcon(icon)
        self.btn_colview.setCheckable(True)
        self.btn_colview.setObjectName("btn_colview")
        self.horizontalLayout_2.addWidget(self.btn_colview)
        self.gridLayout.addWidget(self.change_view_btngroup, 2, 0, 1, 1)
        self.action_set_toplevel = QtWidgets.QAction(mod_structure_dialog)
        self.action_set_toplevel.setObjectName("action_set_toplevel")
        self.action_unset_toplevel = QtWidgets.QAction(mod_structure_dialog)
        self.action_unset_toplevel.setObjectName("action_unset_toplevel")
        self.action_create_directory = QtWidgets.QAction(mod_structure_dialog)
        self.action_create_directory.setObjectName("action_create_directory")
        self.action_rename = QtWidgets.QAction(mod_structure_dialog)
        self.action_rename.setObjectName("action_rename")
        self.action_delete = QtWidgets.QAction(mod_structure_dialog)
        self.action_delete.setObjectName("action_delete")
        self.action_view_tree = QtWidgets.QAction(mod_structure_dialog)
        icon = QtGui.QIcon.fromTheme("view-list-tree")
        self.action_view_tree.setIcon(icon)
        self.action_view_tree.setObjectName("action_view_tree")
        self.action_view_columns = QtWidgets.QAction(mod_structure_dialog)
        icon = QtGui.QIcon.fromTheme("view-column")
        self.action_view_columns.setIcon(icon)
        self.action_view_columns.setObjectName("action_view_columns")

        self.retranslateUi(mod_structure_dialog)
        self._buttonbox.accepted.connect(mod_structure_dialog.accept)
        self._buttonbox.rejected.connect(mod_structure_dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(mod_structure_dialog)

    def retranslateUi(self, mod_structure_dialog):
        _translate = QtCore.QCoreApplication.translate
        mod_structure_dialog.setWindowTitle(_translate("mod_structure_dialog", "Dialog"))
        self.description.setText(_translate("mod_structure_dialog", "This mod does not have game data on the top level of its archive.  Please modify the directory structure on the right to reorganize the data appropriately."))
        self.action_set_toplevel.setText(_translate("mod_structure_dialog", "&Set as top level directory"))
        self.action_unset_toplevel.setText(_translate("mod_structure_dialog", "&Unset top level directory"))
        self.action_create_directory.setText(_translate("mod_structure_dialog", "&Create directory"))
        self.action_rename.setText(_translate("mod_structure_dialog", "&Rename"))
        self.action_delete.setText(_translate("mod_structure_dialog", "&Delete"))
        self.action_view_tree.setText(_translate("mod_structure_dialog", "Tree View"))
        self.action_view_columns.setText(_translate("mod_structure_dialog", "Column View"))

from skymodman.interface.widgets.archivefs_columnview import ResizingColumnView
