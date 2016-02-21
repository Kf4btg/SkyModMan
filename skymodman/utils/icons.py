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
    "undo": [("fa.reply", ), {}],
    "redo": [("fa.share",), {}],
    "file": [("fa.file", ), {}],
    "folder": [("fa.folder", ), {}],
    "folder-open": [("fa.folder-open", ), {}],
    "columns": [("fa.columns", ), {}],
    "c_left": [("fa.caret-left", ), {}],
    "c_right": [("fa.caret-right", ), {}],

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
