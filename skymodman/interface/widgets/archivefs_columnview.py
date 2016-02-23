from functools import partial

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, Qt, pyqtProperty
from PyQt5.QtGui import QResizeEvent
from PyQt5.QtWidgets import QScrollBar, QStyle, QProxyStyle

from skymodman.utils import withlogger, icons


class ResizingListView(QtWidgets.QListView):

    _columnWidthsChanged = pyqtSignal()

    def __init__(self, columnview, *args, **kwargs):
        super().__init__(columnview, *args, **kwargs)

        self._owner = columnview
        self.column = -1
        self._width = 120
        self.connection_made=False
        self.setMinimumWidth(120)
        # self.setDefaultDropAction(Qt.MoveAction)
        # self.setAcceptDrops(True)
        # self.setDragEnabled(True)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(
            self._on_context_menu)
        # self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # self.setVerticalScrollBar(QScrollBar())
        # self.verticalScrollBar().setVisible(False)

        # self.setObjectName("resizinglistview")

        self._defer_resize()


    def setRootIndex(self, index):
        super().setRootIndex(index)
        self._defer_resize()

    def _defer_resize(self):
        ## There were a few places where I might have been able to hack in a call
        # to "setColumnWidths" or resizeToContents--making it happen as a side-effect of
        # some incidental function--but since hacks are, tautalogically, hacky, I think
        # it's probably best to avoid them. And side-effects are widely accepted
        # to be a Generally Bad Idea. The problem is that the only time the columnview
        # communicates with the child list views (without a direct user action) is while
        # they're being created...which is also the only time where we CAN't call
        # setColumnWidths()...Thus the chicken and egg problem. So this is a work-around
        # (slightly different from a hack...) to offload the signal call to a
        # thread which will then call the proper resize method the next time the event
        # loop comes around--a slice of time that will hopefully be unnoticeable.
        if self.sizeHintForColumn(0) > 0:
            # if it doesn't have anything to hint about, forget it.

            if not self.connection_made:
                # don't keep reconnecting
                self._columnWidthsChanged.connect(self._do_deferred_resize,
                                                  Qt.QueuedConnection)
                self.connection_made = True

            # emit for execution on next event-loop
            self._columnWidthsChanged.emit()

    def _on_context_menu(self, point):
        self._owner.show_context_menu(self, self.indexAt(point), self.mapToGlobal(point))

    def _do_deferred_resize(self):
        """handler for _defer_resize event"""
        self.resizeToContents()

    def resizeToContents(self):
        column = 0
        index = self.rootIndex()

        # find out how deep we've gotten into the view
        # while index.isValid():
        visible_root = self._owner.rootIndex()
        while index != visible_root:
            column+=1
            index = index.parent()
        self.column = column

        width = self.sizeHintForColumn(0)
        if width<=0: # Qt is confused, nevermind
            return

        # icon padding
        width+=40

        self._width = width
        # notify columnview

        # if this is the column for the root of the fs, make
        # sure to hide the trash folder
        if self.rootIndex().internalId()==0 and self.model():
            self.setRowHidden(self.model().row4strpath("/.trash"), True)


        # using a direct call rather than emitting a signal so that, as
        # the views get deleted by the user navigating, there
        # aren't tons of dangling  connections sticking around
        # (apparently signals are no longer disconnected at deletion?
        # I'm not really sure, but either way, this reduces overhead
        # compared to having a lot of connected signals...even if it is
        # cheating a bit)
        self._owner.updateWidths(column, width)


