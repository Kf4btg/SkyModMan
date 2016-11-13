# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'skymodman/interface/designer/ui/manager_window.ui'
#
# Created by: PyQt5 UI code generator 5.7
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self._centralwidget = QtWidgets.QWidget(MainWindow)
        self._centralwidget.setObjectName("_centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self._centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.manager_tabs = QtWidgets.QTabWidget(self._centralwidget)
        self.manager_tabs.setObjectName("manager_tabs")
        self.installed_mods_tab = QtWidgets.QWidget()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.installed_mods_tab.sizePolicy().hasHeightForWidth())
        self.installed_mods_tab.setSizePolicy(sizePolicy)
        self.installed_mods_tab.setObjectName("installed_mods_tab")
        self.installed_mods_layout = QtWidgets.QGridLayout(self.installed_mods_tab)
        self.installed_mods_layout.setContentsMargins(0, 0, 0, 0)
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
        self.profile_selector.setMinimumSize(QtCore.QSize(120, 0))
        self.profile_selector.setEditable(False)
        self.profile_selector.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
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
        self.mod_table = ModTable_TreeView(self.installed_mods_tab)
        self.mod_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.mod_table.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.mod_table.setSelectionMode(QtWidgets.QAbstractItemView.ContiguousSelection)
        self.mod_table.setRootIsDecorated(False)
        self.mod_table.setUniformRowHeights(True)
        self.mod_table.setItemsExpandable(False)
        self.mod_table.setExpandsOnDoubleClick(False)
        self.mod_table.setObjectName("mod_table")
        self.mod_table.header().setStretchLastSection(False)
        self.installed_mods_layout.addWidget(self.mod_table, 1, 0, 1, 3)
        self.manager_tabs.addTab(self.installed_mods_tab, "")
        self.filetree_tab = QtWidgets.QWidget()
        self.filetree_tab.setObjectName("filetree_tab")
        self.gridLayout_6 = QtWidgets.QGridLayout(self.filetree_tab)
        self.gridLayout_6.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self._filetreesplitter = QtWidgets.QSplitter(self.filetree_tab)
        self._filetreesplitter.setOrientation(QtCore.Qt.Horizontal)
        self._filetreesplitter.setObjectName("_filetreesplitter")
        self.filetree_listbox = QtWidgets.QGroupBox(self._filetreesplitter)
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
        self.filetree_modlist = FileTabModList(self.filetree_listbox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.filetree_modlist.sizePolicy().hasHeightForWidth())
        self.filetree_modlist.setSizePolicy(sizePolicy)
        self.filetree_modlist.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.filetree_modlist.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.filetree_modlist.setObjectName("filetree_modlist")
        self.gridLayout_4.addWidget(self.filetree_modlist, 3, 1, 1, 2)
        self.filetree_modfilter = EscapeableLineEdit(self.filetree_listbox)
        self.filetree_modfilter.setClearButtonEnabled(True)
        self.filetree_modfilter.setObjectName("filetree_modfilter")
        self.gridLayout_4.addWidget(self.filetree_modfilter, 4, 1, 1, 2)
        self.filetree_filebox = QtWidgets.QGroupBox(self._filetreesplitter)
        self.filetree_filebox.setFlat(True)
        self.filetree_filebox.setObjectName("filetree_filebox")
        self.fileviewer_box = QtWidgets.QVBoxLayout(self.filetree_filebox)
        self.fileviewer_box.setContentsMargins(6, 6, 6, 6)
        self.fileviewer_box.setObjectName("fileviewer_box")
        self.filetree_fileviewer = FileTabTreeView(self.filetree_filebox)
        self.filetree_fileviewer.setMinimumSize(QtCore.QSize(300, 0))
        self.filetree_fileviewer.setUniformRowHeights(True)
        self.filetree_fileviewer.setObjectName("filetree_fileviewer")
        self.fileviewer_box.addWidget(self.filetree_fileviewer)
        self.filetree_filefilter = EscapeableLineEdit(self.filetree_filebox)
        self.filetree_filefilter.setClearButtonEnabled(True)
        self.filetree_filefilter.setObjectName("filetree_filefilter")
        self.fileviewer_box.addWidget(self.filetree_filefilter)
        self.gridLayout_6.addWidget(self._filetreesplitter, 0, 0, 1, 1)
        self.manager_tabs.addTab(self.filetree_tab, "")
        self.gridLayout.addWidget(self.manager_tabs, 0, 0, 1, 5)
        self.lower_group = QtWidgets.QGroupBox(self._centralwidget)
        self.lower_group.setMinimumSize(QtCore.QSize(350, 0))
        self.lower_group.setFlat(True)
        self.lower_group.setObjectName("lower_group")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.lower_group)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem, 0, 2, 1, 1)
        self.modtable_search_button = QtWidgets.QToolButton(self.lower_group)
        icon = QtGui.QIcon.fromTheme("search")
        self.modtable_search_button.setIcon(icon)
        self.modtable_search_button.setObjectName("modtable_search_button")
        self.gridLayout_2.addWidget(self.modtable_search_button, 0, 0, 1, 1)
        self.next_button = QtWidgets.QPushButton(self.lower_group)
        self.next_button.setEnabled(False)
        self.next_button.setLayoutDirection(QtCore.Qt.LeftToRight)
        icon = QtGui.QIcon.fromTheme("arrow-right")
        self.next_button.setIcon(icon)
        self.next_button.setAutoDefault(True)
        self.next_button.setObjectName("next_button")
        self.gridLayout_2.addWidget(self.next_button, 0, 4, 1, 1)
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
        self.modtable_search_box = EscapeableLineEdit(self.lower_group)
        self.modtable_search_box.setObjectName("modtable_search_box")
        self.gridLayout_2.addWidget(self.modtable_search_box, 0, 1, 1, 1)
        self.gridLayout.addWidget(self.lower_group, 3, 0, 1, 5)
        MainWindow.setCentralWidget(self._centralwidget)
        self._menubar = QtWidgets.QMenuBar(MainWindow)
        self._menubar.setGeometry(QtCore.QRect(0, 0, 800, 34))
        self._menubar.setObjectName("_menubar")
        self.menu_file = QtWidgets.QMenu(self._menubar)
        self.menu_file.setObjectName("menu_file")
        self.menu_profiles = QtWidgets.QMenu(self.menu_file)
        icon = QtGui.QIcon.fromTheme("system-users")
        self.menu_profiles.setIcon(icon)
        self.menu_profiles.setObjectName("menu_profiles")
        self.menu_edit = QtWidgets.QMenu(self._menubar)
        self.menu_edit.setObjectName("menu_edit")
        self.menu_ini_files = QtWidgets.QMenu(self.menu_edit)
        self.menu_ini_files.setObjectName("menu_ini_files")
        self.menu_mod = QtWidgets.QMenu(self._menubar)
        self.menu_mod.setObjectName("menu_mod")
        MainWindow.setMenuBar(self._menubar)
        self.file_toolBar = QtWidgets.QToolBar(MainWindow)
        self.file_toolBar.setMovable(False)
        self.file_toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonFollowStyle)
        self.file_toolBar.setObjectName("file_toolBar")
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.file_toolBar)
        self.status_bar = QtWidgets.QStatusBar(MainWindow)
        self.status_bar.setObjectName("status_bar")
        MainWindow.setStatusBar(self.status_bar)
        self.action_install_mod = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("folder-downloads")
        self.action_install_mod.setIcon(icon)
        self.action_install_mod.setAutoRepeat(False)
        self.action_install_mod.setObjectName("action_install_mod")
        self.action_quit = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("application-exit")
        self.action_quit.setIcon(icon)
        self.action_quit.setObjectName("action_quit")
        self.action_choose_mod_folder = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("folder")
        self.action_choose_mod_folder.setIcon(icon)
        self.action_choose_mod_folder.setAutoRepeat(False)
        self.action_choose_mod_folder.setObjectName("action_choose_mod_folder")
        self.action_load_profile = QtWidgets.QAction(MainWindow)
        self.action_load_profile.setObjectName("action_load_profile")
        self.action_new_profile = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("list-add")
        self.action_new_profile.setIcon(icon)
        self.action_new_profile.setAutoRepeat(False)
        self.action_new_profile.setObjectName("action_new_profile")
        self.action_delete_profile = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("list-remove")
        self.action_delete_profile.setIcon(icon)
        self.action_delete_profile.setObjectName("action_delete_profile")
        self.action_edit_skyrim_ini = QtWidgets.QAction(MainWindow)
        self.action_edit_skyrim_ini.setObjectName("action_edit_skyrim_ini")
        self.action_edit_skyrimprefs_ini = QtWidgets.QAction(MainWindow)
        self.action_edit_skyrimprefs_ini.setObjectName("action_edit_skyrimprefs_ini")
        self.action_toggle_mod = QtWidgets.QAction(MainWindow)
        self.action_toggle_mod.setEnabled(False)
        self.action_toggle_mod.setObjectName("action_toggle_mod")
        self.action_save_changes = QtWidgets.QAction(MainWindow)
        self.action_save_changes.setEnabled(False)
        icon = QtGui.QIcon.fromTheme("edit-save")
        self.action_save_changes.setIcon(icon)
        self.action_save_changes.setAutoRepeat(False)
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
        self.action_revert_changes = QtWidgets.QAction(MainWindow)
        self.action_revert_changes.setEnabled(False)
        icon = QtGui.QIcon.fromTheme("document-revert")
        self.action_revert_changes.setIcon(icon)
        self.action_revert_changes.setAutoRepeat(False)
        self.action_revert_changes.setObjectName("action_revert_changes")
        self.action_find_next = QtWidgets.QAction(MainWindow)
        self.action_find_next.setEnabled(False)
        icon = QtGui.QIcon.fromTheme("go-next")
        self.action_find_next.setIcon(icon)
        self.action_find_next.setObjectName("action_find_next")
        self.action_find_previous = QtWidgets.QAction(MainWindow)
        self.action_find_previous.setEnabled(False)
        icon = QtGui.QIcon.fromTheme("go-previous")
        self.action_find_previous.setIcon(icon)
        self.action_find_previous.setObjectName("action_find_previous")
        self.action_show_search = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("edit-find")
        self.action_show_search.setIcon(icon)
        self.action_show_search.setObjectName("action_show_search")
        self.action_uninstall_mod = QtWidgets.QAction(MainWindow)
        self.action_uninstall_mod.setEnabled(False)
        icon = QtGui.QIcon.fromTheme("edit-delete")
        self.action_uninstall_mod.setIcon(icon)
        self.action_uninstall_mod.setObjectName("action_uninstall_mod")
        self.action_preferences = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("configure")
        self.action_preferences.setIcon(icon)
        self.action_preferences.setAutoRepeat(False)
        self.action_preferences.setObjectName("action_preferences")
        self.action_rename_profile = QtWidgets.QAction(MainWindow)
        self.action_rename_profile.setObjectName("action_rename_profile")
        self.action_reinstall_mod = QtWidgets.QAction(MainWindow)
        self.action_reinstall_mod.setEnabled(False)
        icon = QtGui.QIcon.fromTheme("view-refresh")
        self.action_reinstall_mod.setIcon(icon)
        self.action_reinstall_mod.setAutoRepeat(False)
        self.action_reinstall_mod.setObjectName("action_reinstall_mod")
        self.action_manual_install = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("format-justify-left")
        self.action_manual_install.setIcon(icon)
        self.action_manual_install.setObjectName("action_manual_install")
        self.action_select_all = QtWidgets.QAction(MainWindow)
        self.action_select_all.setEnabled(False)
        icon = QtGui.QIcon.fromTheme("edit-select-all")
        self.action_select_all.setIcon(icon)
        self.action_select_all.setObjectName("action_select_all")
        self.action_select_none = QtWidgets.QAction(MainWindow)
        self.action_select_none.setEnabled(False)
        icon = QtGui.QIcon.fromTheme("edit-select-none")
        self.action_select_none.setIcon(icon)
        self.action_select_none.setObjectName("action_select_none")
        self.action_select_inverse = QtWidgets.QAction(MainWindow)
        self.action_select_inverse.setEnabled(False)
        icon = QtGui.QIcon.fromTheme("edit-select-invert")
        self.action_select_inverse.setIcon(icon)
        self.action_select_inverse.setObjectName("action_select_inverse")
        self.menu_profiles.addAction(self.action_new_profile)
        self.menu_profiles.addAction(self.action_delete_profile)
        self.menu_profiles.addAction(self.action_rename_profile)
        self.menu_file.addAction(self.menu_profiles.menuAction())
        self.menu_file.addAction(self.action_choose_mod_folder)
        self.menu_file.addAction(self.action_preferences)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_quit)
        self.menu_ini_files.addAction(self.action_edit_skyrim_ini)
        self.menu_ini_files.addAction(self.action_edit_skyrimprefs_ini)
        self.menu_edit.addAction(self.action_save_changes)
        self.menu_edit.addAction(self.action_revert_changes)
        self.menu_edit.addSeparator()
        self.menu_edit.addAction(self.action_select_all)
        self.menu_edit.addAction(self.action_select_none)
        self.menu_edit.addSeparator()
        self.menu_edit.addAction(self.menu_ini_files.menuAction())
        self.menu_mod.addAction(self.action_install_mod)
        self.menu_mod.addAction(self.action_manual_install)
        self.menu_mod.addAction(self.action_reinstall_mod)
        self.menu_mod.addAction(self.action_uninstall_mod)
        self.menu_mod.addSeparator()
        self.menu_mod.addAction(self.action_show_search)
        self.menu_mod.addAction(self.action_find_next)
        self.menu_mod.addAction(self.action_find_previous)
        self.menu_mod.addAction(self.action_toggle_mod)
        self.menu_mod.addSeparator()
        self.menu_mod.addAction(self.action_move_mod_up)
        self.menu_mod.addAction(self.action_move_mod_down)
        self.menu_mod.addAction(self.action_move_mod_to_top)
        self.menu_mod.addAction(self.action_move_mod_to_bottom)
        self._menubar.addAction(self.menu_file.menuAction())
        self._menubar.addAction(self.menu_edit.menuAction())
        self._menubar.addAction(self.menu_mod.menuAction())
        self.file_toolBar.addAction(self.action_install_mod)
        self.file_toolBar.addAction(self.action_manual_install)
        self.file_toolBar.addSeparator()
        self.file_toolBar.addAction(self.action_preferences)
        self.profile_label.setBuddy(self.profile_selector)

        self.retranslateUi(MainWindow)
        self.manager_tabs.setCurrentIndex(1)
        self.action_show_search.triggered.connect(self.modtable_search_button.click)
        self.modtable_search_box.escapeLineEdit.connect(self.modtable_search_button.click)
        self.filetree_modfilter.escapeLineEdit.connect(self.filetree_modfilter.clear)
        self.filetree_filefilter.escapeLineEdit.connect(self.filetree_filefilter.clear)
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
        self.filetree_modfilter.setToolTip(_translate("MainWindow", "Filter by mod name"))
        self.filetree_modfilter.setPlaceholderText(_translate("MainWindow", "Filter"))
        self.filetree_filefilter.setToolTip(_translate("MainWindow", "Filter by file name"))
        self.filetree_filefilter.setPlaceholderText(_translate("MainWindow", "Filter"))
        self.manager_tabs.setTabText(self.manager_tabs.indexOf(self.filetree_tab), _translate("MainWindow", "Files"))
        self.modtable_search_button.setToolTip(_translate("MainWindow", "Find"))
        self.next_button.setText(_translate("MainWindow", "Next"))
        self.modtable_search_box.setToolTip(_translate("MainWindow", "Hit Enter to Search"))
        self.modtable_search_box.setPlaceholderText(_translate("MainWindow", "Search"))
        self.menu_file.setTitle(_translate("MainWindow", "&File"))
        self.menu_profiles.setTitle(_translate("MainWindow", "P&rofiles"))
        self.menu_edit.setTitle(_translate("MainWindow", "&Edit"))
        self.menu_ini_files.setTitle(_translate("MainWindow", "&Ini Files"))
        self.menu_mod.setTitle(_translate("MainWindow", "&Mod"))
        self.file_toolBar.setWindowTitle(_translate("MainWindow", "toolBar"))
        self.action_install_mod.setText(_translate("MainWindow", "&Install..."))
        self.action_install_mod.setToolTip(_translate("MainWindow", "Install Mod From Archive"))
        self.action_install_mod.setStatusTip(_translate("MainWindow", "Install a mod archive using the Automated Installer."))
        self.action_install_mod.setShortcut(_translate("MainWindow", "Ctrl+I"))
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
        self.action_toggle_mod.setText(_translate("MainWindow", "Toggle &Selection Active"))
        self.action_toggle_mod.setToolTip(_translate("MainWindow", "Enable or Disable Selected Mod(s)"))
        self.action_toggle_mod.setShortcut(_translate("MainWindow", "Space"))
        self.action_save_changes.setText(_translate("MainWindow", "&Save Changes"))
        self.action_save_changes.setStatusTip(_translate("MainWindow", "Save Changes"))
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
        self.action_revert_changes.setText(_translate("MainWindow", "Revert &Changes"))
        self.action_revert_changes.setToolTip(_translate("MainWindow", "Revert all unsaved changes"))
        self.action_revert_changes.setStatusTip(_translate("MainWindow", "Reset to last saved state, undoing any unsaved changes"))
        self.action_revert_changes.setShortcut(_translate("MainWindow", "Ctrl+Shift+R"))
        self.action_find_next.setText(_translate("MainWindow", "&Find Next"))
        self.action_find_next.setToolTip(_translate("MainWindow", "Find Next Occurrence"))
        self.action_find_previous.setText(_translate("MainWindow", "Find &Previous"))
        self.action_find_previous.setToolTip(_translate("MainWindow", "Find Previous Occurrence"))
        self.action_show_search.setText(_translate("MainWindow", "S&how Search Bar"))
        self.action_uninstall_mod.setText(_translate("MainWindow", "&Uninstall"))
        self.action_preferences.setText(_translate("MainWindow", "&Preferences"))
        self.action_preferences.setShortcut(_translate("MainWindow", "Ctrl+P"))
        self.action_rename_profile.setText(_translate("MainWindow", "&Rename..."))
        self.action_rename_profile.setToolTip(_translate("MainWindow", "Rename Profile"))
        self.action_reinstall_mod.setText(_translate("MainWindow", "&Reinstall"))
        self.action_reinstall_mod.setToolTip(_translate("MainWindow", "Reinstall Mod"))
        self.action_reinstall_mod.setStatusTip(_translate("MainWindow", "Rerun installation for selected mod"))
        self.action_manual_install.setText(_translate("MainWindow", "Ma&nual Install..."))
        self.action_manual_install.setToolTip(_translate("MainWindow", "Manually Install a Mod Archive"))
        self.action_manual_install.setStatusTip(_translate("MainWindow", "Manually define which of the contents from a mod archive to install."))
        self.action_manual_install.setShortcut(_translate("MainWindow", "Ctrl+Shift+I"))
        self.action_select_all.setText(_translate("MainWindow", "S&elect All"))
        self.action_select_none.setText(_translate("MainWindow", "C&lear Selection"))
        self.action_select_inverse.setText(_translate("MainWindow", "Invert Selection"))

from skymodman.interface.designer.plugins.widgets.escapeablelineedit import EscapeableLineEdit
from skymodman.interface.views.filetab_modlist import FileTabModList
from skymodman.interface.views.filetab_treeview import FileTabTreeView
from skymodman.interface.views.modtable_treeview import ModTable_TreeView
