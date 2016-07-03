from PyQt5.QtCore import QRegularExpression
from PyQt5.QtGui import QRegularExpressionValidator
from PyQt5.QtWidgets import (QDialog,
                             QDialogButtonBox)

from skymodman.interface.designer.uic.new_profile_dialog_ui import Ui_NewProfileDialog
from skymodman.utils import withlogger


@withlogger
class NewProfileDialog(QDialog,  Ui_NewProfileDialog):
    """
    Dialog window allowing the user to create a new profile. They
    have the option of using default starting values or copying
    the settings from an existing profile.

    New profile names must be unique, ignoring case.
    """


    def __init__(self, *, combobox_model, **kwargs):
        super(NewProfileDialog, self).__init__(**kwargs)

        self.setupUi(self)

        self.okbutton = self.buttonBox.button(QDialogButtonBox.Ok)
        self.okbutton.setDisabled(True)

        self.final_name = None
        self.copy_from = None

        self.comboBox.setModel(combobox_model)

        # according to timeit, checking if a word is in a list is
        # faster than checking against a RegExp--even a compiled RE,
        # and even if you pre-process the word to check each time
        # (e.g.: word.lower() in wordlist)
        self.name_list = [p.name.lower() for p in combobox_model.profiles]

        # this validator ensures that no spaces or invalid characters can be entered.
        # (only letters, numbers, underscores, hyphens, and periods)
        vre_str = r"[\w\d_.-]+"
        self.vre = QRegularExpression(vre_str)
        self.validator = QRegularExpressionValidator(self.vre)

        self.lineEdit.setValidator(self.validator)

        # stylesheet for invalid text
        self.ss_invalid = "QLineEdit { color: red }"

        # tooltip for invalid text
        self.tt_invalid = "Profile names must be unique"


    def on_lineEdit_textChanged(self, text):
        """
        This slot handles giving feedback to the user about the
        validity of their chosen profile name. First, it makes sure
        that there is actually text in the lineedit. If not, the "OK"
        button stays or becomes disabled.
        If text has been entered, it is checked against the list of
        pre-existing profile names. If there is a match, the text will
        become red and the OK button disabled to indicate that only
        unique profile names will be accepted.

        We don't worry about spaces or invalid characters here because
        the user is prevented from typing those into the box by the
        Regular Expression validator attached to the lineedit.

        There are a lot of conditional checks in this method because
        we want to be sure to only apply style/button-state when
        there's an actual change in the valid-state of the text. This
        is important not only to maintain consistency in the interface,
        but also to minimize the flicker that sometimes occurs when
        changing styles.

        :param str text: the text entered into the line edit
        :return:
        """
        if text:
            if text.lower() in self.name_list: # they entered a pre-existing name
                # we only want to update things when switching from valid->invalid or v-v.
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
        super().accept()