@withlogger
class ResizingColumnView(QtWidgets.QColumnView):

    # todo: while dragging, if one hovers over the 2px border btwn columns, this apparently counts as targeting the root (invalid) index; dropping the item in this case will move it to the root folder. Not a big issue, but not exactly expected behaviour, either.

    # fixme: another problem with dragging: moving a folder into another folder in the same parent folder as the original folder (uhhh....you know what i mean?) doesn't update the 'child' columns correctly; until a click or two is made on different items, one will still see the contents of the moved folder as if that folder were still selected in the current column.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._owner = None
        self._model = None
        """:type: skymodman.interface.models.archivefs_treemodel.ModArchiveTreeModel"""

        self.views = {} # just a place to for them to hide from the GC
        self._widths = [120]*10
        # self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.setStyle(ColumnStyle(self.style()))

        # set a style to show a divider between two columns
        # (we hide the vertical scroll bar due to being way fugly).
        # for some reason, just setting border-right didn't do anything;
        # but setting a whole border and turning the others off does work, so...
        self.setStyleSheet(
            """QColumnView QAbstractItemView {
                border: 2px solid palette(dark);
                border-left: none;
                border-top: none;
                border-bottom: none;
            }
            """)

        self._hiddeninode = -1
        self._icon = icons.get("c_right")

    @pyqtProperty(str)
    def arrowicon(self):
        return self._icon

    @arrowicon.setter
    def arrowicon(self, value):
        self._icon = icons.get(value)


    def isIndexHidden(self, index):
        return index.internalId() == self._hiddeninode

    def setRootIndex(self, index):
        self.views.clear()
        self._widths=[120]*10
        super().setRootIndex(index)

    @property
    def owner(self):
        return self._owner

    @owner.setter
    def owner(self, value):
        self._owner = value

    def setModel(self, model):
        super().setModel(model)
        self._model = model
        self._hiddeninode = self._model.trash.inode

    def reflow(self):
        """Force column view to update"""
        s = self.size()
        self.resizeEvent(QResizeEvent(s, s))

    def updateWidths(self, change_col, width):
        """
        Resize the columns to their reported widths.
        :param change_col: Column reporting a new width
        :param width: the new width
        """
        try:
            if self._widths[change_col] == width:
                return
            self._widths[change_col] = width
        except IndexError:
            while len(self._widths) < change_col:
                self._widths.append(self._widths[-1])
            self._widths.append(width)

        self.setColumnWidths(self._widths)
        self.reflow()

    def createColumn(self, index):
        """
        Override to replace the regular QListView columns with ResizingListView

        :param QModelIndex index: the root index (diretory) whose contents will be shown in this column
        """
        # for c in self.children():
        #     try:
        #         self._printinfo(c)
        #         # printattrs(c)
        #     except Exception as e:
        #         print(e)

        view = ResizingListView(self)
        view.setModel(self._model)
        view.setRootIndex(index)
        self.initializeColumn(view)

        # We must hold a reference to this somewhere so that it isn't
        # garbage collected on us.
        self.views[view.column] = view

        return view

    def initializeColumn(self, column):
        super().initializeColumn(column)

        # just need to make a few tweaks to the default setup
        column.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        column.setMinimumWidth(120)

    def show_context_menu(self, view, index, global_pos):
        # just send the event on up
        self.owner.show_context_menu(view, index, global_pos)

    def scrollTo(self, current, *args):
        """
        This prevents the column view from showing the preview column when
        a non-directory item is activated

        :param QModelIndex current:
        """
        # disable preview widget
        if not self._model._isdir(current.internalId()):
            pwid = self.previewWidget()

            # we'll need something
            if not pwid:
                pwid = QtWidgets.QWidget()
                self.setPreviewWidget(pwid)

            # The protected preview column owns the preview widget.
            column = pwid.parent().parent()
            # hide
            column.setFixedWidth(0)

        super().scrollTo(current, *args)

    # def _printinfo(self, c, depth=0, i="  "):
    #     print()
    #     try:
    #         print(i*depth, 1, type(c))
    #         print(i*depth, 2, str(c))
    #         print(i*depth, 3, c.objectName())
    #         # print(4, c.accessibleName())
    #         # print(5, c.accessibleDescription())
    #         print(i*depth, 6, c.x(), c.y())
    #         # print(7, c.winId())
    #         # print(i*depth, 8, c.size())
    #         print(i*depth, 8, "w", c.width(), ", h", c.height())
    #         print(i*depth, 9, "min:", c.minimumSize())
    #         print(i*depth, "a", c.geometry())
    #         # print(i*depth, "b", c.dynamicPropertyNames())
    #         # print(i*depth, "c", c.backgroundRole(), c.foregroundRole())
    #         print(i*depth, "d   ", c.children())
    #     except Exception as e:
    #         print(i*depth, e)
    #
    #     if c.children():
    #         for cc in c.children():
    #             print(i*depth, "---------sub-child:------")
    #             self._printinfo(cc, depth+1)

class ColumnStyle(QProxyStyle):
    """
    Replaces the horrible right-arrow indicator in the column view with something a little nicer.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.r_arrow = icons.get("c_right", scale_factor=0.5)
        self.ENABLED = type(self.r_arrow).Normal
        self.DISABLED = type(self.r_arrow).Disabled
        self.ON = type(self.r_arrow).On

    def drawPrimitive(self, element, option, painter, widget=None):

        if element == QStyle.PE_IndicatorColumnViewArrow:
            selected = bool(option.state & self.State_Selected)

            self.r_arrow.paint(painter, option.rect,
                               mode=(self.DISABLED, self.ENABLED)[selected],
                               state = self.ON)
        else:
            super().drawPrimitive(element, option, painter, widget)

