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

    def force_set_checkstate(self, state):
        """
        Simply set the checkstate of this item to `state`, no
        questions asked--although Qt.PartiallyChecked is invalid for
        files and will be changed to Qt.Checked.

        No recursion occurs within this method.
        """

        if self.isdir:
            # for directories, we use a cached value for the checkstate,
            # so directly set that instead of letting it be derived
            self._child_state = state

        # and for files, the checkstate is taken from the 'hidden'
        # status; we need to set that for directories as well, so this
        # part can be universal

        # NOT hidden if state is Checked or PartiallyChecked
        self.hidden = state == Qt_Unchecked

    def setChecked(self, checked, recurse = True):
        """
        :param bool checked:
        """
        return self.set_checkstate(Qt_Checked if checked
                            else Qt_Unchecked,
                            recurse)

    def set_checkstate(self, state, recurse=True):
        """Set the checkstate of the item to `state`. If `recurse` is
        True and this item is a directory, that state will also be
        applied to all children under this item

        :return: the last QFSItem that was affected by this operation
            (which would be this item if this item is a file, otherwise
            the final item in this directory or the deepest sub-dir)

        # """

        self._set_checkstate(state, recurse)
        return QFSItem.last_child_changed

        # invalidate parent child_state attribute
        # if self.parent and self.parent.parent:
            # to avoid returning the root item, we
            # check for self.parent (which should always be valid,
            # since the user can't change the "checked" state of the
            # root item) and self.parent.parent (which may be invalid
            # IFF the parent of this item IS the root item, in which
            # case we have no need to invalidate its child_state and
            # so we return THIS item as the top-most affected ancestor)
            # return self.parent._invalidate_child_state()
            # self.parent._invalidate_child_state()
        # return self

    def _set_checkstate(self, state, recurse):
        """For internal use"""

        # using a class variable, track which items were changed
        QFSItem.last_child_changed = self


        if recurse:
            self._set_checkstate_recursive(state)

        # the "hidden" attribute on the baseclass is what will allow us
        # to save the lists of hidden files to disk, so be sure to set
        # it here;

        # note:: only explicitly unchecked items will be marked as
        # hidden here; checked and partially-checked directories will
        # not be hidden
        self.hidden = state == Qt_Unchecked

    def _set_checkstate_recursive(self, state):
        # state propagation for dirs:
        # (only dirs can have the tristate flag turned on)
        if self.flags & Qt_ItemIsTristate:
            # propagate a check-or-uncheck down the line:
            for c in self.iterchildren():

                # this will trigger any child dirs to do the same
                c._set_checkstate(state, c.isdir)

            # we know that, now, all the children of this item have
            # `state` as their current checkState, so we can update this:
            self._child_state = state


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

                if s == Qt_Unchecked:
                    uncheckedkids = True
                else:
                    checkedkids = True

                # if we've found both kinds, return partial
                if checkedkids and uncheckedkids:
                    self._child_state = Qt_PartiallyChecked
                    break
            else:
                # we didn't break, so one of the values must still be False
                self._child_state = Qt_Unchecked if uncheckedkids else Qt_Checked

        return self._child_state

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

    def invalidate_child_state(self):
        """Indicate that the cached _child_state attribute should
        be considered invalid and be recalculated on next call. Does
        not propagate up."""
        self._child_state = None


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
