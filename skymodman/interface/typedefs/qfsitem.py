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
    last_child_changed = None


    # Since the base class has __slots__, we need to define them here,
    # too, or we'll lose all the benefits.
    __slots__=("_checkstate", "flags", "icon", "_child_state")

    # noinspection PyTypeChecker,PyArgumentList
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._checkstate=Qt_Checked # tracks explicit checks
        self.flags = Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if self.isdir:
            self.flags |= Qt_ItemIsTristate
            self.icon = QIcon.fromTheme("folder")
        else: #file
            self.flags |= Qt.ItemNeverHasChildren
            self.icon = QIcon.fromTheme("text-plain")

        self._child_state=None

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

        # return self._checkstate
        return Qt_Unchecked if self.hidden else Qt_Checked

    # @checkState.setter
    # def checkState(self, state):
    #     self.set_checkstate(state)


    def setChecked(self, checked, recurse = True):
        """
        :param bool checked:
        """
        self.set_checkstate(Qt_Checked if checked
                            else Qt_Unchecked,
                            recurse)

    def set_checkstate(self, state, recurse=True):
        """Set the checkstate of the item to `state`. If `recurse` is
        True and this item is a directory, that state will also be
        applied to all children under this item


        :return: the FSItem highest in the parent-hierarchy above this
            instance (i.e., the directory directly below the root item
            that (at some level) contains this item). If this FSItem
            is itself a top-level file or directory, it will return
            itself.
            This is for tracking which items have had their check-states
            changed or invalidated (as in the case of directories, where
            checkstate is derived from that of its children)"""

        self._set_checkstate(state, recurse)

        # invalidate parent child_state attribute
        if self.parent and self.parent.parent:
            # to avoid returning the root item, we
            # check for self.parent (which should always be valid,
            # since the user can't change the "checked" state of the
            # root item) and self.parent.parent (which may be invalid
            # IFF the parent of this item IS the root item, in which
            # case we have no need to invalidate its child_state and
            # so we return THIS item as the top-most affected ancestor)
            return self.parent._invalidate_child_state()
        return self

    def _set_checkstate(self, state, recurse):
        """For internal use"""
        # this is kept separate to avoid gillions of unnecessary
        # "parent._invalidate_child_state()" calls when recursing

        # using a class variable, track which items were changed
        QFSItem.last_child_changed = self


        if recurse:
            self._set_checkstate_recursive(state)
        # self._checkstate = state

        # the "hidden" attribute on the baseclass is what will allow us
        # to save the lists of hidden files to disk, so be sure to set
        # it here;

        # note:: only explicitly unchecked items will be marked as
        # hidden here; checked and partially-checked directories will
        # not be hidden
        self.hidden = state == Qt_Unchecked

    def _set_checkstate_recursive(self, state):
        # using a class variable, track which items were changed
        # QFSItem.last_child_changed = self


        # state propagation for dirs:
        # (only dirs can have the tristate flag turned on)
        if self.flags & Qt_ItemIsTristate:
            # propagate a check-or-uncheck down the line:
            for c in self.iterchildren():

                # this will trigger any child dirs to do the same
                c.set_checkstate(state, c.isdir)

                # c.setEnabled(state == Qt_Checked)

            # we know that, now, all the children of this item have
            # `state` as their current checkState, so we can update this:
            self._child_state = state

        # self.set_checkstate(state, False)


    # So, I think the protocol here is, when a directory is un/checked,
    # set the checkstates of all that directory's children to match.
    # here's the python translation of the c++ code from qtreewidget.cpp:
    def children_checkState(self):
        """
        Calculates the checked state of the item based on the checked
        state of its children.

            * if all children checked => this item is also checked
            * if some children checked => this item is partially checked
            * if no children checked => this item is unchecked.

          Note: both the description above and the algorithm below were
          'borrowed' from the Qt code for QTreeWidgetItem"""


        # if we have a cached, valid child state, skip the calculation
        # and just return that; otherwise derive the conglomerate
        # state of this item from that of its children
        if self._child_state is None:

            checkedkids = False
            uncheckedkids = False

            # roughly equivalent to:
            #
            # if any(c.checkState == PartialCheck for c in children):
            #   self.checkstate = PartialCheck
            # elif all(c.checkstate == Unchecked for c in children):
            #   self.checkstate = Unchecked
            # elif all(c.checkstate == Checked for c in children):
            #   self.checkstate = Checked
            # else:
            #   self.checkstate = PartialCheck

            # check child checkstates;
            # break when answer can be determined;
            # shouldn't need to be recursive if check state is properly
            # propagated and set for all descendants
            for c in self.iterchildren():
                s = c.checkState
                # if any child is partially checked, so will this be
                if s == Qt_PartiallyChecked:
                    self._child_state = Qt_PartiallyChecked
                    break
                    # return Qt_PartiallyChecked

                if s == Qt_Unchecked:
                    uncheckedkids = True
                else:
                    checkedkids = True

                # if we've found both kinds, return partial
                if checkedkids and uncheckedkids:
                    self._child_state = Qt_PartiallyChecked
                    break
                    # return Qt_PartiallyChecked
            else:
                # we didn't break, so one of the values must still be False
                self._child_state = Qt_Unchecked if uncheckedkids else Qt_Checked

        return self._child_state
            # return Qt_Unchecked if uncheckedkids else Qt_Checked

    def _invalidate_child_state(self):
        """Indicate that the cached _child_state attribute should
        be considered invalid and be recalculated on next call"""
        self._child_state = None

        # necessarily, this requires that the parent of this item
        # have its child_state rendered invalid as well
        p = self.parent
        if p and p.parent:
            # check for the parent's parent because the root item
            # is inaccessible to the user and thus will never
            # have its child_state queried
            return p._invalidate_child_state()
        return self

    def setEnabled(self, enabled):
        """
        Modify this item's flags to set it enabled or disabled based on
        value of boolean

        :param bool enabled:
        """
        if enabled:
            self.flags |= Qt.ItemIsEnabled
        else:
            self.flags &= ~Qt.ItemIsEnabled
