# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'widgets/new_profile_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_NewProfileDialog(object):
    def setupUi(self, NewProfileDialog):
        NewProfileDialog.setObjectName("NewProfileDialog")
        NewProfileDialog.resize(400, 200)
        self.formLayout = QtWidgets.QFormLayout(NewProfileDialog)
        self.formLayout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setFormAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.formLayout.setContentsMargins(15, -1, 15, 0)
        self.formLayout.setVerticalSpacing(20)
        self.formLayout.setObjectName("formLayout")
        self.label = QtWidgets.QLabel(NewProfileDialog)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label)
        self.lineEdit = QtWidgets.QLineEdit(NewProfileDialog)
        self.lineEdit.setClearButtonEnabled(True)
        self.lineEdit.setObjectName("lineEdit")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.lineEdit)
        self.checkBox = QtWidgets.QCheckBox(NewProfileDialog)
        self.checkBox.setObjectName("checkBox")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.checkBox)
        self.comboBox = QtWidgets.QComboBox(NewProfileDialog)
        self.comboBox.setEnabled(False)
        self.comboBox.setObjectName("comboBox")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.comboBox)
        self.buttonBox = QtWidgets.QDialogButtonBox(NewProfileDialog)
        self.buttonBox.setEnabled(True)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.SpanningRole, self.buttonBox)
        self.label.setBuddy(self.lineEdit)

        self.retranslateUi(NewProfileDialog)
        self.buttonBox.accepted.connect(NewProfileDialog.accept)
        self.buttonBox.rejected.connect(NewProfileDialog.reject)
        self.checkBox.toggled['bool'].connect(self.comboBox.setEnabled)
        QtCore.QMetaObject.connectSlotsByName(NewProfileDialog)

    def retranslateUi(self, NewProfileDialog):
        _translate = QtCore.QCoreApplication.translate
        NewProfileDialog.setWindowTitle(_translate("NewProfileDialog", "Create New Profile"))
        self.label.setText(_translate("NewProfileDialog", "New Profi&le Name:"))
        self.checkBox.setToolTip(_translate("NewProfileDialog", "<html><head/><body><p>Check this box and choose an existing profile from the list on the right to duplicate the settings of that profile into your new profile.  The new profile will begin with default settings if this option is not chosen.</p></body></html>"))
        self.checkBox.setText(_translate("NewProfileDialog", "Copy Settings From:"))

