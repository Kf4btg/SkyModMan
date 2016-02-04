# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'skymodman/interface/designer/ui/fomod_installer.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Wizard(object):
    def setupUi(self, Wizard):
        Wizard.setObjectName("Wizard")
        Wizard.resize(600, 500)
        Wizard.setWizardStyle(QtWidgets.QWizard.ClassicStyle)
        Wizard.setOptions(QtWidgets.QWizard.NoBackButtonOnStartPage)
        self.page_start = QtWidgets.QWizardPage()
        self.page_start.setSubTitle("")
        self.page_start.setObjectName("page_start")
        Wizard.addPage(self.page_start)
        self.wizardPage2 = QtWidgets.QWizardPage()
        self.wizardPage2.setObjectName("wizardPage2")
        Wizard.addPage(self.wizardPage2)

        self.retranslateUi(Wizard)
        QtCore.QMetaObject.connectSlotsByName(Wizard)

    def retranslateUi(self, Wizard):
        _translate = QtCore.QCoreApplication.translate
        Wizard.setWindowTitle(_translate("Wizard", "Wizard"))
        self.page_start.setTitle(_translate("Wizard", "Mod Name"))
        self.wizardPage2.setTitle(_translate("Wizard", "Mod Name"))
        self.wizardPage2.setSubTitle(_translate("Wizard", "Step Name"))

