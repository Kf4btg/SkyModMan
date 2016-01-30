# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'skymodman/interface/widgets/archive_extract_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ArchiveUnpackerDialog(object):
    def setupUi(self, ArchiveUnpackerDialog):
        ArchiveUnpackerDialog.setObjectName("ArchiveUnpackerDialog")
        ArchiveUnpackerDialog.resize(400, 200)
        self.gridLayout = QtWidgets.QGridLayout(ArchiveUnpackerDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.frame = QtWidgets.QFrame(ArchiveUnpackerDialog)
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.frame)
        self.gridLayout_2.setObjectName("gridLayout_2")
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_2.addItem(spacerItem, 0, 0, 1, 1)
        self.label_label = QtWidgets.QLabel(self.frame)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_label.setFont(font)
        self.label_label.setObjectName("label_label")
        self.gridLayout_2.addWidget(self.label_label, 2, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_2.addItem(spacerItem1, 5, 0, 1, 1)
        self.progress_bar = QtWidgets.QProgressBar(self.frame)
        self.progress_bar.setProperty("value", 0)
        self.progress_bar.setObjectName("progress_bar")
        self.gridLayout_2.addWidget(self.progress_bar, 4, 0, 1, 1)
        self.current_activity_label = QtWidgets.QLabel(self.frame)
        self.current_activity_label.setObjectName("current_activity_label")
        self.gridLayout_2.addWidget(self.current_activity_label, 1, 0, 1, 1)
        self.gridLayout.addWidget(self.frame, 0, 0, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(ArchiveUnpackerDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 1, 0, 1, 1)

        self.retranslateUi(ArchiveUnpackerDialog)
        self.buttonBox.accepted.connect(ArchiveUnpackerDialog.accept)
        self.buttonBox.rejected.connect(ArchiveUnpackerDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(ArchiveUnpackerDialog)

    def retranslateUi(self, ArchiveUnpackerDialog):
        _translate = QtCore.QCoreApplication.translate
        ArchiveUnpackerDialog.setWindowTitle(_translate("ArchiveUnpackerDialog", "Extracting Archive"))
        self.label_label.setText(_translate("ArchiveUnpackerDialog", "TextLabel"))
        self.current_activity_label.setText(_translate("ArchiveUnpackerDialog", "Progress:"))

