from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtDesigner import QPyDesignerCustomWidgetPlugin

from skymodman.qt_interface.plugins.widgets.escapeablelineedit import EscapeableLineEdit

class EscapeableLineEditPlugin(QPyDesignerCustomWidgetPlugin):

    # Initialise the instance.
    def __init__(self, parent=None):
        super().__init__(parent)

        self._initialized = False

    # Initialise the custom widget for use with the specified formEditor
    # interface.
    def initialize(self, formEditor):
        if self._initialized:
            return

        self._initialized = True

    # Return True if the custom widget has been intialised.
    def isInitialized(self):
        return self._initialized

    # Return a new instance of the custom widget with the given parent.
    def createWidget(self, parent):
        return EscapeableLineEdit(parent)

    # Return the name of the class that implements the custom widget.
    def name(self):
        return "EscapeableLineEdit"

    # Return the name of the group to which the custom widget belongs.  A new
    # group will be created if it doesn't already exist.
    def group(self):
        return "SMM_Custom"

    # Return the icon used to represent the custom widget in Designer's widget
    # box.
    def icon(self):
        return QIcon(_logo_pixmap)

    # Return a short description of the custom widget used by Designer in a
    # tool tip.
    def toolTip(self):
        return "QLineEdit that emits a signal on Escape"

    # Return a full description of the custom widget used by Designer in
    # "What's This?" help for the widget.
    def whatsThis(self):
        return "A simple extension to the standard QLineEdit that catches a press of the Escape key and emits a signal."

    # Return True if the custom widget acts as a container for other widgets.
    def isContainer(self):
        return False

    # Return an XML fragment that allows the default values of the custom
    # widget's properties to be overridden.
    def domXml(self):
        return '<widget class="EscapeableLineEdit" name="escapeablelineedit">\n' \
               ' <property name="toolTip" >\n' \
               '  <string></string>\n' \
               ' </property>\n' \
               ' <property name="whatsThis" >\n' \
               '  <string></string>\n' \
               ' </property>\n' \
               '</widget>\n'

    # Return the name of the module containing the class that implements the
    # custom widget.  It may include a module path.
    def includeFile(self):
        return "skymodman.qt_interface.plugins.widgets.escapeablelineedit"


# Define the image used for the icon.
_logo_16x16_xpm = [
"16 16 4 1",
"0 c #000000",
"1 c #464646",
". c #fefefe",
"  c none",
"   0000000000   ",
"  011111111110  ",
"  0....11....0  ",
"  0....00....0  ",
"  0...0000...0  ",
"  01000..00010  ",
"  01000..00010  ",
"  0...0000...0  ",
"  0....00....0  ",
"  01...00...10  ",
"   01..00..10   ",
"    01.11.10    ",
"     01..10     ",
"      0110      ",
"       00       ",
"                "]

_logo_pixmap = QPixmap(_logo_16x16_xpm)