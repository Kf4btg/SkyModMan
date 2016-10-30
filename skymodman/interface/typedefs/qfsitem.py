from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from skymodman.types import FSItem

# actually provides a slight (but noticeable) speedup
Qt_Checked = Qt.Checked
Qt_Unchecked = Qt.Unchecked
Qt_PartiallyChecked = Qt.PartiallyChecked
Qt_ItemIsTristate = Qt.ItemIsTristate

class QFSItem(FSItem):
    """FSITem subclass with Qt-specific functionality"""

    # now here's a hack...
    # this is changed by every child when recursively toggling check
    # state; thus its final value will be the final child accessed.
    last_child_seen = None


    # Since the base class has __slots__, we need to define them here,
    # too, or we'll lose all the benefits.
    __slots__=("_checkstate", "flags", "icon")

    # noinspection PyTypeChecker,PyArgumentList
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._checkstate=Qt_Checked # tracks explicit checks
        self.flags = Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if self.isdir:
            self.flags |= Qt_ItemIsTristate
            self.icon = QIcon.fromTheme("folder")
        else: #file
            self.flags |= Qt.ItemNeverHasChildren
            self.icon = QIcon.fromTheme("text-plain")

    @property
    def itemflags(self):
        """
        Initial flags for all items are Qt.ItemIsUserCheckable and
        Qt.ItemIsEnabled. Non-directories receive the
        Qt.ItemNeverHasChildren flag, and dirs get Qt_ItemIsTristate to
        allow the 'partially-checked' state
        """
        return self.flags

    @itemflags.setter
    def itemflags(self, value):
        self.flags = value

    @property
    def checkState(self):
        ## XXX: This is not a trivial operation (for directories--it is for files), so it likely shouldn't be a property
        # if not self.isdir:
        if self.isdir and self.child_count>0:
            return self.children_checkState()

        return self._checkstate

    # So, I think the protocol here is, when a directory is un/checked,
    # set the checkstates of all that directory's children to match.
    # here's the python translation of the c++ code from qtreewidget.cpp:

    @checkState.setter
    def checkState(self, state):
        self.setCheckState(state)


    def setChecked(self, checked):
        """
        :param bool checked:
        """
        self.setCheckState(Qt_Checked if checked else Qt_Unchecked)


    def setCheckState(self, state):
        # using a class variable, track which items were changed
        QFSItem.last_child_seen = self

        # state propagation for dirs:
        # (only dirs can have the tristate flag turned on)
        if self.flags & Qt_ItemIsTristate:
            # propagate a check-or-uncheck down the line:
            for c in self.iterchildren():

                # this will trigger any child dirs to do the same
                c.checkState = state
                # c.setEnabled(state == Qt_Checked)

        self._checkstate = state

        # the "hidden" attribute on the baseclass is what will allow us
        # to save the lists of hidden files to disk, so be sure to set
        # it here;

        # note:: only explicitly unchecked items will be marked as
        # hidden here; checked and partially-checked directories will
        # not be hidden
        self.hidden = state == Qt_Unchecked

        # add final check for if this was the last unhidden file in a directory:

    def children_checkState(self):
        """
        Calculates the checked state of the item based on the checked
        state of its children.

            * if all children checked => this item is also checked
            * if some children checked => this item is partially checked
            * if no children checked => this item is unchecked.

          Note: both the description above and the algorithm below were
          'borrowed' from the Qt code for QTreeWidgetItem"""
        checkedkids = False
        uncheckedkids = False

        # check child checkstates;
        # break when answer can be determined;
        # shouldn't need to be recursive if check state is properly
        # propagated and set for all descendants
        for c in self.iterchildren():
            s = c.checkState
            # if any child is partially checked, so will this be
            if s == Qt_PartiallyChecked:
                return Qt_PartiallyChecked

            if s == Qt_Unchecked:
                uncheckedkids = True
            else:
                checkedkids = True

            # if we've found both kinds, return partial
            if checkedkids and uncheckedkids:
                return Qt_PartiallyChecked

        return Qt_Unchecked if uncheckedkids else Qt_Checked


    def setEnabled(self, boolean):
        """
        Modify this item's flags to set it enabled or disabled based on
        value of boolean

        :param boolean:
        """
        if boolean:
            self.flags |= Qt.ItemIsEnabled
        else:
            self.flags &= ~Qt.ItemIsEnabled
