from PyQt5 import QtCore, QtGui, QtWidgets

from . import new_profile_dialog_ui


class PluginPage(QtWidgets.QWidget):

    def __init__(self, page_index: int, selection_type, parent: QtWidgets.QStackedWidget, **kwargs):
        super(PluginPage, self).__init__(parent, **kwargs)

        self.page = page_index
        self.parent = parent
        self.list_type = selection_type

        # set up contained widgets
        self.setObjectName("plugin_page_{}".format(page_index))
        self.grid = QtWidgets.QGridLayout(self)

        #self.spacer

        self.plugin_listw = PluginList(self)

        self.plugin_infow = PluginInfoView(self)

        self.grid.addWidget(self.plugin_listw, 0, 0, 1, 1)
        self.grid.addWidget(self.plugin_infow, 0, 1, 1, 1)


    def setVisibleDescription(self, text):
        self.plugin_infow.description.setText(text)

    def setVisibleImage(self, pixmap:QtGui.QPixmap):
        self.plugin_infow.image.setPixmap(pixmap)




class PluginList(QtWidgets.QListWidget):
    def __init__(self, parent: PluginPage):
        super(PluginList, self).__init__(parent)

        self._type = parent.list_type


    @property
    def type(self):
        return self._type


class PluginItem(QtWidgets.QListWidgetItem):

    FLAGS_FOR_TYPE = {
        "selectAny": {
            "flags": QtCore.Qt.ItemIsSelectable
                      |QtCore.Qt.ItemIsUserCheckable
                      |QtCore.Qt.ItemIsEnabled,
            "checked": QtCore.Qt.Checked
        },
        "selectExactlyOne": {
            "flags": QtCore.Qt.ItemIsSelectable
                      |QtCore.Qt.ItemIsUserCheckable
                      |QtCore.Qt.ItemIsEnabled,
            "checked": QtCore.Qt.Unchecked
        },
        "selectAtMostOne": {
            "flags": QtCore.Qt.ItemIsSelectable
                      |QtCore.Qt.ItemIsUserCheckable
                      |QtCore.Qt.ItemIsEnabled,
            "checked": QtCore.Qt.Unchecked
        },
        "selectAll": {
            "flags": QtCore.Qt.ItemIsSelectable
                      |QtCore.Qt.ItemIsEnabled,
            "checked": None
        }
    }

    def __init__(self, parent: PluginList, *args):
        super(PluginItem, self).__init__(parent, *args)

        self.setFlags(PluginItem.FLAGS_FOR_TYPE[parent.type]["flags"])

        if PluginItem.FLAGS_FOR_TYPE[parent.type]["checked"] is not None:
            self.setCheckState(PluginItem.FLAGS_FOR_TYPE[parent.type]["checked"])


class PluginInfoView(QtWidgets.QGroupBox):
    def __init__(self, parent: PluginPage, *args):
       super(PluginInfoView, self).__init__(parent, *args)

       self.verticalLayout = QtWidgets.QVBoxLayout(self)
       self.plugin_description_view = QtWidgets.QTextBrowser(self)

       self.plugin_image_view = QtWidgets.QLabel(self.plugin_view)

       sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
       sizePolicy.setHorizontalStretch(0)
       sizePolicy.setVerticalStretch(0)
       sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
       self.plugin_image_view.setSizePolicy(sizePolicy)
       self.plugin_image_view.setText("")
       # self.plugin_image_view.setPixmap(QtGui.QPixmap("res/STEP/STEP.png"))
       self.plugin_image_view.setScaledContents(True)
       self.plugin_image_view.setObjectName("label")


       self.verticalLayout.addWidget(self.plugin_description_view)
       self.verticalLayout.addWidget(self.plugin_image_view)


    @property
    def description(self) -> QtWidgets.QTextBrowser:
        return self.plugin_description_view

    # @description.setter
    # def description(self, value):
    #     pass

    @property
    def image(self) -> QtWidgets.QLabel:
        return self.plugin_image_view



class NewProfileDialog(QtWidgets.QDialog, new_profile_dialog_ui.Ui_NewProfileDialog):


    def __init__(self, *args, **kwargs):
        super(NewProfileDialog, self).__init__(*args, **kwargs)

        self.setupUi(self)

        self.okbutton = self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)
        self.okbutton.setDisabled(True)

        self.final_name = None
        self.copy_from = None


        # self.lineEdit.textChanged.connect(self.onTextChange)
        # self.accepted.connect(self.submitData)


    def on_lineEdit_textChanged(self, text):
        if text and self.comboBox.findText(text, QtCore.Qt.MatchFixedString) == -1:
            self.okbutton.setEnabled(True)
        else:
            self.okbutton.setDisabled(True)

    def accept(self):
        # override

        # name input by user
        self.final_name = self.lineEdit.text()

        # profile to copy data from, if selected
        if self.checkBox.isChecked():
            self.copy_from = self.comboBox.currentData()

        # call original accept()
        super(NewProfileDialog, self).accept()





