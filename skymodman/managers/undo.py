import collections
from pprint import pprint

Delta = collections.namedtuple("Delta", "attrname previous current")

class ObjectDiffTracker:

    def __init__(self, target_type, *slots, callback=None):
        """

        :param type target_type: type (class) of object being tracked
        :param list[str] slots: names of tracked properties in an instance of target type
        """
        self._type = target_type
        self._slots = slots

        self._savepoint = -1 # updated when user saves, points to index in revision list that is the new "clean" state

        # container of Delta stacks for each registered property slot
        self._tracked = {}  # dict of target_ids to target_objects
        self._revisions = {} # dict of target_ids to target revision stacks (list of Deltas)

        self._callback = callback
        # self._callbacks = {} # if specified when adding a tracked item, the target's
                             # callback will be invoked instead of setattr when changing values
        # the 'revision cursor'
        self._revcur = {} # mapping of [id: int], where the value is the index in the target's revisions list corresponding to current location in the undo/redo stack for that item

    ##===============================================
    ## Properties (-ish)
    ##===============================================

    def stack_size(self, target_id):
        return len(self._revisions[target_id])

    def max_undos(self, target_id):
        return self._revcur[target_id] + 1

    def max_redos(self, target_id):
        return self.stack_size(target_id)-self.max_undos(target_id)

    ####
    ## Check/Set savepoint
    @property
    def savepoint(self) -> int:
        return self._savepoint

    @savepoint.setter
    def savepoint(self, new_savept):
        self._savepoint = new_savept

    def is_clean(self, target_id):
        """Returns False if any revisions have been made to the target since the last savepoint"""

        # if savepoint is beyond the length of this item's revstack,
        # then return true if the revision cursor points to end of stack
        return self._revcur[target_id] == min(self._savepoint, self.stack_size(target_id))

    def _steps_to_revert(self, target_id):
        """ number of undo steps required to revert this target
           to its most recent saved state

        :param target_id:
        :return: # of undo-ops; negative means redo-ops
        """
        return self._revcur[target_id] - self._savepoint

    ##===============================================
    ## Adding/removing Tracked objects
    ##===============================================

    # def track(self, target, target_id, callback=None):
    # def track(self, target, target_id):
    #     """Start tracking change operations for the specified object
    #
    #     :param target:
    #         the actual object being tracked. To prevent state corruption, changes to tracked items should only be done through the Delta/tracker mechanics.
    #     :param target_id:
    #         must be a unique, hashable value that can be used to identify this object amongst all the other tracked items
    #     :param callable callback:
    #         if specified, will be invoked instead of setattr when changing values on the target. Called with the property name and new value as arguments. Useful for immutable objects like namedtuples.
    #     """
    #     if target_id not in self._tracked:
    #         self._tracked[target_id] = target
    #         # if callback is not None: self._callbacks[target_id]=callback
    #
    #         self._revisions[target_id] = []

            # on first add, save the values for each tracked property
            # in the first entry of the revision stack
            # self._revisions[target_id] = {p:getattr(target, p) for p in self._slots}

    def untrack(self, target_id):
        """Stop tracking the object with the specified id"""

        for coll in [self._tracked, self._revisions, self._revcur, self._callbacks]:
            try:
                del coll[target_id]
            except KeyError:
                pass

    def resetTracker(self):
        """Forget all tracked objects. Does not revert state."""
        for coll in [self._tracked, self._revisions, self._revcur]:
            coll.clear()

    ##===============================================
    ## Tracking changes
    ##===============================================
    bstr = (str, bytes)
    def addNew(self, target, target_id, *args):
        """Use when adding the first change to begin tracking the target"""
        if target_id not in self._tracked:
            self._tracked[target_id] = target
            self._revisions[target_id] = []
            self._revcur[target_id]=-1

        self.add(target_id, *args)

    def add(self, target_id, *args):
        """Basically a selector for the the other _add* methods (Change, Delta, DeltaGroup)

            * add(target_id, attrname, prev_value, curr_value)
            * add(target_id, Delta)
            * add(target_id, Iterable(Delta))

        """
        if isinstance(args[0],self.bstr): #prop name
            self._addChange(target_id, *args)
        elif isinstance(args[0], Delta):
            self._addDelta(target_id, *args)
        elif isinstance(args[0], collections.Iterable):
            self._addDeltaGroup(target_id, *args)

        # self._revcur[target_id]+=1

        # now need to actually apply the change
        self.redo(target_id)

    def _addChange(self, target_id, prop, old_val, new_val):
        """
        Record a change operation to the tracked object specified by target_id;
        the effect of the operation is given by `delta`, containing the names and new values of the updated properties.

        :param target_id:
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
        :return:
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
        r = self.max_undos(target_id) # should == stacksize for this target if at end
        if self.stack_size(target_id) > r:
            self._revisions[target_id][r:] = []
            # invalidates savepoint if it is further ahead in undo-stack
            if self._savepoint > r:
                self._savepoint = -1

    ##===============================================
    ## Undo Management
    ##===============================================

    def _accum_changes(self, target_id, num_steps, step=-1):
        """

        :param target_id:
        :param num_steps: number of steps to move
        :param step: either +1 or -1, depending on if this is called from the redo or undo method
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

        # afterwards, update cursor
        # self._revcur[target_id] = start

        # print("changes: ", acc_changes)

        return acc_changes

    def _apply_opchanges(self, target_id, changes):
        """
        Apply finalized state changes to target.

        :param target_id:
        :param changes: dict of changes accumulated during traversal of revision stack
        :return:
        """
        target = self._tracked[target_id]
        # print(changes)


        if self._callback:
            for prop, val in changes.items():
                # print(getattr(target, prop), end=" ")

                self._callback(prop, val)
                # print(getattr(target, prop), end=" ")


        else:
            for prop, val in changes.items():
                # print(getattr(target, prop), end="==>")

                setattr(target, prop, val)
                # print(getattr(target, prop), end="::")

        # print()
        return True
    #
    # def _undo(self, target_id, steps=1):
    #     """Undo `steps` most recent change operations to the target"""
    #
    #     acc_changes  = self._accum_changes(target_id, steps, -1)
    #
    #     return self._apply_opchanges(target_id, acc_changes)


    ##===============================================
    ## Redo
    ##===============================================
    #
    # def _redo(self, target_id, steps=1):
    #
    #     acc_changes = self._accum_changes(target_id, steps, 1)
    #
    #     return self._apply_opchanges(target_id, acc_changes)


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


    ###
    def _walk_stack(self, target_id, steps):
        if steps == 0: return False  # steps==0 is a noop

        if steps < 0: #undo
            _steps = min(abs(steps), self.max_undos(target_id))
            _norm = -1 #step direction

        else: # steps > 0:  # redo
            _steps = min(steps, self.max_redos(target_id))
            _norm = 1

        acc_changes = self._accum_changes(target_id, _steps, _norm)
        stat = self._apply_opchanges(target_id, acc_changes)
        self._revcur[target_id] += _norm*_steps

        return stat

    def undo(self, target_id, steps=1):
        return self._walk_stack(target_id, -steps)

    def redo(self, target_id, steps=1):
        return self._walk_stack(target_id, steps)

