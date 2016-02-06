# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'skymodman/interface/designer/ui/installation_wizpage.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_FinalPage(object):
    def setupUi(self, FinalPage):
        FinalPage.setObjectName("FinalPage")
        FinalPage.resize(600, 500)
        self.gridLayout = QtWidgets.QGridLayout(FinalPage)
        self.gridLayout.setObjectName("gridLayout")
        self._splitter = QtWidgets.QSplitter(FinalPage)
        self._splitter.setOrientation(QtCore.Qt.Vertical)
        self._splitter.setObjectName("_splitter")
        self.install_summary = QtWidgets.QTextBrowser(self._splitter)
        self.install_summary.setObjectName("install_summary")
        self.install_progress = QtWidgets.QProgressBar(self._splitter)
        self.install_progress.setProperty("value", 24)
        self.install_progress.setObjectName("install_progress")
        self.gridLayout.addWidget(self._splitter, 0, 0, 1, 1)

        self.retranslateUi(FinalPage)
        QtCore.QMetaObject.connectSlotsByName(FinalPage)

    def retranslateUi(self, FinalPage):
        _translate = QtCore.QCoreApplication.translate
        FinalPage.setWindowTitle(_translate("FinalPage", "WizardPage"))
        self.install_summary.setHtml(_translate("FinalPage", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Exo 2\'; font-size:12pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:\'monospace\';\">Installing the following files:</span></p>\n"
"<ul style=\"margin-top: 0px; margin-bottom: 0px; margin-left: 0px; margin-right: 0px; -qt-list-indent: 1;\"><li style=\" font-family:\'monospace\';\" style=\" margin-top:12px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Cool File 1</li>\n"
"<li style=\" font-family:\'monospace\';\" style=\" margin-top:0px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Cool file 2</li></ul></body></html>"))

