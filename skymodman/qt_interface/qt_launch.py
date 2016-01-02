import sys

from PyQt5.QtCore import Qt, QStandardPaths, QDir, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QFileDialog, QFileSystemModel, QDialogButtonBox

import skymodman.constants as const
from skymodman.qt_interface.qt_manager_ui import Ui_MainWindow
from skymodman.utils import withlogger
# from collections import OrderedDict

@withlogger
class ModManagerWindow(QMainWindow, Ui_MainWindow):

    modListModified = pyqtSignal()
    modListSaved = pyqtSignal()
    changesCanceled = pyqtSignal()
    

    def __init__(self, mmanager: 'managers.ModManager', *args, **kwargs):
        super(ModManagerWindow, self).__init__(*args, **kwargs)
        self.LOGGER.debug("Initializing ModManager Window")

        self._manager = mmanager # grab a reference to the singleton Mod Manager

        # setup the ui
        self.setupUi(self)

        # connect the buttons

        # use a dialog-button-box
        # no helper signal (like accepted()) for these,
        # so have to specify it by standard button type
        self.save_cancel_btnbox.button(QDialogButtonBox.Apply).clicked.connect(self.saveModsList)
        self.save_cancel_btnbox.button(QDialogButtonBox.Reset).clicked.connect(self.resetTable)

        # connect the actions
        self.action_Quit.triggered.connect(quit_app)
        self.action_Install_Fomod.triggered.connect(self.loadFomod)

        # list of (modname, modId, modVersion) tuples
        # self.mods_list = load_mods(self._manager.Config.modsdirectory)
        # self.mods_list = self._manager.modinfo

        # setup table of installed mods
        self.mod_table.setColumnCount(4)
        self.mod_table.setHorizontalHeaderLabels(["", "Mod ID",
                                                  "Version",
                                                  "Name",
                                                  ])
        # populate from cached mod-info
        self.populateModTable()
        # enable sorting AFTER population
        self.mod_table.setSortingEnabled(True)
        # let double clicking toggle the checkbox
        self.mod_table.cellDoubleClicked.connect(self.toggleModState)
        # make columns fit their contents
        self.mod_table.resizeColumnsToContents()


        # keep track of changes made to mod list
        # self.mod_list_modified = False
        self.file_tree_modified = False

        # set placeholder fields
        self.loaded_fomod = None
        
        # make some UI adjustments
        self.manager_tabs.setCurrentIndex(0)
        self.installerpages.setCurrentIndex(0)

        # these should be disabled until a change is made,
        # self.modListModified.connect(self.enableSaveCancelButtons)
        # self.modListSaved.connect(self.disableSaveCancelButtons)
        self.changesCanceled.connect(self.resetTable)

        # set up file-tree view and model
        self.file_tree_model = QFileSystemModel()
        self.file_tree_model.setRootPath(self._manager.Config['dir_mods'])
        self.filetree_tree.setModel(self.file_tree_model)
        self.filetree_tree.setRootIndex(self.file_tree_model.index(self._manager.Config["dir_mods"]))

        # connect other signals
        self.manager_tabs.currentChanged.connect(self.updateUI)
        # self.mod_table.cellChanged.connect(self.onTableModified)
        self.mod_table.cellChanged.connect(self.cellChanged)

        # tracking modified rows; using list or ordered dict might allow for an "undo" function later
        self._modified_cells = [] # list of point-tuples (row, column) for fields in table


        # update UI
        self.updateUI()

    def cellChanged(self, row, col):
        self.LOGGER.debug("Cell ({}, {}) changed".format(row, col))

        # only enable on first change
        # if not self.mod_list_modified:

        # if the list of changes is empty:
        if not self._modified_cells:
            # self.mod_list_modified = True
            self.save_cancel_btnbox.setEnabled(True)

        self._modified_cells.append((row, col))


    @property
    def Manager(self):
        return self._manager

    def updateUI(self, *args):
        if self.loaded_fomod is None:
            self.fomod_tab.setEnabled(False)

        curtab = self.manager_tabs.currentIndex()

        self.save_cancel_btnbox.setVisible(curtab in [const.TAB_MODLIST, const.TAB_FILETREE])

        if self.save_cancel_btnbox.isVisible():
            self.save_cancel_btnbox.setEnabled(
                (curtab == const.TAB_MODLIST and len(self._modified_cells)>0)
            or  (curtab == const.TAB_FILETREE and self.file_tree_modified)
            )

        self.next_button.setVisible(curtab == const.TAB_INSTALLER)

    @pyqtSlot()
    def saveModsList(self):
        """
        If the list of installed mods has been modified (e.g.
        some mods marked inactive, names changed, etc.), save
        the modified status of the mods to a file
        :return:
        """
        # self.Manager.saveModList(self.modsByState())


        ## TODO: delegate this process to the mod manager
        for cell in self._modified_cells:
            if cell[1] == const.COL_NAME:
                ## NOTE: XXX: FIXME: TODO: remember that the "install order" (db primary key) starts at one
                self.Manager.DB.updateField(cell[0]+1, cell[1], self.mod_table.item(cell[0], cell[1]).text())
            else:
                self.Manager.DB.updateField(cell[0]+1, cell[1], bool(self.mod_table.item(cell[0], cell[1]).checkState()))

        self.Manager.saveModList()

        self._modified_cells.clear()
        # self.modListSaved.emit()
        self.updateUI()


    def loadFomod(self):
        # mimes = [m for m in QImageReader.supportedMimeTypes()]
        # print(mimes)
        # mimes = ['application/x-7z-compressed']
        mimes = ['application/xml']
        start_locs = QStandardPaths.standardLocations(QStandardPaths.HomeLocation) # type: List[str]
        dialog = QFileDialog(self, "Choose ModuleConfig.xml file",
                             QDir.currentPath()
                             # start_locs.pop() if start_locs else QDir.currentPath()
                             )
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setMimeTypeFilters(mimes)
        dialog.selectMimeTypeFilter(mimes[0])

        if dialog.exec_() == QFileDialog.Accepted:
            files = dialog.selectedFiles()
            print(files)

            self.loaded_fomod = files[0]
            # todo: maybe run this method in a separate thread? at least the dialog
            # todo: setup 2nd tab with data from xml file and begin installation process
            # todo: support loading actual fomod archives. (7z, rar, zip, etc.)



    def getTab(self, index:int):
        return self.manager_tabs.widget(index)

    # ===================================
    # TABLE OF INSTALLED MODS FUNCTIONS
    # ===================================

    def toggleModState(self, row, column):
        if column > 2: return #only the first 3 columns (box, id, ver)

        # grab the first column ( the checkable one)
        item = self.mod_table.item(row, const.COL_ENABLED)
        item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)


    def populateModTable(self):
        self.mod_table.blockSignals(True)
        r=0

        #clear placeholder values
        self.mod_table.clearContents()
        self.mod_table.setRowCount(0)

        # for m in self.Manager.allmods():
        for m in self.Manager.DB.conn.execute("SELECT name, modid, version, enabled FROM mods"):
            self.mod_table.insertRow(r)
            _name, _id, _ver, _enabled = m
            # self.LOGGER.debug("{} {} {} {}".format(_name, _id, _ver, _enabled))

            items = (QTableWidgetItem(), # first column is empty, is for the checkbox
                QTableWidgetItem(str(_id)),
                    QTableWidgetItem(_ver),
                    QTableWidgetItem(_name),
                     )

            # 1st column has checkbox indicating whether or not the mod is active
            items[const.COL_ENABLED].setFlags(Qt.ItemIsUserCheckable
                                              | Qt.ItemIsEnabled
                                              # | Qt.ItemIsDragEnabled
                                              # | Qt.ItemIsDropEnabled
                                              # | Qt.DragMoveCursor
                                              )
            # set check state from saved state
            items[const.COL_ENABLED].setCheckState(Qt.Checked if _enabled else Qt.Unchecked)

            items[const.COL_MODID].setFlags(Qt.ItemIsSelectable
                                            | Qt.ItemIsEnabled
                                            # | Qt.ItemIsDragEnabled
                                            # | Qt.ItemIsDropEnabled
                                            # | Qt.DragMoveCursor
                                            )

            # Version can just be selected
            items[const.COL_VERSION].setFlags(Qt.ItemIsSelectable
                                              | Qt.ItemIsEnabled
                                              # | Qt.ItemIsDragEnabled
                                              # | Qt.ItemIsDropEnabled
                                              # | Qt.DragMoveCursor
                                              )
            # name can be edited
            # todo: save changes to name
            items[const.COL_NAME].setFlags(Qt.ItemIsSelectable
                                           | Qt.ItemIsEditable
                                           | Qt.ItemIsEnabled
                                           # | Qt.ItemIsDragEnabled
                                           # | Qt.ItemIsDropEnabled
                                           # | Qt.DragMoveCursor
                                           )

            for i in range(4):
                self.mod_table.setItem(r,i,items[i])

            r+=1
        self.mod_table.blockSignals(False)

    def syncModListWithStates(self):

        for cell in self._modified_cells:
            row, col = cell   # get parts of tuple

            #TODO: remember! that db numbers start at 1!
            modinfo = self.Manager.DB.conn.execute("SELECT enabled, name FROM mods WHERE iorder = ?", [row+1]).fetchone()

            if col == const.COL_ENABLED:
                self.mod_table.item(row,
                                    const.COL_ENABLED)\
                    .setCheckState(Qt.Checked if modinfo[0]   ## these should sync up...unless i'm bad at math
                                                   else Qt.Unchecked)
            elif col == const.COL_NAME:
                self.mod_table.item(row, const.COL_NAME).setText(modinfo[1])


    def resetTable(self):
        self.mod_table.blockSignals(True)
        self.syncModListWithStates()
        self._modified_cells.clear()

        # self.mod_list_modified = False
        # self.disableSaveCancelButtons(
        self.mod_table.blockSignals(False)
        self.updateUI()

    # SLOTS


    # def enableSaveCancelButtons(self):
    #     if not self.save_button.isEnabled():
    #         self.LOGGER.debug("Save/Cancel buttons enabled")
    #         self.save_button.setEnabled(True)
    #         self.cancel_button.setEnabled(True)
    #
    # def disableSaveCancelButtons(self):
    #     self.LOGGER.debug("Save/Cancel buttons disabled")
    #     self.save_button.setEnabled(False)
    #     self.cancel_button.setEnabled(False)

    # def onTableModified(self, row:int , col: int):
    #     if col in [const.COL_ENABLED, const.COL_NAME]: # checkbox or name
    #         self.mod_list_modified = True
    #         # self.updateUI()
    #         self.modListModified.emit()



def quit_app():
    skylog.stop_listener()
    QApplication.quit()

if __name__ == '__main__':

    from skymodman import managers, skylog

    app = QApplication(sys.argv)

    MM = managers.ModManager()

    w = ModManagerWindow(MM)
    w.resize(QGuiApplication.primaryScreen().availableSize()*3/5)
    w.show()

    sys.exit(app.exec_())
