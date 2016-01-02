# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'qtinstaller.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 3, 0, 1, 1)
        self.next_button = QtWidgets.QPushButton(self.centralwidget)
        self.next_button.setLayoutDirection(QtCore.Qt.LeftToRight)
        icon = QtGui.QIcon.fromTheme("arrow-right")
        self.next_button.setIcon(icon)
        self.next_button.setAutoDefault(False)
        self.next_button.setDefault(True)
        self.next_button.setFlat(False)
        self.next_button.setObjectName("next_button")
        self.gridLayout.addWidget(self.next_button, 3, 2, 1, 1)
        self.quit_button = QtWidgets.QPushButton(self.centralwidget)
        self.quit_button.setLayoutDirection(QtCore.Qt.LeftToRight)
        icon = QtGui.QIcon.fromTheme("dialog-cancel")
        self.quit_button.setIcon(icon)
        self.quit_button.setAutoDefault(False)
        self.quit_button.setObjectName("quit_button")
        self.gridLayout.addWidget(self.quit_button, 3, 1, 1, 1)
        self.plugin_list = QtWidgets.QListWidget(self.centralwidget)
        self.plugin_list.setObjectName("plugin_list")
        self.gridLayout.addWidget(self.plugin_list, 0, 0, 1, 3)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 34))
        self.menubar.setObjectName("menubar")
        self.menu_File = QtWidgets.QMenu(self.menubar)
        self.menu_File.setObjectName("menu_File")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.toolBar = QtWidgets.QToolBar(MainWindow)
        self.toolBar.setObjectName("toolBar")
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        self.action_Install_Fomod = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("package-x-generic")
        self.action_Install_Fomod.setIcon(icon)
        self.action_Install_Fomod.setObjectName("action_Install_Fomod")
        self.action_Quit = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("application-exit")
        self.action_Quit.setIcon(icon)
        self.action_Quit.setObjectName("action_Quit")
        self.actionChoose_Mod_Folder = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("folder")
        self.actionChoose_Mod_Folder.setIcon(icon)
        self.actionChoose_Mod_Folder.setObjectName("actionChoose_Mod_Folder")
        self.menu_File.addAction(self.action_Install_Fomod)
        self.menu_File.addSeparator()
        self.menu_File.addAction(self.action_Quit)
        self.menubar.addAction(self.menu_File.menuAction())
        self.toolBar.addAction(self.actionChoose_Mod_Folder)
        self.toolBar.addAction(self.action_Install_Fomod)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.next_button.setText(_translate("MainWindow", "Next"))
        self.quit_button.setText(_translate("MainWindow", "Quit"))
        self.menu_File.setTitle(_translate("MainWindow", "&File"))
        self.toolBar.setWindowTitle(_translate("MainWindow", "toolBar"))
        self.action_Install_Fomod.setText(_translate("MainWindow", "&Install Fomod..."))
        self.action_Install_Fomod.setShortcut(_translate("MainWindow", "Ctrl+I"))
        self.action_Quit.setText(_translate("MainWindow", "&Quit"))
        self.action_Quit.setShortcut(_translate("MainWindow", "Ctrl+Q"))
        self.actionChoose_Mod_Folder.setText(_translate("MainWindow", "Choose Mod Folder"))
        self.actionChoose_Mod_Folder.setToolTip(_translate("MainWindow", "Choose Mod Folder"))

