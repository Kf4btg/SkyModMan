from PyQt5.QtWidgets import QMessageBox, QSpacerItem, QSizePolicy, QCheckBox
from contextlib import suppress

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


def _mdialog(icon, title, text, info_text, buttons, default_button, parent, min_width):
    """
    Internal function. Construct the message dialog
    :return: the dialog box
    """

    # defaults
    micon = QMessageBox.NoIcon
    dbutton = QMessageBox.NoButton
    mbuttons = QMessageBox.NoButton

    with suppress(KeyError):
        micon = _icons[icon]

    if isinstance(buttons, str):
        # handle just one value passed for 'buttons'
        with suppress(KeyError):
            mbuttons = _buttons[buttons]
    elif buttons is not None:
        for b in buttons:
            with suppress(KeyError):
                mbuttons |= _buttons[b]

    with suppress(KeyError):
        dbutton = _buttons[default_button]

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
    hspacer = QSpacerItem(min_width, 0, QSizePolicy.Minimum,
                          QSizePolicy.Expanding)
    ml = mbox.layout()
    ml.addItem(hspacer, ml.rowCount(), 0, 1, ml.columnCount())

    return mbox

def message(icon='question', title='', text="What's that you say?", info_text=None, buttons=('yes', 'no'), default_button = 'none', parent=None, min_width=500):
    """
    Helper for constructing and gettting replies from QMessageBoxes.
    Most arguments take strings (buttons an iterable of strings). Rather
    than return the response code from the QMessageBox, this method
    filters almost all the codes down to either 'positive' or 'negative'
    response and return True or False accordingly. If, somehow, the
    response does not fall in one of these categories, then the code
    will be returned instead.

    :param parent: QWidget parent
    :param str icon: one of 'question', 'warning', 'info', 'information',
        'critical', 'none', or 'noicon' (these last 2 are the same)
    :param str title:
    :param str text:
    :param str info_text:
    :param buttons: a str or tuple of strs, which can be any of: 'ok',
        'open', 'save', 'cancel', 'close', 'discard', 'apply', 'reset',
        'restore', 'help', 'yes', 'no', 'abort', 'retry', 'ignore',
        'none', or 'nobutton'.  The default is ``('yes', 'no')``

    :param str default_button: by default, there is no default button.
        Specify one of the buttons passed for `buttons` to make it the
        default.
    :param int min_width: minimum width of the created dialog box

    :return: True or False
    """

    mbox = _mdialog(icon, title, text, info_text, buttons, default_button, parent, min_width)

    response =  mbox.exec_()

    if response in _yes_response:
        return True
    if response in _no_response:
        return False
    return response

def checkbox_message(icon='question', title='', text="What's that you say?", info_text=None, buttons=('yes', 'no'), default_button = 'none', parent=None, min_width=500, checkbox_text="", checkbox_checked=False):
    """
    Identical to message() except that this function adds a checkbox
     to the dialog box with a customizable message. Also, the return
     value is now tuple of bools: [0] is the return value based on
     the button the user clicked, and [1] is the check-state of the
     checkbox.

    :param parent: QWidget parent
    :param str icon: one of 'question', 'warning', 'info', 'information',
        'critical', 'none', or 'noicon' (these last 2 are the same)
    :param str title:
    :param str text:
    :param str info_text:
    :param buttons: a str or tuple of strs, which can be any of: 'ok',
        'open', 'save', 'cancel', 'close', 'discard', 'apply', 'reset',
        'restore', 'help', 'yes', 'no', 'abort', 'retry', 'ignore',
        'none', or 'nobutton'.  The default is ``('yes', 'no')``

    :param str default_button: by default, there is no default button.
        Specify one of the buttons passed for `buttons` to make it the
        default.
    :param int min_width: minimum width of the created dialog box

    :param checkbox_text: Text to show beside the checkbox
    :param checkbox_checked: whether the checkbox should be checked by default
    :return: tuple(bool, bool): (User response, checkbox state)
    """

    mbox = _mdialog(icon, title, text, info_text, buttons, default_button, parent, min_width)

    cbox=QCheckBox()
    if checkbox_text:
        cbox.setText(checkbox_text)
    cbox.setChecked(checkbox_checked)

    # horiz=shrink(maximum),
    # vert=grow(minimum)
    # without setting this (specifically the horizontal size policy),
    # the checkbox would block the dialog buttons, even though the
    # the widget itself didn't appear to be anywhere near them.
    cbox.setSizePolicy(4, 1)

    ml = mbox.layout()
    ml.addWidget(cbox, ml.rowCount() - 2, 0, 1, -1)

    response = mbox.exec_()

    if response in _yes_response:
        ret = True
    if response in _no_response:
        ret = False
    else:
        ret = response

    return ret, cbox.isChecked()

