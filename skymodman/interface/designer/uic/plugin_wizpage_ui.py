# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'skymodman/interface/designer/ui/plugin_wizpage.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_WizardPage(object):
    def setupUi(self, WizardPage):
        WizardPage.setObjectName("WizardPage")
        WizardPage.resize(632, 459)
        self.gridLayout = QtWidgets.QGridLayout(WizardPage)
        self.gridLayout.setObjectName("gridLayout")
        self.splitter = QtWidgets.QSplitter(WizardPage)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.splitter.sizePolicy().hasHeightForWidth())
        self.splitter.setSizePolicy(sizePolicy)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setObjectName("splitter")
        self.plugin_list = QtWidgets.QListWidget(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.plugin_list.sizePolicy().hasHeightForWidth())
        self.plugin_list.setSizePolicy(sizePolicy)
        self.plugin_list.setMinimumSize(QtCore.QSize(200, 0))
        self.plugin_list.setMouseTracking(True)
        self.plugin_list.setWordWrap(True)
        self.plugin_list.setObjectName("plugin_list")
        item = QtWidgets.QListWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled)
        item.setCheckState(QtCore.Qt.Unchecked)
        self.plugin_list.addItem(item)
        item = QtWidgets.QListWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled)
        item.setCheckState(QtCore.Qt.Unchecked)
        self.plugin_list.addItem(item)
        self.plugin_view = QtWidgets.QGroupBox(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.plugin_view.sizePolicy().hasHeightForWidth())
        self.plugin_view.setSizePolicy(sizePolicy)
        self.plugin_view.setObjectName("plugin_view")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.plugin_view)
        self.verticalLayout.setObjectName("verticalLayout")
        self.splitter_2 = QtWidgets.QSplitter(self.plugin_view)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.splitter_2.sizePolicy().hasHeightForWidth())
        self.splitter_2.setSizePolicy(sizePolicy)
        self.splitter_2.setOrientation(QtCore.Qt.Vertical)
        self.splitter_2.setChildrenCollapsible(False)
        self.splitter_2.setObjectName("splitter_2")
        self.plugin_description_view = QtWidgets.QTextBrowser(self.splitter_2)
        self.plugin_description_view.setMinimumSize(QtCore.QSize(0, 200))
        self.plugin_description_view.setObjectName("plugin_description_view")
        self.label = ScaledLabel(self.splitter_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setMinimumSize(QtCore.QSize(10, 10))
        self.label.setText("")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.splitter_2)
        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)

        self.retranslateUi(WizardPage)
        QtCore.QMetaObject.connectSlotsByName(WizardPage)

    def retranslateUi(self, WizardPage):
        _translate = QtCore.QCoreApplication.translate
        WizardPage.setWindowTitle(_translate("WizardPage", "WizardPage"))
        __sortingEnabled = self.plugin_list.isSortingEnabled()
        self.plugin_list.setSortingEnabled(False)
        item = self.plugin_list.item(0)
        item.setText(_translate("WizardPage", "Select One Plugin Test"))
        item = self.plugin_list.item(1)
        item.setText(_translate("WizardPage", "ITemtest2"))
        self.plugin_list.setSortingEnabled(__sortingEnabled)
        self.plugin_view.setTitle(_translate("WizardPage", "Description"))
        self.plugin_description_view.setPlaceholderText(_translate("WizardPage", "Testing Testing We\'ll put some stuff here it\'ll be great you just know it haha."))

from skymodman.interface.widgets.fomod_installer_wizard import ScaledLabel
