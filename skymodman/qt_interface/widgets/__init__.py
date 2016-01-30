from . import custom_widgets
from .new_profile_dialog import NewProfileDialog
from PyQt5.QtWidgets import QMessageBox, QSpacerItem, QSizePolicy

_icons = {
    'question': QMessageBox.Question,
    'warning': QMessageBox.Warning,
    'info': QMessageBox.Information,
    'information': QMessageBox.Information,
    'critical': QMessageBox.Critical,

    'none': QMessageBox.NoIcon,
    'noicon': QMessageBox.NoIcon
}

_buttons = {
    'ok'      : QMessageBox.Ok,
    'open'    : QMessageBox.Open,
    'save'    : QMessageBox.Save,
    'cancel'  : QMessageBox.Cancel,
    'close'   : QMessageBox.Close,
    'discard' : QMessageBox.Discard,
    'apply'   : QMessageBox.Apply,
    'reset'   : QMessageBox.Reset,
    'restore' : QMessageBox.RestoreDefaults,
    'help'    : QMessageBox.Help,
    'yes'     : QMessageBox.Yes,
    'no'      : QMessageBox.No,
    'abort'   : QMessageBox.Abort,
    'retry'   : QMessageBox.Retry,
    'ignore'  : QMessageBox.Ignore,

    'none'    : QMessageBox.NoButton,
    'nobutton': QMessageBox.NoButton,
}

_yes_response = [QMessageBox.Ok, QMessageBox.Open, QMessageBox.Save, QMessageBox.Apply, QMessageBox.Yes, QMessageBox.RestoreDefaults, QMessageBox.Retry]

_no_response = [QMessageBox.No, QMessageBox.Cancel, QMessageBox.Close, QMessageBox.Abort, QMessageBox.Discard, QMessageBox.Reset]

def message(icon='question', title='', text='Are you sure?', info_text=None, buttons=('yes', 'no'), default_button = 'none', parent=None, min_width:int=500):
    """
    Helper for constructing and gettting replies from QMessageBoxes. Most arguments take strings (buttons an iterable of strings). Rather than return the response code from the QMessageBox, this method filters almost all the codes down to either 'positive' or 'negative' response and return True or False accordingly. If, somehow, the response does not fall in one of these categories, then the code will be returned instead.
    :param parent: QWidget parent
    :param min_width: minimum width of the created box
    :param icon:
    :param title:
    :param text:
    :param info_text:
    :param buttons:
    :param default_button:
    :return:
    """
    try:
        micon = _icons[icon]
    except KeyError:
        micon = QMessageBox.NoIcon

    mbuttons = QMessageBox.NoButton
    for b in buttons:
        try:
            mbuttons = mbuttons | _buttons[b]
        except KeyError:
            pass

    try:
        dbutton = _buttons[default_button]
    except KeyError:
        dbutton = QMessageBox.NoButton

    if not mbuttons: mbuttons = QMessageBox.OK

    mbox = QMessageBox(micon, title, text, mbuttons, parent)
    mbox.setDefaultButton(dbutton)

    if info_text:
        mbox.setInformativeText(info_text)

    # could not figure out how to get the box to be a reasonable size...
    # it seemed to ignore all size hints and resize commands...
    # then i found this hack about adding a spacer to its layout:
    # http://www.qtcentre.org/threads/22298-QMessageBox-Controlling-the-width?p=113348#post113348
    # well, at least it seems to work.
    hspacer = QSpacerItem(min_width, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
    ml = mbox.layout()
    ml.addItem(hspacer, ml.rowCount(), 0, 1, ml.columnCount())

    response =  mbox.exec_()

    if response in _yes_response:
        return True
    if response in _no_response:
        return False
    return response

