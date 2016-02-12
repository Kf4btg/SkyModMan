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
        spacerItem = QtWidgets.QSpacerItem(20, 55, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        self.gridLayout.addItem(spacerItem, 1, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(20, 55, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        self.gridLayout.addItem(spacerItem1, 3, 0, 1, 1)
        self.mod_structure_view = MyTreeWidget(mod_structure_dialog)
        self.mod_structure_view.setEditTriggers(QtWidgets.QAbstractItemView.EditKeyPressed)
        self.mod_structure_view.setDragEnabled(True)
        self.mod_structure_view.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.mod_structure_view.setObjectName("mod_structure_view")
        self.mod_structure_view.headerItem().setText(0, "1")
        self.mod_structure_view.header().setVisible(False)
        self.gridLayout.addWidget(self.mod_structure_view, 0, 2, 4, 1)
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
        self.gridLayout.addWidget(self._buttonbox, 2, 0, 1, 1, QtCore.Qt.AlignHCenter)
        self.action_set_data_directory = QtWidgets.QAction(mod_structure_dialog)
        self.action_set_data_directory.setCheckable(True)
        self.action_set_data_directory.setObjectName("action_set_data_directory")
        self.action_create_directory = QtWidgets.QAction(mod_structure_dialog)
        self.action_create_directory.setObjectName("action_create_directory")

        self.retranslateUi(mod_structure_dialog)
        self._buttonbox.accepted.connect(mod_structure_dialog.accept)
        self._buttonbox.rejected.connect(mod_structure_dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(mod_structure_dialog)

    def retranslateUi(self, mod_structure_dialog):
        _translate = QtCore.QCoreApplication.translate
        mod_structure_dialog.setWindowTitle(_translate("mod_structure_dialog", "Dialog"))
        self.description.setText(_translate("mod_structure_dialog", "This mod does not have game data on the top level of its archive.  Please modify the directory structure on the right to reorganize the data appropriately."))
        self.action_set_data_directory.setText(_translate("mod_structure_dialog", "Set Data Directory"))
        self.action_create_directory.setText(_translate("mod_structure_dialog", "Create Directory"))

from skymodman.interface.widgets.mytreewidget import MyTreeWidget
