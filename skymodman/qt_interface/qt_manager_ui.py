# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'skymodman/qt_interface/qt_manager.ui'
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
        self.next_button.setEnabled(False)
        self.next_button.setLayoutDirection(QtCore.Qt.LeftToRight)
        icon = QtGui.QIcon.fromTheme("arrow-right")
        self.next_button.setIcon(icon)
        self.next_button.setAutoDefault(True)
        self.next_button.setObjectName("next_button")
        self.gridLayout.addWidget(self.next_button, 3, 2, 1, 1)
        self.save_cancel_btnbox = QtWidgets.QDialogButtonBox(self.centralwidget)
        self.save_cancel_btnbox.setEnabled(False)
        self.save_cancel_btnbox.setStandardButtons(QtWidgets.QDialogButtonBox.Apply|QtWidgets.QDialogButtonBox.Reset)
        self.save_cancel_btnbox.setObjectName("save_cancel_btnbox")
        self.gridLayout.addWidget(self.save_cancel_btnbox, 3, 1, 1, 1, QtCore.Qt.AlignRight)
        self.manager_tabs = QtWidgets.QTabWidget(self.centralwidget)
        self.manager_tabs.setObjectName("manager_tabs")
        self.installed_mods_tab = QtWidgets.QWidget()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.installed_mods_tab.sizePolicy().hasHeightForWidth())
        self.installed_mods_tab.setSizePolicy(sizePolicy)
        self.installed_mods_tab.setObjectName("installed_mods_tab")
        self.installed_mods_layout = QtWidgets.QGridLayout(self.installed_mods_tab)
        self.installed_mods_layout.setObjectName("installed_mods_layout")
        self.move_mod_box = QtWidgets.QGroupBox(self.installed_mods_tab)
        self.move_mod_box.setEnabled(False)
        self.move_mod_box.setTitle("")
        self.move_mod_box.setFlat(True)
        self.move_mod_box.setObjectName("move_mod_box")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.move_mod_box)
        self.gridLayout_2.setContentsMargins(-1, 0, -1, 0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.move_mod_label = QtWidgets.QLabel(self.move_mod_box)
        self.move_mod_label.setObjectName("move_mod_label")
        self.gridLayout_2.addWidget(self.move_mod_label, 0, 0, 1, 1)
        self.mod_up_button = QtWidgets.QToolButton(self.move_mod_box)
        icon = QtGui.QIcon.fromTheme("arrow-up")
        self.mod_up_button.setIcon(icon)
        self.mod_up_button.setObjectName("mod_up_button")
        self.gridLayout_2.addWidget(self.mod_up_button, 0, 1, 1, 1)
        self.mod_down_button = QtWidgets.QToolButton(self.move_mod_box)
        icon = QtGui.QIcon.fromTheme("arrow-down")
        self.mod_down_button.setIcon(icon)
        self.mod_down_button.setObjectName("mod_down_button")
        self.gridLayout_2.addWidget(self.mod_down_button, 0, 2, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem1, 0, 3, 1, 1)
        self.installed_mods_layout.addWidget(self.move_mod_box, 0, 3, 1, 1)
        self.line = QtWidgets.QFrame(self.installed_mods_tab)
        self.line.setFrameShape(QtWidgets.QFrame.VLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.installed_mods_layout.addWidget(self.line, 0, 2, 1, 1)
        self.profile_group = QtWidgets.QGroupBox(self.installed_mods_tab)
        self.profile_group.setFlat(True)
        self.profile_group.setObjectName("profile_group")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.profile_group)
        self.horizontalLayout_2.setContentsMargins(-1, 0, -1, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.profile_label = QtWidgets.QLabel(self.profile_group)
        self.profile_label.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.profile_label.setObjectName("profile_label")
        self.horizontalLayout_2.addWidget(self.profile_label)
        self.profile_selector = QtWidgets.QComboBox(self.profile_group)
        self.profile_selector.setObjectName("profile_selector")
        self.profile_selector.addItem("")
        self.profile_selector.addItem("")
        self.horizontalLayout_2.addWidget(self.profile_selector)
        self.new_profile_button = QtWidgets.QToolButton(self.profile_group)
        self.new_profile_button.setText("")
        icon = QtGui.QIcon.fromTheme("add")
        self.new_profile_button.setIcon(icon)
        self.new_profile_button.setObjectName("new_profile_button")
        self.horizontalLayout_2.addWidget(self.new_profile_button)
        self.remove_profile_button = QtWidgets.QToolButton(self.profile_group)
        self.remove_profile_button.setEnabled(False)
        icon = QtGui.QIcon.fromTheme("remove")
        self.remove_profile_button.setIcon(icon)
        self.remove_profile_button.setObjectName("remove_profile_button")
        self.horizontalLayout_2.addWidget(self.remove_profile_button)
        self.installed_mods_layout.addWidget(self.profile_group, 0, 0, 1, 2)
        self.manager_tabs.addTab(self.installed_mods_tab, "")
        self.filetree_tab = QtWidgets.QWidget()
        self.filetree_tab.setObjectName("filetree_tab")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.filetree_tab)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.splitter = QtWidgets.QSplitter(self.filetree_tab)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setObjectName("splitter")
        self.filetree_listbox = QtWidgets.QGroupBox(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.filetree_listbox.sizePolicy().hasHeightForWidth())
        self.filetree_listbox.setSizePolicy(sizePolicy)
        self.filetree_listbox.setMinimumSize(QtCore.QSize(250, 0))
        self.filetree_listbox.setObjectName("filetree_listbox")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.filetree_listbox)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.filetree_modlist = QtWidgets.QListView(self.filetree_listbox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.filetree_modlist.sizePolicy().hasHeightForWidth())
        self.filetree_modlist.setSizePolicy(sizePolicy)
        self.filetree_modlist.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.filetree_modlist.setObjectName("filetree_modlist")
        self.gridLayout_4.addWidget(self.filetree_modlist, 0, 0, 1, 1)
        self.filetree_fileviewer = QtWidgets.QTreeView(self.splitter)
        self.filetree_fileviewer.setObjectName("filetree_fileviewer")
        self.gridLayout_3.addWidget(self.splitter, 0, 0, 1, 1)
        self.manager_tabs.addTab(self.filetree_tab, "")
        self.fomod_tab = QtWidgets.QWidget()
        self.fomod_tab.setObjectName("fomod_tab")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.fomod_tab)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.installerpages = QtWidgets.QStackedWidget(self.fomod_tab)
        self.installerpages.setEnabled(True)
        self.installerpages.setObjectName("installerpages")
        self.plugin_page_1 = QtWidgets.QWidget()
        self.plugin_page_1.setObjectName("plugin_page_1")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.plugin_page_1)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.plugin_list = QtWidgets.QListWidget(self.plugin_page_1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.plugin_list.sizePolicy().hasHeightForWidth())
        self.plugin_list.setSizePolicy(sizePolicy)
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
        self.horizontalLayout.addWidget(self.plugin_list, 0, QtCore.Qt.AlignLeft)
        self.plugin_view = QtWidgets.QGroupBox(self.plugin_page_1)
        self.plugin_view.setObjectName("plugin_view")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.plugin_view)
        self.verticalLayout.setObjectName("verticalLayout")
        self.plugin_description_view = QtWidgets.QTextBrowser(self.plugin_view)
        self.plugin_description_view.setObjectName("plugin_description_view")
        self.verticalLayout.addWidget(self.plugin_description_view, 0, QtCore.Qt.AlignTop)
        self.label = QtWidgets.QLabel(self.plugin_view)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setText("")
        self.label.setPixmap(QtGui.QPixmap("res/STEP/STEP.png"))
        self.label.setScaledContents(True)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label, 0, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
        self.horizontalLayout.addWidget(self.plugin_view)
        self.installerpages.addWidget(self.plugin_page_1)
        self.plugin_page_2 = QtWidgets.QWidget()
        self.plugin_page_2.setObjectName("plugin_page_2")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.plugin_page_2)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        spacerItem2 = QtWidgets.QSpacerItem(20, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.verticalLayout_3.addItem(spacerItem2)
        self.plugin_list_2 = QtWidgets.QListWidget(self.plugin_page_2)
        self.plugin_list_2.setObjectName("plugin_list_2")
        item = QtWidgets.QListWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled)
        item.setCheckState(QtCore.Qt.Unchecked)
        self.plugin_list_2.addItem(item)
        item = QtWidgets.QListWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled)
        item.setCheckState(QtCore.Qt.Unchecked)
        self.plugin_list_2.addItem(item)
        self.verticalLayout_3.addWidget(self.plugin_list_2)
        self.installerpages.addWidget(self.plugin_page_2)
        self.verticalLayout_2.addWidget(self.installerpages)
        self.manager_tabs.addTab(self.fomod_tab, "")
        self.gridLayout.addWidget(self.manager_tabs, 0, 0, 1, 4)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 34))
        self.menubar.setObjectName("menubar")
        self.menu_File = QtWidgets.QMenu(self.menubar)
        self.menu_File.setObjectName("menu_File")
        self.menuProfile = QtWidgets.QMenu(self.menubar)
        self.menuProfile.setObjectName("menuProfile")
        self.menuIni_Files = QtWidgets.QMenu(self.menuProfile)
        self.menuIni_Files.setObjectName("menuIni_Files")
        MainWindow.setMenuBar(self.menubar)
        self.toolBar = QtWidgets.QToolBar(MainWindow)
        self.toolBar.setObjectName("toolBar")
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        self.statusBar = QtWidgets.QStatusBar(MainWindow)
        self.statusBar.setObjectName("statusBar")
        MainWindow.setStatusBar(self.statusBar)
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
        self.actionLoad = QtWidgets.QAction(MainWindow)
        self.actionLoad.setObjectName("actionLoad")
        self.actionNew = QtWidgets.QAction(MainWindow)
        self.actionNew.setObjectName("actionNew")
        self.actionDelete = QtWidgets.QAction(MainWindow)
        self.actionDelete.setObjectName("actionDelete")
        self.actionSkyrim_ini = QtWidgets.QAction(MainWindow)
        self.actionSkyrim_ini.setObjectName("actionSkyrim_ini")
        self.actionSkyrimPrefs_ini = QtWidgets.QAction(MainWindow)
        self.actionSkyrimPrefs_ini.setObjectName("actionSkyrimPrefs_ini")
        self.menu_File.addAction(self.action_Install_Fomod)
        self.menu_File.addAction(self.actionChoose_Mod_Folder)
        self.menu_File.addSeparator()
        self.menu_File.addAction(self.action_Quit)
        self.menuIni_Files.addAction(self.actionSkyrim_ini)
        self.menuIni_Files.addAction(self.actionSkyrimPrefs_ini)
        self.menuProfile.addAction(self.actionLoad)
        self.menuProfile.addAction(self.actionNew)
        self.menuProfile.addAction(self.actionDelete)
        self.menuProfile.addSeparator()
        self.menuProfile.addAction(self.menuIni_Files.menuAction())
        self.menubar.addAction(self.menu_File.menuAction())
        self.menubar.addAction(self.menuProfile.menuAction())
        self.toolBar.addAction(self.actionChoose_Mod_Folder)
        self.toolBar.addAction(self.action_Install_Fomod)
        self.profile_label.setBuddy(self.profile_selector)

        self.retranslateUi(MainWindow)
        self.manager_tabs.setCurrentIndex(1)
        self.installerpages.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.next_button.setText(_translate("MainWindow", "Next"))
        self.move_mod_label.setText(_translate("MainWindow", "Install Order:"))
        self.mod_up_button.setStatusTip(_translate("MainWindow", "Move selected mod(s) up in the install order."))
        self.mod_down_button.setStatusTip(_translate("MainWindow", "Move selected mod(s) down in the install order."))
        self.profile_label.setText(_translate("MainWindow", "Profile:"))
        self.profile_selector.setStatusTip(_translate("MainWindow", "Select a profile."))
        self.profile_selector.setItemText(0, _translate("MainWindow", "Default"))
        self.profile_selector.setItemText(1, _translate("MainWindow", "Not Default"))
        self.new_profile_button.setToolTip(_translate("MainWindow", "Add Profile"))
        self.new_profile_button.setStatusTip(_translate("MainWindow", "Create a new profile."))
        self.remove_profile_button.setToolTip(_translate("MainWindow", "Delete Profile"))
        self.remove_profile_button.setStatusTip(_translate("MainWindow", "Delete the active profile."))
        self.remove_profile_button.setText(_translate("MainWindow", "..."))
        self.manager_tabs.setTabText(self.manager_tabs.indexOf(self.installed_mods_tab), _translate("MainWindow", "Mods"))
        self.manager_tabs.setTabToolTip(self.manager_tabs.indexOf(self.installed_mods_tab), _translate("MainWindow", "Currently installed mods"))
        self.filetree_listbox.setTitle(_translate("MainWindow", "Active Mods"))
        self.manager_tabs.setTabText(self.manager_tabs.indexOf(self.filetree_tab), _translate("MainWindow", "Files"))
        __sortingEnabled = self.plugin_list.isSortingEnabled()
        self.plugin_list.setSortingEnabled(False)
        item = self.plugin_list.item(0)
        item.setText(_translate("MainWindow", "Select One Plugin Test"))
        item = self.plugin_list.item(1)
        item.setText(_translate("MainWindow", "ITemtest2"))
        self.plugin_list.setSortingEnabled(__sortingEnabled)
        self.plugin_view.setTitle(_translate("MainWindow", "Description"))
        self.plugin_description_view.setPlaceholderText(_translate("MainWindow", "Testing Testing We\'ll put some stuff here it\'ll be great you just know it haha."))
        __sortingEnabled = self.plugin_list_2.isSortingEnabled()
        self.plugin_list_2.setSortingEnabled(False)
        item = self.plugin_list_2.item(0)
        item.setText(_translate("MainWindow", "Select Any Test"))
        item = self.plugin_list_2.item(1)
        item.setText(_translate("MainWindow", "ITemtest2"))
        self.plugin_list_2.setSortingEnabled(__sortingEnabled)
        self.manager_tabs.setTabText(self.manager_tabs.indexOf(self.fomod_tab), _translate("MainWindow", "Install"))
        self.menu_File.setTitle(_translate("MainWindow", "&File"))
        self.menuProfile.setTitle(_translate("MainWindow", "P&rofile"))
        self.menuIni_Files.setTitle(_translate("MainWindow", "&Ini Files"))
        self.toolBar.setWindowTitle(_translate("MainWindow", "toolBar"))
        self.action_Install_Fomod.setText(_translate("MainWindow", "&Install Fomod..."))
        self.action_Install_Fomod.setShortcut(_translate("MainWindow", "Ctrl+I"))
        self.action_Quit.setText(_translate("MainWindow", "&Quit"))
        self.action_Quit.setShortcut(_translate("MainWindow", "Ctrl+Q"))
        self.actionChoose_Mod_Folder.setText(_translate("MainWindow", "&Choose Mod Folder"))
        self.actionChoose_Mod_Folder.setToolTip(_translate("MainWindow", "Choose Mod Folder"))
        self.actionChoose_Mod_Folder.setShortcut(_translate("MainWindow", "Ctrl+M"))
        self.actionLoad.setText(_translate("MainWindow", "&Load..."))
        self.actionLoad.setShortcut(_translate("MainWindow", "Ctrl+L"))
        self.actionNew.setText(_translate("MainWindow", "&New..."))
        self.actionNew.setShortcut(_translate("MainWindow", "Ctrl+N"))
        self.actionDelete.setText(_translate("MainWindow", "D&elete"))
        self.actionSkyrim_ini.setText(_translate("MainWindow", "&Skyrim.ini"))
        self.actionSkyrimPrefs_ini.setText(_translate("MainWindow", "SkyrimPrefs.&ini"))

