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
        self.installed_mods_layout.addWidget(self.profile_group, 0, 0, 1, 2)
        self.filters_dropdown = QtWidgets.QToolButton(self.installed_mods_tab)
        self.filters_dropdown.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.filters_dropdown.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.filters_dropdown.setObjectName("filters_dropdown")
        self.installed_mods_layout.addWidget(self.filters_dropdown, 0, 2, 1, 1)
        self.manager_tabs.addTab(self.installed_mods_tab, "")
        self.filetree_tab = QtWidgets.QWidget()
        self.filetree_tab.setObjectName("filetree_tab")
        self.gridLayout_6 = QtWidgets.QGridLayout(self.filetree_tab)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.splitter = QtWidgets.QSplitter(self.filetree_tab)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.filetree_listbox = QtWidgets.QGroupBox(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.filetree_listbox.sizePolicy().hasHeightForWidth())
        self.filetree_listbox.setSizePolicy(sizePolicy)
        self.filetree_listbox.setMinimumSize(QtCore.QSize(250, 0))
        self.filetree_listbox.setFlat(True)
        self.filetree_listbox.setObjectName("filetree_listbox")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.filetree_listbox)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.filetree_listlabel = QtWidgets.QLabel(self.filetree_listbox)
        self.filetree_listlabel.setObjectName("filetree_listlabel")
        self.gridLayout_4.addWidget(self.filetree_listlabel, 1, 1, 1, 1)
        self.filetree_activeonlytoggle = QtWidgets.QCheckBox(self.filetree_listbox)
        self.filetree_activeonlytoggle.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.filetree_activeonlytoggle.setChecked(True)
        self.filetree_activeonlytoggle.setObjectName("filetree_activeonlytoggle")
        self.gridLayout_4.addWidget(self.filetree_activeonlytoggle, 1, 2, 1, 1)
        self.filetree_modlist = QtWidgets.QListView(self.filetree_listbox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.filetree_modlist.sizePolicy().hasHeightForWidth())
        self.filetree_modlist.setSizePolicy(sizePolicy)
        self.filetree_modlist.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.filetree_modlist.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.filetree_modlist.setObjectName("filetree_modlist")
        self.gridLayout_4.addWidget(self.filetree_modlist, 3, 1, 1, 2)
        self.filetree_modfilter = QtWidgets.QLineEdit(self.filetree_listbox)
        self.filetree_modfilter.setClearButtonEnabled(True)
        self.filetree_modfilter.setObjectName("filetree_modfilter")
        self.gridLayout_4.addWidget(self.filetree_modfilter, 4, 1, 1, 2)
        self.filetree_filebox = QtWidgets.QGroupBox(self.splitter)
        self.filetree_filebox.setFlat(True)
        self.filetree_filebox.setObjectName("filetree_filebox")
        self.fileviewer_box = QtWidgets.QVBoxLayout(self.filetree_filebox)
        self.fileviewer_box.setContentsMargins(6, 6, 6, 6)
        self.fileviewer_box.setObjectName("fileviewer_box")
        self.filetree_fileviewer = QtWidgets.QTreeView(self.filetree_filebox)
        self.filetree_fileviewer.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.filetree_fileviewer.setUniformRowHeights(True)
        self.filetree_fileviewer.setObjectName("filetree_fileviewer")
        self.fileviewer_box.addWidget(self.filetree_fileviewer)
        self.filetree_filefilter = QtWidgets.QLineEdit(self.filetree_filebox)
        self.filetree_filefilter.setClearButtonEnabled(True)
        self.filetree_filefilter.setObjectName("filetree_filefilter")
        self.fileviewer_box.addWidget(self.filetree_filefilter)
        self.gridLayout_6.addWidget(self.splitter, 0, 0, 1, 1)
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
        spacerItem = QtWidgets.QSpacerItem(20, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.verticalLayout_3.addItem(spacerItem)
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
        self.gridLayout.addWidget(self.manager_tabs, 0, 0, 1, 5)
        self.lower_group = QtWidgets.QGroupBox(self.centralwidget)
        self.lower_group.setMinimumSize(QtCore.QSize(350, 0))
        self.lower_group.setFlat(True)
        self.lower_group.setObjectName("lower_group")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.lower_group)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.modtable_search_button = QtWidgets.QToolButton(self.lower_group)
        icon = QtGui.QIcon.fromTheme("search")
        self.modtable_search_button.setIcon(icon)
        self.modtable_search_button.setObjectName("modtable_search_button")
        self.gridLayout_2.addWidget(self.modtable_search_button, 0, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem1, 0, 2, 1, 1)
        self.modtable_search_box = QtWidgets.QLineEdit(self.lower_group)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.modtable_search_box.sizePolicy().hasHeightForWidth())
        self.modtable_search_box.setSizePolicy(sizePolicy)
        self.modtable_search_box.setObjectName("modtable_search_box")
        self.gridLayout_2.addWidget(self.modtable_search_box, 0, 1, 1, 1)
        self.save_cancel_btnbox = QtWidgets.QDialogButtonBox(self.lower_group)
        self.save_cancel_btnbox.setEnabled(False)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.save_cancel_btnbox.sizePolicy().hasHeightForWidth())
        self.save_cancel_btnbox.setSizePolicy(sizePolicy)
        self.save_cancel_btnbox.setStandardButtons(QtWidgets.QDialogButtonBox.Apply|QtWidgets.QDialogButtonBox.Reset)
        self.save_cancel_btnbox.setObjectName("save_cancel_btnbox")
        self.gridLayout_2.addWidget(self.save_cancel_btnbox, 0, 3, 1, 1)
        self.next_button = QtWidgets.QPushButton(self.lower_group)
        self.next_button.setEnabled(False)
        self.next_button.setLayoutDirection(QtCore.Qt.LeftToRight)
        icon = QtGui.QIcon.fromTheme("arrow-right")
        self.next_button.setIcon(icon)
        self.next_button.setAutoDefault(True)
        self.next_button.setObjectName("next_button")
        self.gridLayout_2.addWidget(self.next_button, 0, 4, 1, 1)
        self.gridLayout.addWidget(self.lower_group, 3, 0, 1, 5)
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
        self.menuEdit = QtWidgets.QMenu(self.menubar)
        self.menuEdit.setObjectName("menuEdit")
        MainWindow.setMenuBar(self.menubar)
        self.file_toolBar = QtWidgets.QToolBar(MainWindow)
        self.file_toolBar.setObjectName("file_toolBar")
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.file_toolBar)
        self.statusBar = QtWidgets.QStatusBar(MainWindow)
        self.statusBar.setObjectName("statusBar")
        MainWindow.setStatusBar(self.statusBar)
        self.action_install_fomod = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("package-x-generic")
        self.action_install_fomod.setIcon(icon)
        self.action_install_fomod.setObjectName("action_install_fomod")
        self.action_quit = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("application-exit")
        self.action_quit.setIcon(icon)
        self.action_quit.setObjectName("action_quit")
        self.action_choose_mod_folder = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("folder")
        self.action_choose_mod_folder.setIcon(icon)
        self.action_choose_mod_folder.setObjectName("action_choose_mod_folder")
        self.action_load_profile = QtWidgets.QAction(MainWindow)
        self.action_load_profile.setObjectName("action_load_profile")
        self.action_new_profile = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("add")
        self.action_new_profile.setIcon(icon)
        self.action_new_profile.setObjectName("action_new_profile")
        self.action_delete_profile = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("remove")
        self.action_delete_profile.setIcon(icon)
        self.action_delete_profile.setObjectName("action_delete_profile")
        self.action_edit_skyrim_ini = QtWidgets.QAction(MainWindow)
        self.action_edit_skyrim_ini.setObjectName("action_edit_skyrim_ini")
        self.action_edit_skyrimprefs_ini = QtWidgets.QAction(MainWindow)
        self.action_edit_skyrimprefs_ini.setObjectName("action_edit_skyrimprefs_ini")
        self.action_undo = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("edit-undo")
        self.action_undo.setIcon(icon)
        self.action_undo.setObjectName("action_undo")
        self.action_redo = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("edit-redo")
        self.action_redo.setIcon(icon)
        self.action_redo.setObjectName("action_redo")
        self.action_toggle_mod = QtWidgets.QAction(MainWindow)
        self.action_toggle_mod.setEnabled(False)
        self.action_toggle_mod.setObjectName("action_toggle_mod")
        self.action_save_changes = QtWidgets.QAction(MainWindow)
        self.action_save_changes.setEnabled(False)
        icon = QtGui.QIcon.fromTheme("edit-save")
        self.action_save_changes.setIcon(icon)
        self.action_save_changes.setObjectName("action_save_changes")
        self.action_move_mod_up = QtWidgets.QAction(MainWindow)
        self.action_move_mod_up.setEnabled(False)
        icon = QtGui.QIcon.fromTheme("arrow-up")
        self.action_move_mod_up.setIcon(icon)
        self.action_move_mod_up.setObjectName("action_move_mod_up")
        self.action_move_mod_down = QtWidgets.QAction(MainWindow)
        self.action_move_mod_down.setEnabled(False)
        icon = QtGui.QIcon.fromTheme("arrow-down")
        self.action_move_mod_down.setIcon(icon)
        self.action_move_mod_down.setObjectName("action_move_mod_down")
        self.action_move_mod_to_top = QtWidgets.QAction(MainWindow)
        self.action_move_mod_to_top.setEnabled(False)
        icon = QtGui.QIcon.fromTheme("go-top")
        self.action_move_mod_to_top.setIcon(icon)
        self.action_move_mod_to_top.setObjectName("action_move_mod_to_top")
        self.action_move_mod_to_bottom = QtWidgets.QAction(MainWindow)
        self.action_move_mod_to_bottom.setEnabled(False)
        icon = QtGui.QIcon.fromTheme("go-bottom")
        self.action_move_mod_to_bottom.setIcon(icon)
        self.action_move_mod_to_bottom.setObjectName("action_move_mod_to_bottom")
        self.menu_File.addAction(self.action_install_fomod)
        self.menu_File.addAction(self.action_choose_mod_folder)
        self.menu_File.addSeparator()
        self.menu_File.addAction(self.action_save_changes)
        self.menu_File.addAction(self.action_quit)
        self.menuIni_Files.addAction(self.action_edit_skyrim_ini)
        self.menuIni_Files.addAction(self.action_edit_skyrimprefs_ini)
        self.menuProfile.addAction(self.action_load_profile)
        self.menuProfile.addAction(self.action_new_profile)
        self.menuProfile.addAction(self.action_delete_profile)
        self.menuProfile.addSeparator()
        self.menuProfile.addAction(self.menuIni_Files.menuAction())
        self.menuEdit.addAction(self.action_undo)
        self.menuEdit.addAction(self.action_redo)
        self.menuEdit.addSeparator()
        self.menuEdit.addAction(self.action_toggle_mod)
        self.menuEdit.addSeparator()
        self.menuEdit.addAction(self.action_move_mod_up)
        self.menuEdit.addAction(self.action_move_mod_down)
        self.menuEdit.addAction(self.action_move_mod_to_top)
        self.menuEdit.addAction(self.action_move_mod_to_bottom)
        self.menubar.addAction(self.menu_File.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menuProfile.menuAction())
        self.file_toolBar.addAction(self.action_choose_mod_folder)
        self.file_toolBar.addAction(self.action_install_fomod)
        self.profile_label.setBuddy(self.profile_selector)

        self.retranslateUi(MainWindow)
        self.manager_tabs.setCurrentIndex(0)
        self.installerpages.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.profile_label.setText(_translate("MainWindow", "Profile:"))
        self.profile_selector.setStatusTip(_translate("MainWindow", "Select a profile."))
        self.profile_selector.setItemText(0, _translate("MainWindow", "Default"))
        self.profile_selector.setItemText(1, _translate("MainWindow", "Not Default"))
        self.filters_dropdown.setText(_translate("MainWindow", "Filters"))
        self.manager_tabs.setTabText(self.manager_tabs.indexOf(self.installed_mods_tab), _translate("MainWindow", "Mods"))
        self.manager_tabs.setTabToolTip(self.manager_tabs.indexOf(self.installed_mods_tab), _translate("MainWindow", "Currently installed mods"))
        self.filetree_listlabel.setText(_translate("MainWindow", "Installed Mods"))
        self.filetree_activeonlytoggle.setToolTip(_translate("MainWindow", "Only Show Active Mods"))
        self.filetree_activeonlytoggle.setStatusTip(_translate("MainWindow", "Show or hide inactive mods in list"))
        self.filetree_modfilter.setPlaceholderText(_translate("MainWindow", "Filter"))
        self.filetree_filefilter.setPlaceholderText(_translate("MainWindow", "Filter"))
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
        self.modtable_search_button.setToolTip(_translate("MainWindow", "Find"))
        self.modtable_search_box.setToolTip(_translate("MainWindow", "Type to search mod list"))
        self.modtable_search_box.setPlaceholderText(_translate("MainWindow", "Search"))
        self.next_button.setText(_translate("MainWindow", "Next"))
        self.menu_File.setTitle(_translate("MainWindow", "&File"))
        self.menuProfile.setTitle(_translate("MainWindow", "Prof&ile"))
        self.menuIni_Files.setTitle(_translate("MainWindow", "&Ini Files"))
        self.menuEdit.setTitle(_translate("MainWindow", "E&dit"))
        self.file_toolBar.setWindowTitle(_translate("MainWindow", "toolBar"))
        self.action_install_fomod.setText(_translate("MainWindow", "&Install Fomod..."))
        self.action_install_fomod.setShortcut(_translate("MainWindow", "Ctrl+I"))
        self.action_quit.setText(_translate("MainWindow", "&Quit"))
        self.action_quit.setShortcut(_translate("MainWindow", "Ctrl+Q"))
        self.action_choose_mod_folder.setText(_translate("MainWindow", "&Choose Mod Folder"))
        self.action_choose_mod_folder.setToolTip(_translate("MainWindow", "Choose Mod Folder"))
        self.action_choose_mod_folder.setShortcut(_translate("MainWindow", "Ctrl+M"))
        self.action_load_profile.setText(_translate("MainWindow", "&Load..."))
        self.action_load_profile.setShortcut(_translate("MainWindow", "Ctrl+L"))
        self.action_new_profile.setText(_translate("MainWindow", "&New..."))
        self.action_new_profile.setToolTip(_translate("MainWindow", "Create New Profile"))
        self.action_new_profile.setShortcut(_translate("MainWindow", "Ctrl+N"))
        self.action_delete_profile.setText(_translate("MainWindow", "D&elete"))
        self.action_delete_profile.setToolTip(_translate("MainWindow", "Remove Profile"))
        self.action_edit_skyrim_ini.setText(_translate("MainWindow", "&Skyrim.ini"))
        self.action_edit_skyrimprefs_ini.setText(_translate("MainWindow", "SkyrimPrefs.&ini"))
        self.action_undo.setText(_translate("MainWindow", "&Undo"))
        self.action_undo.setShortcut(_translate("MainWindow", "Ctrl+Z"))
        self.action_redo.setText(_translate("MainWindow", "&Redo"))
        self.action_redo.setShortcut(_translate("MainWindow", "Ctrl+Shift+Z"))
        self.action_toggle_mod.setText(_translate("MainWindow", "Toggle &Selection Active"))
        self.action_toggle_mod.setToolTip(_translate("MainWindow", "Enable or Disable Selected Mod(s)"))
        self.action_toggle_mod.setShortcut(_translate("MainWindow", "Space"))
        self.action_save_changes.setText(_translate("MainWindow", "&Save Changes"))
        self.action_move_mod_up.setText(_translate("MainWindow", "&Move Mod Up"))
        self.action_move_mod_up.setToolTip(_translate("MainWindow", "Move mod earlier in the install sequence"))
        self.action_move_mod_up.setShortcut(_translate("MainWindow", "Ctrl+Up"))
        self.action_move_mod_down.setText(_translate("MainWindow", "Move Mod &Down"))
        self.action_move_mod_down.setToolTip(_translate("MainWindow", "Move mod later in the install sequence"))
        self.action_move_mod_down.setShortcut(_translate("MainWindow", "Ctrl+Down"))
        self.action_move_mod_to_top.setText(_translate("MainWindow", "M&ove Mod To Top"))
        self.action_move_mod_to_top.setToolTip(_translate("MainWindow", "Move mod to the start of the install sequence"))
        self.action_move_mod_to_top.setShortcut(_translate("MainWindow", "Ctrl+Shift+Up"))
        self.action_move_mod_to_bottom.setText(_translate("MainWindow", "Move Mod To &Bottom"))
        self.action_move_mod_to_bottom.setToolTip(_translate("MainWindow", "Move mod to the end of the install sequence"))
        self.action_move_mod_to_bottom.setShortcut(_translate("MainWindow", "Ctrl+Shift+Down"))

