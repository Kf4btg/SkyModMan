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


    def __init__(self, combobox_model, *args, **kwargs):
        super(NewProfileDialog, self).__init__(*args, **kwargs)

        self.setupUi(self)

        self.okbutton = self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok) #type: QtWidgets.QPushButton
        self.okbutton.setDisabled(True)

        self.final_name = None
        self.copy_from = None

        self.comboBox.setModel(combobox_model)

        # self.re = "^(" + "|".join([p.name for p in combobox_model.profiles]) + ")$"

        # according to timeit, checking if a word is in a list is faster than checking against
        # a RegExp--even a compiled RE, and even if you pre-process the word to check each time
        # (e.g.: word.lower() in wordlist)
        self.name_list = [p.name.lower() for p in combobox_model.profiles]

        # this validator ensures that no spaces or invalid characters can be entered.
        # (only letters, numbers, underscores, hyphens, and periods)
        vre_str = r"[\w\d_.-]+"
        self.vre = QtCore.QRegularExpression(vre_str)
        self.validator = QtGui.QRegularExpressionValidator(self.vre)

        self.lineEdit.setValidator(self.validator)

        # stylesheet for invalid text
        self.ss_invalid = "QLineEdit { color: red }"

        # tooltip for invalid text
        self.tt_invalid = "Profile names must be unique"


    def on_lineEdit_textChanged(self, text:str):
        """
        This slot handles giving feedback to the user about the validity of their chosen profile name.
        First, it makes sure that there is actually text in the lineedit. If not, the "OK" button
        stays or becomes disabled.
        If text has been entered, it is checked against the list of pre-existing profile names.
        If there is a match, the text will become red and the OK button disabled to indicate
        that only unique profile names will be accepted.

        We don't worry about spaces or invalid characters here because the user is prevented from typing
        those into the box by the Regular Expression validator attached to the lineedit.

        There are a lot of conditional checks in this method because we want to be sure to only
        apply style/button-state when there's an actual change in the valid-state of the text.
        This is important not only to maintain consistency in the interface, but also to minimize
        the flicker that sometimes occurs when changing styles.

        :param text: the text entered into the line edit
        :return:
        """
        if text:
            if text.lower() in self.name_list: # they entered a pre-existing name
                # we only want to update things when switching from valid->invalid p r vv.
                if self.okbutton.isEnabled(): self.okbutton.setEnabled(False)
                if not self.lineEdit.styleSheet():
                    self.lineEdit.setStyleSheet(self.ss_invalid)
                    self.lineEdit.setToolTip(self.tt_invalid)

            else:
                if not self.okbutton.isEnabled():
                    self.okbutton.setEnabled(True)
                if self.lineEdit.styleSheet():
                    self.lineEdit.setStyleSheet("")
                    self.lineEdit.setToolTip(None)

        else:
            if self.okbutton.isEnabled():  self.okbutton.setEnabled(False)
            if self.lineEdit.styleSheet():
                self.lineEdit.setStyleSheet("")
                self.lineEdit.setToolTip(None)

    def accept(self):
        """Qt override"""

        # name input by user
        self.final_name = self.lineEdit.text()

        # profile to copy data from, if selected
        if self.checkBox.isChecked():
            self.copy_from = self.comboBox.currentData()

        # call original accept()
        super(NewProfileDialog, self).accept()

