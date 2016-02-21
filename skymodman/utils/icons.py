from skymodman.thirdparty import qtawesome as qta
from PyQt5 import QtGui
# valid_options = ['active', 'animation', 'color', 'color_active',
# 'color_disabled', 'color_selected', 'disabled', 'offset',
# 'scale_factor', 'selected']


# define options
_icon_defs = {
    # key:  (names of icons from which to build the icon), {options}
    "edit": [("fa.edit", ), {}],
    "save": [("fa.save", ), {}],
    # "undo": [("fa.undo", ), {}],
    "undo": [("fa.reply", ), {}],
    # "redo": [("fa.repeat",), {}],
    "redo": [("fa.share",), {}],

    "open": [("fa.open",), {}],
    "close": [("fa.close",), {}],


    "file": [("fa.file", ), {}],
    "folder": [("fa.folder", ), {}],
    "folder-open": [("fa.folder-open", ), {}],

    "view-column": [("fa.columns", ), {}],
    "view-tree": [("fa.tree", ), {}],
    # "view-tree": [("fa.site-map", ), {}],

    "c_left": [("fa.caret-left", ), {}],
    "c_right": [("fa.caret-right", ), {}],

    "move-up": [("fa.angle-up", ), {}],
    "move-down": [("fa.angle-down", ), {}],
    "move-top": [("fa.angle-double-up", ), {}],
    "move-bottom": [("fa.angle-double-down", ), {}],

    "add": [("fa.plus", ), {}],
    "remove": [("fa.minus", ), {}],

    "find": [("fa.search", ), {}],
    "show": [("fa.eye", ), {}],
    "hide": [("fa.eye-slash", ), {}],

    "check": [("fa.check", ), {}],
    "warning": [("fa.warning", ), {}],
    "flag": [("fa.flag", ), {}],

    "profiles": [("fa.users", ), {}],
    "profile-add": [("fa.user-plus", ), {}],
    "profile-remove": [("fa.user-times", ), {}],

    "file-text": [("fa.file-text-o", ), {}],
    "file-image": [("fa.file-image-o", ), {}],
    "file-script": [("fa.file-code-o", ), {}],
    "file-sound": [("fa.file-audio-o", ), {}],

    "archive": [("fa.archive", ), {}],
    "archive-o": [("fa.file-archive-o", ), {}],

    "spinner": [("fa.spinner",), {}],

    "unchecked": [("fa.square-o",), {}],
    "checked": [("fa.check-square-o",), {}],
    "filled": [("fa.square",), {}],

    "radio": [("fa.circle-o",), {}],
    "radio-checked": [("fa.circle",), {}],

    "steam": [("fa.steam",), {}],
}

_default_opts = {"color": QtGui.QPalette().color(QtGui.QPalette.WindowText)}

def get(icon, **kwargs):
    try:
        args, kws = _icon_defs[icon]

        _kwargs = {}
        #order matters here
        _kwargs.update(_default_opts)
        _kwargs.update(kws)
        _kwargs.update(kwargs)
        return qta.icon(*args, **_kwargs)
    except KeyError:
        return QtGui.QIcon()
