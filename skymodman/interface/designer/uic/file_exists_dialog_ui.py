# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'skymodman/interface/designer/ui/file_exists_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_FileExistsDialog(object):
    def setupUi(self, FileExistsDialog):
        FileExistsDialog.setObjectName("FileExistsDialog")
        FileExistsDialog.resize(450, 200)
        self.gridLayout = QtWidgets.QGridLayout(FileExistsDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.btnbox = QtWidgets.QDialogButtonBox(FileExistsDialog)
        self.btnbox.setOrientation(QtCore.Qt.Horizontal)
        self.btnbox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.btnbox.setObjectName("btnbox")
        self.gridLayout.addWidget(self.btnbox, 4, 2, 1, 1)
        self._nameeditlayout = QtWidgets.QHBoxLayout()
        self._nameeditlayout.setContentsMargins(-1, -1, -1, 24)
        self._nameeditlayout.setObjectName("_nameeditlayout")
        self.name_edit = QtWidgets.QLineEdit(FileExistsDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.name_edit.sizePolicy().hasHeightForWidth())
        self.name_edit.setSizePolicy(sizePolicy)
        self.name_edit.setObjectName("name_edit")
        self._nameeditlayout.addWidget(self.name_edit)
        self.btn_new_name = QtWidgets.QPushButton(FileExistsDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_new_name.sizePolicy().hasHeightForWidth())
        self.btn_new_name.setSizePolicy(sizePolicy)
        self.btn_new_name.setMinimumSize(QtCore.QSize(120, 0))
        self.btn_new_name.setMaximumSize(QtCore.QSize(150, 16777215))
        self.btn_new_name.setObjectName("btn_new_name")
        self._nameeditlayout.addWidget(self.btn_new_name)
        self.gridLayout.addLayout(self._nameeditlayout, 2, 0, 1, 3)
        self.label = QtWidgets.QLabel(FileExistsDialog)
        self.label.setStyleSheet("QLabel {padding: 0 10px 0px 0px; }")
        self.label.setAlignment(QtCore.Qt.AlignBottom|QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft)
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 3)
        self.btn_overwrite = QtWidgets.QPushButton(FileExistsDialog)
        self.btn_overwrite.setAutoDefault(False)
        self.btn_overwrite.setObjectName("btn_overwrite")
        self.gridLayout.addWidget(self.btn_overwrite, 4, 1, 1, 1)

        self.retranslateUi(FileExistsDialog)
        self.btnbox.accepted.connect(FileExistsDialog.accept)
        self.btnbox.rejected.connect(FileExistsDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(FileExistsDialog)

    def retranslateUi(self, FileExistsDialog):
        _translate = QtCore.QCoreApplication.translate
        FileExistsDialog.setWindowTitle(_translate("FileExistsDialog", "Dialog"))
        self.btn_new_name.setText(_translate("FileExistsDialog", "Suggest New Name"))
        self.label.setText(_translate("FileExistsDialog", "This operation would overwrite \'{path}\' with itself. How would you like to continue?"))
        self.btn_overwrite.setText(_translate("FileExistsDialog", "Overwrite"))

