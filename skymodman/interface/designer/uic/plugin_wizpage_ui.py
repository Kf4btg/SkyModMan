# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'skymodman/interface/designer/ui/plugin_wizpage.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_InstallStepPage(object):
    def setupUi(self, InstallStepPage):
        InstallStepPage.setObjectName("InstallStepPage")
        InstallStepPage.resize(632, 459)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(InstallStepPage.sizePolicy().hasHeightForWidth())
        InstallStepPage.setSizePolicy(sizePolicy)
        self.gridLayout = QtWidgets.QGridLayout(InstallStepPage)
        self.gridLayout.setObjectName("gridLayout")
        self.v_splitter = QtWidgets.QSplitter(InstallStepPage)
        self.v_splitter.setOrientation(QtCore.Qt.Horizontal)
        self.v_splitter.setChildrenCollapsible(False)
        self.v_splitter.setObjectName("v_splitter")
        self.plugin_list = QtWidgets.QTreeWidget(self.v_splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.plugin_list.sizePolicy().hasHeightForWidth())
        self.plugin_list.setSizePolicy(sizePolicy)
        self.plugin_list.setMinimumSize(QtCore.QSize(200, 0))
        self.plugin_list.setMouseTracking(True)
        self.plugin_list.setStyleSheet("QTreeWidget::item:has-children {\n"
"    color: rgb(85, 170, 255)\n"
"}\n"
"\n"
"QTreeWidget::branch {\n"
"    background: transparent\n"
"}\n"
"\n"
"QTreeWidget QLabel {\n"
"    padding: 2px;\n"
"    font-size:10pt;\n"
"}")
        self.plugin_list.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.plugin_list.setIndentation(10)
        self.plugin_list.setRootIsDecorated(False)
        self.plugin_list.setItemsExpandable(False)
        self.plugin_list.setAnimated(False)
        self.plugin_list.setWordWrap(True)
        self.plugin_list.setHeaderHidden(True)
        self.plugin_list.setExpandsOnDoubleClick(False)
        self.plugin_list.setObjectName("plugin_list")
        item_0 = QtWidgets.QTreeWidgetItem(self.plugin_list)
        item_1 = QtWidgets.QTreeWidgetItem(item_0)
        item_1.setCheckState(0, QtCore.Qt.Checked)
        item_1 = QtWidgets.QTreeWidgetItem(item_0)
        item_1.setCheckState(0, QtCore.Qt.Checked)
        self.plugin_view = QtWidgets.QGroupBox(self.v_splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.plugin_view.sizePolicy().hasHeightForWidth())
        self.plugin_view.setSizePolicy(sizePolicy)
        self.plugin_view.setObjectName("plugin_view")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.plugin_view)
        self.verticalLayout.setObjectName("verticalLayout")
        self.h_splitter = QtWidgets.QSplitter(self.plugin_view)
        self.h_splitter.setOrientation(QtCore.Qt.Vertical)
        self.h_splitter.setChildrenCollapsible(False)
        self.h_splitter.setObjectName("h_splitter")
        self.plugin_description_view = QtWidgets.QTextBrowser(self.h_splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.plugin_description_view.sizePolicy().hasHeightForWidth())
        self.plugin_description_view.setSizePolicy(sizePolicy)
        self.plugin_description_view.setMinimumSize(QtCore.QSize(0, 100))
        self.plugin_description_view.setObjectName("plugin_description_view")
        self.label = ScaledLabel(self.h_splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setMinimumSize(QtCore.QSize(10, 10))
        self.label.setText("")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.h_splitter)
        self.gridLayout.addWidget(self.v_splitter, 0, 0, 1, 1)

        self.retranslateUi(InstallStepPage)
        QtCore.QMetaObject.connectSlotsByName(InstallStepPage)

    def retranslateUi(self, InstallStepPage):
        _translate = QtCore.QCoreApplication.translate
        InstallStepPage.setWindowTitle(_translate("InstallStepPage", "WizardPage"))
        self.plugin_list.headerItem().setText(0, _translate("InstallStepPage", "1"))
        __sortingEnabled = self.plugin_list.isSortingEnabled()
        self.plugin_list.setSortingEnabled(False)
        self.plugin_list.topLevelItem(0).setText(0, _translate("InstallStepPage", "Group 1"))
        self.plugin_list.topLevelItem(0).child(0).setText(0, _translate("InstallStepPage", "Choice1"))
        self.plugin_list.topLevelItem(0).child(1).setText(0, _translate("InstallStepPage", "Choice2"))
        self.plugin_list.setSortingEnabled(__sortingEnabled)
        self.plugin_view.setTitle(_translate("InstallStepPage", "Description"))
        self.plugin_description_view.setPlaceholderText(_translate("InstallStepPage", "Testing Testing We\'ll put some stuff here it\'ll be great you just know it haha."))

from skymodman.interface.widgets.scaledlabel import ScaledLabel
