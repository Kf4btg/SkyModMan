import collections
from pprint import pprint

Delta = collections.namedtuple("Delta", "attrname previous current")

class ObjectDiffTracker:

    def __init__(self, target_type, *slots, attrgetter=None,attrsetter=None):
        """

        :param type target_type:
            type (class) of object being tracked
        :param list[str] slots:
            names of tracked properties in an instance of target type
        :param callable attrgetter:
            if specified, must be a callable object that takes two parameters--an instance of `target_type`; and the name of a property or attribute--and returns the value of that attribute for the passed instance. This callback will be used instead of getattr() to get values from tracked targets.
        :param callable attrsetter:
            if specified, must be a callable object that takes three parameters--an instance of `target_type`; the name of a property or attribute; and some value--and sets that attribute on the instance to the passed value. It should then return the modified object. This callback will be used instead of setattr() to set values on tracked targets.
        """
        self._type = target_type
        self._slots = slots

        # -----------------------------------------------
        # Mappings and collections
        # -----------------------------------------------

        # dict of target_ids to target_objects
        self._tracked = {}
        # a dictview collection on the keys of the tracked objects for easy access to the target ids
        self._ids = self._tracked.keys()

        # dict of target_ids to target revision stacks (list of Deltas)
        self._revisions = {}

        # the 'revision cursors'
        # mapping of [target_id: int], where the value is the index in the target's revisions stack corresponding to the Delta object that describes the target's current revision state.
        self._revcur = {}

        # each stack will also need it's own savepoint cursor;
        # these point to the stack index that was current the last
        # time a save command was issued (or the program loaded)
        self._savecur = {}

        #-----------------------------------------------
        # define attribute getter/setter
        #-----------------------------------------------

        if attrgetter is not None:
            assert callable(attrgetter)
            self._getattr = lambda tid,n: attrgetter(self._tracked[tid], n)
        else:
            self._getattr = lambda t,n: getattr(self._tracked[t],n)

        if attrsetter is not None:
            assert callable(attrsetter)
            def __sattr(tid,attr,val):
                self._tracked[tid] = attrsetter(self._tracked[tid],attr,val)
            self._setattr = lambda t,n,v: __sattr(t,n,v)
        else:
            self._setattr = lambda t,n,v: setattr(self._tracked[t], n,v)


    ##===============================================
    ## Properties (-ish)
    ##===============================================

    def stack_size(self, target_id):
        return len(self._revisions[target_id])

    def max_undos(self, target_id):
        return self._revcur[target_id] + 1

    def max_redos(self, target_id):
        return self.stack_size(target_id)-self.max_undos(target_id)

    ## Attr get/set
    ##==============
    def get_attr(self, target_id, attr_name):
        return self._getattr(target_id, attr_name)

    def set_attr(self, target_id, attr_name, value):
        self._setattr(target_id, attr_name, value)

    ## Retrieve a tracked object by id
    ##=================================
    def __getitem__(self, target_id):
        return self._tracked[target_id]

    ## Saving/checking saved status
    ##=============================
    def save(self):
        """
        Mark the current revision position in each stack as the "clean" state.
        :return:
        """
        for tid, cur in self._revcur.items():
            self._savecur[tid] = cur

    def is_clean(self, target_id):
        """Returns False if any revisions have been made to the target since the last savepoint"""

        return self._savecur[target_id] == self._revcur[target_id]

    def all_clean(self):
        """Returns True iff every tracked object evaluates as clean. Short circuits on finding first non-clean obj"""
        return any(not self.is_clean(t) for t in self._ids)

    def _steps_to_revert(self, target_id):
        """ number of undo steps required to revert this target
           to its most recent saved state

        :param target_id:
        :return: # of undo-ops; negative means redo-ops
        """
        return self._revcur[target_id] - self._savecur[target_id]

    ##===============================================
    ## Adding/removing Tracked objects
    ##===============================================

    def untrack(self, target_id):
        """Stop tracking the object with the specified id"""

        for coll in [self._tracked, self._revisions, self._revcur, self._savecur]:
            try:
                del coll[target_id]
            except KeyError:
                pass

    def resetTracker(self):
        """Forget all tracked objects. Does not revert state."""
        for coll in [self._tracked, self._revisions, self._revcur, self._savecur]:
            coll.clear()

    ##===============================================
    ## Tracking changes
    ##===============================================
    bstr = (str, bytes)
    def addNew(self, target, target_id, *args):
        """Use the first time a change is added for an object; this causes the tracker to register `target` as a tracked item and begin managing its undo/redo state.

        For subsequent changes to this target, use the ``add()`` method

        :param target:
            the actual object to tracked. To prevent state corruption, any changes to the target should only be done through the DiffTracker after tracking has begun.
        :param target_id:
            must be a unique, hashable value that can be used to identify this object among all the other tracked items
        :param args: see description for the ``add()`` method.
        """

        if target_id not in self._tracked:
            self._tracked[target_id] = target
            self._revisions[target_id] = []
            self._revcur[target_id] = self._savecur[target_id] = -1

        self.add(target_id, *args)

    def add(self, target_id, *args):
        """Basically an overloaded method for recording changes in several ways (Change, Delta, DeltaGroup)

            * add(target_id, attrname, prev_value, curr_value)
            * add(target_id, Delta)
            * add(target_id, Iterable(Delta))

        :param args:
            should either be three arguments in the order (attribute_name, previous_value, current_value); a ``Delta`` object with the corresponding fields set; or several ``Delta`` objects contained in an ordered iterable such as a list. All the changes in a 'Delta group' will be undone/redone by a single undo or redo operation.
        """
        if isinstance(args[0],self.bstr): #prop name
            self._addChange(target_id, *args)
        elif isinstance(args[0], Delta):
            self._addDelta(target_id, *args)
        elif isinstance(args[0], collections.Iterable):
            self._addDeltaGroup(target_id, *args)

        # now need to actually apply the change
        self.redo(target_id)

    def _addChange(self, target_id, prop, old_val, new_val):
        """
        Record a change operation to the tracked object specified by target_id;
        the effect of the operation is given by `delta`, containing the names and new values of the updated properties.

        """
        self._truncate_redos(target_id)
        self._revisions[target_id].append(Delta(prop, old_val, new_val))

    def _addDelta(self, target_id, delta):
        """
        Record a change operation to the tracked object specified by target_id;
        the effect of the operation is given by `delta`, containing the name, old value, and new value of the updated property.

        :param target_id:
        :param delta:
        """
        assert isinstance(delta, Delta)
        self._truncate_redos(target_id)
        self._revisions[target_id].append(delta)


    def _addDeltaGroup(self, target_id, deltas):
        """Any Deltas contained within the sequence `deltas` will be
        undone/redone as a single operation when invoked via Undo/Redo

        :param target_id:
        :param collections.Iterable[Delta] deltas: must be an ordered sequence of Delta objects
        """
        self._truncate_redos(target_id)
        self._revisions[target_id].append(deltas)

    def _truncate_redos(self, target_id):
        """
        If a change is being added and we are not at the end of the revision stack
        (because some actions have been undone), truncate the items after the
        current cursor position so that the current position is now the final item of the stack.

        :param target_id:
        """
        # get max undos, a.k.a. (revision_cursor_index)+1;
        # this should == stacksize for this target if we're at
        # end of the stack.
        r = self.max_undos(target_id)

        # But if it doesn't, then it is the start
        # of the slice of the stack we need to drop.
        if self.stack_size(target_id) > r:
            self._revisions[target_id][r:] = []

            # invalidate save cursor if it was in the part
            # of the stack that just got chopped
            if self._savecur[target_id] > r:
                self._savecur[target_id] = -1

    ##===============================================
    ## Undo/Redo Helpers
    ##===============================================

    def _accum_changes(self, target_id, num_steps, step=-1):
        """

        :param target_id:
        :param int num_steps: number of steps to move
        :param int step: either +1 or -1, depending on if this is called from the redo or undo method
        :return:
        """
        acc_changes = {}  # accumulate the changes as we go backwards/forwards

        revlist = self._revisions[target_id]
        cur = self._revcur[target_id]
        start= cur+max(step,0) # ==cur for undo, ==cur+1 for redo
        end= start+step*num_steps


        # print("revlist: ")
        # pprint(revlist)
        # print("cursor pos: ", cur)
        #
        # print("slice: [start=",start,", stop=",end,
        #       ", step=",step,"] == ",
        #       revlist[start:end:step])

        for change in revlist[start:end:step]:

        # for s in range(num_steps):
        #     start += step
        #     change = revlist[start]  # type: Delta|List[Delta]
        #     print("delta: ", change)

            if not isinstance(change, Delta): #delta group
                for c in change[::step]:  # type: Delta
                    acc_changes[c.attrname] = \
                        (None, c.current, c.previous)[step] # this is what i call a "silly hack"
            else:
                acc_changes[change.attrname] = (None, change.current, change.previous)[step]

        # print("changes: ", acc_changes)

        return acc_changes

    def _apply_opchanges(self, target_id, changes):
        """
        Apply finalized state changes to target.

        :param target_id:
        :param changes: dict of changes accumulated during traversal of revision stack
        :return:
        """
        # target = self._tracked[target_id]
        # print(changes)

        for prop, val in changes.items():
                # print(getattr(target, prop), end="==>")
                self.set_attr(target_id, prop, val)
                # print(getattr(target, prop), end="::")

        # print()
        return True



    def most_recent_values(self, target_id):
        """gets the most recently recorded value for each property that has ever been changed for this target. Properties that have never been changed will not be included"""
        vals = {}
        cur = self._revcur[target_id]
        for delta in self._revisions[target_id][cur::-1]: #type: Delta
            if not delta.attrname in vals:
                vals[delta.attrname] = delta.current

                # short circuit when have a value for everything
                if len(vals) == len(self._slots):
                    break

        return vals

    ##===============================================
    ## Undo/Redo Calls
    ##===============================================


    def _walk_stack(self, target_id, steps):
        """
        This is the real method that handles both undo and redo calls; which operation is performed depends on the sign (positive or negative) of `steps`.

        :param target_id:
        :param int steps:
        :return: False if the operation could not be performed for some reason, such as steps being passed as 0, or if there are no more possible operations of that type in the stack. True if the undo/redo operation proceeds as normal.
        """

        _steps = min(abs(steps),
                     self.max_undos(target_id) if steps < 0
                     else self.max_redos(target_id))

        # if steps was passed as 0 or there are no undo/redos to do:
        if _steps == 0: return False # no change

        _norm = abs(steps)//steps #step direction unit vector


        acc_changes = self._accum_changes(target_id, _steps, _norm)
        stat = self._apply_opchanges(target_id, acc_changes)
        self._revcur[target_id] += _norm*_steps

        return stat

    def undo(self, target_id, steps=1):
        """

        :param target_id:
        :param steps:
            how many steps to move backward in the revision stack. Note that a negative value here will actually result in a redo.
        :return: False if the operation could not be performed for some reason, such as steps being passed as 0, or if the revision cursor is already at the beginning of the stack. True if the undo operation proceeds as normal.
        """
        return self._walk_stack(target_id, -steps)

    def redo(self, target_id, steps=1):
        """

        :param target_id:
        :param steps: how many steps in the revision stack to move forward. Note that a negative value here will actually result in an undo.
        :return: False if the operation could not be performed for some reason, such as steps being passed as 0, or if the revision cursor is already at the end of the stack. True if the redo operation proceeds as normal.
        """
        return self._walk_stack(target_id, steps)

