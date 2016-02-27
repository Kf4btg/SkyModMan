import re

from PyQt5.QtCore import QRegularExpression, Qt
from PyQt5.QtGui import QRegularExpressionValidator
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

from skymodman.interface.designer.uic.file_exists_dialog_ui import Ui_FileExistsDialog
from skymodman.constants import OverwriteMode
from skymodman.utils.archivefs import PureCIPath


class FileExistsDialog(QDialog, Ui_FileExistsDialog):

    def __init__(self, target_path, src_is_dir=False, same_file=False, in_merge_op=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.overwrite = OverwriteMode.PROMPT
        self.apply_to_all = False

        # self.allow_overwrite = True
        self.path = self.new_dest = PureCIPath(target_path)
        self._oname = self.new_name = self.path.name

        self.merging = in_merge_op

        ## just thinking about the possible permutations...
        # dir2dir = src_is_dir and target_path.is_dir
        # file2dir = target_path.is_dir and not src_is_dir
        # tofile = not target_path.is_dir
        #
        # self.btn_overwrite.setVisible(not same_file and not file2dir)
        # self.btn_merge.setVisible(not same_file and dir2dir)

        self.btn_skip.setVisible(self.merging)
        self.cbox_sticky.setVisible(self.merging)
        self.btn_overwrite.setVisible(False)
        self.btn_merge.setVisible(False)

        ## Set title, tweak button setup based on arguments ##
        if same_file:
            self.setWindowTitle("File exists.")
            # self.allow_overwrite = False
            # self.btn_overwrite.setVisible(False)
            # self.btn_merge.setVisible(False)

            self.label.setText("This operation would overwrite '{path}' with itself; please enter a new name:".format(path=self.path))

        elif target_path.is_dir:
            if src_is_dir:
                self.setWindowTitle("Destination directory exists.")

                # offer merge
                self.btn_overwrite.setVisible(True)
                self.btn_merge.setVisible(True)

                self.label.setText("This operation will overwrite '{path}'. How would you like to proceed?".format(path=self.path))
            else:
                self.setWindowTitle("Destination exists as directory.")

                # self.btn_overwrite.setVisible(False)
                # self.btn_merge.setVisible(False)

                self.label.setText("A directory with the name '{name}' already exists. Please enter a new name:".format(name=self.path.name))
        else:
            # target is a file, src is whatever
            self.setWindowTitle("File exists.")

            self.btn_overwrite.setVisible(True)
            # self.btn_merge.setVisible(False)

            self.label.setText(
                "This operation will overwrite '{path}'. How would you like to proceed?".format(path=self.path))
            # self.label.setText(self.label.text().format(path=self.path))


        ## Change 'OK' text ##
        self.okbutton = self.btnbox.button(QDialogButtonBox.Ok) # type: QPushButton
        self.okbutton.setText("Rename")
        self.okbutton.setEnabled(False)

        ## Setup Button actions ##
        self.btn_new_name.clicked.connect(self.on_suggest_new_name)
        self.btn_overwrite.clicked.connect(self.on_overwrite_clicked)
        self.btn_merge.clicked.connect(self.on_merge_clicked)
        self.btn_skip.clicked.connect(self.on_skip_clicked)

        # status msg for cbox
        if self.btn_overwrite.isVisible():
            self.cbox_sticky.stateChanged.connect(self.on_cbox_changed)

        ## Set Default text for name field ##
        self.name_edit.setText(self._oname)
        self.name_edit.textChanged.connect(self.on_name_changed)

        ## list of current filenames in the destination ##
        self._dirnames = target_path.sparent.ls(conv=str.lower)

        # any char other than / or : or NUL (not sure how to specify that one...)
        # ; also exclude \
        vre_str = r"[^/:\\]+"
        self.vre = QRegularExpression(vre_str)
        self.validator = QRegularExpressionValidator(self.vre)
        self.name_edit.setValidator(self.validator)

        # Also can't start with - or be . or ..
        # This one doesn't prevent entry, but disables the buttons
        # if the entered string matches
        self.reinvalid = re.compile(r"^(-.*|\.\.?$)")


    def on_name_changed(self, text):
        text = text.strip().lower()

        valid = text and not self.reinvalid.match(text)

        if valid:
            exists = text in self._dirnames
            self.okbutton.setEnabled(not exists)
            self.btn_overwrite.setEnabled(exists)

            # todo: enable/disable this button based on whether the new target is a directory or not.
            if self.btn_merge.isVisible():
                self.btn_merge.setEnabled(exists and text == self._oname)
        else:
            self.okbutton.setEnabled(False)
            self.btn_overwrite.setEnabled(False)

    def on_overwrite_clicked(self):
        self.overwrite=OverwriteMode.REPLACE
        self.accept()

    def on_merge_clicked(self):
        self.overwrite = OverwriteMode.MERGE
        self.accept()

    def on_skip_clicked(self):
        self.overwrite = OverwriteMode.IGNORE
        self.accept()

    def on_cbox_changed(self, state):
        # only called when ovewrite button is visible
        if state & Qt.Checked:
            self.lbl_status.setText("")

    def on_suggest_new_name(self):
        suffix = 1

        getname = (self._oname+" {}").format
        newname = getname(suffix)
        while newname.lower() in self._dirnames:
            suffix+=1
            newname = getname(suffix)

        self.name_edit.setText(newname)

    def accept(self):
        """Qt override"""

        if self.merging and self.cbox_sticky.isChecked():
            # if skip or overwrite buttons were clicked after checking
            # the 'apply to all' box, combine the ow mode with MERGE
            # to make the option persistent and prevent any more of
            # these dialogs from showing up.
            self.apply_to_all = True
            # self.overwrite = self.overwrite | OverwriteMode.MERGE


        # name input by user
        _newname = self.name_edit.text()
        if self._oname != _newname:
            self.new_dest = self.path.with_name(_newname)

        # self.new_name = self.name_edit.text()
        
        super().accept()


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    from skymodman.utils.archivefs import ArchiveFS
    from PyQt5.QtWidgets import QPushButton

    import sys

    app = QApplication(sys.argv)

    fs = ArchiveFS()
    fs.touch("/test/best/rest")
    fs.touch("/test/jest")

    # d = FileExistsDialog(fs.CIPath("/test/best/rest"))
    # d = FileExistsDialog(fs.CIPath("/test/best/rest"), True)
    # d = FileExistsDialog(fs.CIPath("/test/best"), True)
    # d = FileExistsDialog(fs.CIPath("/test/best"))
    d = FileExistsDialog(fs.CIPath("/test/jest"))
    # d = FileExistsDialog(fs.CIPath("/test/best"), False, True)
    # d = FileExistsDialog(fs.CIPath("/test/best"), True, True)
    # d = FileExistsDialog(fs.CIPath("/test/best/rest"), False, True)
    # d = FileExistsDialog(fs.CIPath("/test/best/rest"), True, True)

    d.show()

    app.exec_()

    print(d.result())
    print(d.new_name)
    print(d.overwrite)