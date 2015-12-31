from dialog import Dialog
import textwrap
from . import IModInstaller

class DialogInstaller(IModInstaller):
    tw = textwrap.TextWrapper(width=80, tabsize=2, break_long_words=False)

    def __init__(self, modname, **dialog_opts):
        IModInstaller.__init__(self, modname)

        self.d = Dialog(**dialog_opts)
        self.button_names = {self.d.OK: "Next",
                             self.d.CANCEL: "Cancel",
                             self.d.HELP: "Help",
                             self.d.EXTRA: "Extra"}

        self.d.set_background_title(modname)
