## Concept and implementation based off of:
## http://stackoverflow.com/questions/23919798/is-there-a-way-to-overlay-multiple-items-on-a-parent-widget-pyside-qt

from PyQt5 import QtWidgets, QtCore


class OverlayCenter(QtWidgets.QLayout):
    """Layout for managing overlays."""

    def __init__(self, parent):
        super().__init__(parent)

        # Properties
        self.setContentsMargins(0, 0, 0, 0)

        self.items = []
    # end Constructor

    def addLayout(self, layout):
        """Add a new layout to overlay on top of the other layouts and widgets."""
        self.addChildLayout(layout)
        self.addItem(layout)
    # end addLayout

    ## I'm not entirely sure this method is necessary...
    ## (and it throws an exception,
    ## so I'm going to comment it out and see what happens)
    # def __del__(self):
    #     """Destructor for garbage collection."""
    #     item = self.takeAt(0)
    #     while item:
    #         item.deleteLater()
    #         item = self.takeAt(0)
    # end Destructor

    def addItem(self, item):
        """Add an item (widget/layout) to the list."""
        self.items.append(item)
    # end addItem

    def count(self):
        """Return the number of items."""
        return len(self.items)
    # end Count

    def itemAt(self, index):
        """Return the item at the given index."""
        try:
            return self.items[index]
        except IndexError:
            return None
    # end itemAt

    def takeAt(self, index):
        """Remove and return the item at the given index."""
        try:
            return self.items.pop(index)
        except IndexError:
            return None
    # end takeAt

    def sizeHint(self):
        return self.parentWidget().size()

    def setGeometry(self, rect):
        """Set the main geometry and the item geometry."""
        super().setGeometry(rect)

        for item in self.items:
            item.setGeometry(rect)
    # end setGeometry
# end class OverlayCenter

align_flags = {
    "left": QtCore.Qt.AlignLeft,
    "right": QtCore.Qt.AlignRight,
    "top": QtCore.Qt.AlignTop,
    "bottom": QtCore.Qt.AlignBottom,
    "vcenter": QtCore.Qt.AlignVCenter,
    "hcenter": QtCore.Qt.AlignHCenter,
}

class Overlay(QtWidgets.QBoxLayout):
    """Overlay widgets on a parent widget."""

    def __init__(self, align="left", align2=None, stylesheet=None, parent=None):
        super().__init__(QtWidgets.QBoxLayout.TopToBottom, parent)

        if align2 is None: # center
            if align in {"left", "right"}:
                align2="vcenter"
            else:
                align2="hcenter"

        if {"top", "bottom"} & {align, align2}:
            setdir=QtWidgets.QBoxLayout.LeftToRight
        else:
            setdir=QtWidgets.QBoxLayout.TopToBottom

        self.setDirection(setdir)
        self.setAlignment(align_flags[align] | align_flags[align2])

        #
        # if location == "left":
        #     self.setDirection(QtWidgets.QBoxLayout.TopToBottom)
        #     self.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        # elif location == "right":
        #     self.setDirection(QtWidgets.QBoxLayout.TopToBottom)
        #     self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # elif location == "top":
        #     self.setDirection(QtWidgets.QBoxLayout.LeftToRight)
        #     self.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        # elif location == "bottom":
        #     self.setDirection(QtWidgets.QBoxLayout.LeftToRight)
        #     self.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter)

        if stylesheet is None:
            self.css = "QWidget {background-color: rgba(0,0,0,0.5); color: white}"
        else:
            self.css = stylesheet
    # end Constructor

    def addWidget(self, widget):
        super().addWidget(widget)

        widget.setStyleSheet(self.css)
    # end addWidget
# end class Overlay

def main():
    app = QtWidgets.QApplication(sys.argv)

    window = QtWidgets.QMainWindow()
    window.show()

    widg = QtWidgets.QTreeView()
    window.setCentralWidget(widg)

    left = Overlay("left", "top")
    lhlbl = QtWidgets.QLabel("Hello")
    lwlbl = QtWidgets.QLabel("World!")
    lhlbl.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
    lwlbl.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
    left.addWidget(lhlbl)
    left.addWidget(lwlbl)

    top = Overlay("top")
    lhlbl = QtWidgets.QLabel("HELLO")
    lwlbl = QtWidgets.QLabel("WORLD!")
    lhlbl.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
    lwlbl.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
    top.addWidget(lhlbl)
    top.addWidget(lwlbl)

    right = Overlay("right")
    lhlbl = QtWidgets.QLabel("hellO")
    lwlbl = QtWidgets.QLabel("worlD!")
    lhlbl.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
    lwlbl.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
    right.addWidget(lhlbl)
    right.addWidget(lwlbl)

    bottom = Overlay("bottom", "right")
    lhlbl = QtWidgets.QLabel("hello")
    lwlbl = QtWidgets.QLabel("world!")
    lhlbl.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
    lwlbl.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
    bottom.addWidget(lhlbl)
    bottom.addWidget(lwlbl)

    center = OverlayCenter(widg)
    center.addLayout(left)
    center.addLayout(top)
    center.addLayout(right)
    center.addLayout(bottom)

    return app.exec_()
# end main

if __name__ == '__main__':
    import sys
    sys.exit(main())