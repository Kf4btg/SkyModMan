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
        FileExistsDialog.resize(551, 200)
        self.gridLayout = QtWidgets.QGridLayout(FileExistsDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setContentsMargins(-1, -1, -1, 10)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.name_edit = QtWidgets.QLineEdit(FileExistsDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.name_edit.sizePolicy().hasHeightForWidth())
        self.name_edit.setSizePolicy(sizePolicy)
        self.name_edit.setObjectName("name_edit")
        self.gridLayout_2.addWidget(self.name_edit, 0, 1, 1, 1)
        self.btn_new_name = QtWidgets.QPushButton(FileExistsDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_new_name.sizePolicy().hasHeightForWidth())
        self.btn_new_name.setSizePolicy(sizePolicy)
        self.btn_new_name.setMinimumSize(QtCore.QSize(120, 0))
        self.btn_new_name.setMaximumSize(QtCore.QSize(150, 16777215))
        self.btn_new_name.setObjectName("btn_new_name")
        self.gridLayout_2.addWidget(self.btn_new_name, 0, 2, 1, 1)
        self.lbl_status = QtWidgets.QLabel(FileExistsDialog)
        self.lbl_status.setObjectName("lbl_status")
        self.gridLayout_2.addWidget(self.lbl_status, 1, 1, 1, 2)
        self.gridLayout.addLayout(self.gridLayout_2, 2, 0, 1, 5)
        self.btnbox = QtWidgets.QDialogButtonBox(FileExistsDialog)
        self.btnbox.setOrientation(QtCore.Qt.Horizontal)
        self.btnbox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.btnbox.setObjectName("btnbox")
        self.gridLayout.addWidget(self.btnbox, 4, 4, 1, 1)
        self.btn_overwrite = QtWidgets.QPushButton(FileExistsDialog)
        self.btn_overwrite.setAutoDefault(False)
        self.btn_overwrite.setObjectName("btn_overwrite")
        self.gridLayout.addWidget(self.btn_overwrite, 4, 1, 1, 1)
        self.label = QtWidgets.QLabel(FileExistsDialog)
        self.label.setStyleSheet("QLabel {padding: 0 10px 0px 0px; }")
        self.label.setAlignment(QtCore.Qt.AlignBottom|QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft)
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 5)
        self.btn_merge = QtWidgets.QPushButton(FileExistsDialog)
        self.btn_merge.setAutoDefault(False)
        self.btn_merge.setObjectName("btn_merge")
        self.gridLayout.addWidget(self.btn_merge, 4, 0, 1, 1)
        self.btn_skip = QtWidgets.QPushButton(FileExistsDialog)
        self.btn_skip.setObjectName("btn_skip")
        self.gridLayout.addWidget(self.btn_skip, 4, 2, 1, 1)
        self.cbox_sticky = QtWidgets.QCheckBox(FileExistsDialog)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.cbox_sticky.setFont(font)
        self.cbox_sticky.setObjectName("cbox_sticky")
        self.gridLayout.addWidget(self.cbox_sticky, 4, 3, 1, 1)

        self.retranslateUi(FileExistsDialog)
        self.btnbox.accepted.connect(FileExistsDialog.accept)
        self.btnbox.rejected.connect(FileExistsDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(FileExistsDialog)

    def retranslateUi(self, FileExistsDialog):
        _translate = QtCore.QCoreApplication.translate
        FileExistsDialog.setWindowTitle(_translate("FileExistsDialog", "Dialog"))
        self.btn_new_name.setText(_translate("FileExistsDialog", "Suggest New Name"))
        self.btn_overwrite.setText(_translate("FileExistsDialog", "Overwrite"))
        self.label.setText(_translate("FileExistsDialog", "This operation would overwrite \'{path}\' with itself. How would you like to continue?"))
        self.btn_merge.setText(_translate("FileExistsDialog", "Merge"))
        self.btn_skip.setText(_translate("FileExistsDialog", "Skip"))
        self.cbox_sticky.setText(_translate("FileExistsDialog", "Apply to all    "))

