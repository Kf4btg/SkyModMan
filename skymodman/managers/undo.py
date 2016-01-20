import collections
from skymodman.utils import singledispatch_m, dispatch_on
from pprint import pprint

# Delta = collections.namedtuple("Delta", "attrname previous current")
Delta = collections.namedtuple("Delta", "id attrname previous current")

class delta_:

    @staticmethod
    def make(attrname, prev_value, updated_value, description=None):
        """
        Create and return a Delta object change descriptor.

        :param attrname: Name of the attribute being changed
        :param prev_value: The value of the attribute before the change
        :param updated_value: value of the attribute after the change
        :param description: Text description of the change made, for display in e.g. undo menu items. If not provided, default to simply "Change <attrname>".
        :return:
        """
        if description is None:
            description = "Change {}".format(attrname)

        return Delta(attrname, prev_value, updated_value)

    @staticmethod
    def produce(from_obj, attrname, new_value, desc=None):
        """
        create and return a Delta change descriptor object for the named attribute using the current value of that attribute from 'from_obj' and the given new_value.

        :param from_obj:
        :param attrname: must be available via getattr(from_obj, attrname)
        :param new_value:
        :param desc:
        :return:
        """
        if desc is None:
            desc = "Change {}".format(attrname)

        return Delta(attrname, getattr(from_obj, attrname), new_value)



class UndoStack:

    def __init__(self):
        self.stack = []

    @property
    def stacksize(self):
        return len(self.stack)

class RevisionTracker:

    stackitem = collections.namedtuple("stackitem", "id delta description")
    """These make up the elements of the master undo stack; they hold a reference to the object that was modified for a specific change operation, as well as a text description of the change that can be displayed e.g. in a menu"""

    # def __init__(self, target_type, keyfunc, *slots, attrgetter=None,attrsetter=None):
    def __init__(self, target_type=None, keyfunc=None, *slots, attrgetter=None, attrsetter=None, descriptions=None):
        """Initialize the Revision Tracker, allowing the pushing of change operations and performing undo/redo commands. To register a type during construction, pass values for the optional arguments: at a minumum `target_type`, `keyfunc`, and some number of `slots` must be provided to register a type. Types can also be registered after construction with the ``register()`` method. See that method for descriptions of the parameters."""


        self._savepoint = 0

        # -----------------------------------------------
        # Mappings and collections
        # -----------------------------------------------
        self._descriptions = {}

        self._slots = {}    #dict[type, tuple[str]]
        self._keyfuncs = {} #dict[type, func(type)->id]

        self.attr_getters = {} #dict[type, func(object, str)->val]
        self.attr_setters = {} #dict[type, func(object, str, val)]

        self.undostack = collections.deque() #type: collections.deque[RevisionTracker.stackitem]
        self.redostack = collections.deque() #type: collections.deque[RevisionTracker.stackitem]

        # determines which Delta field to get without knowing
        # precisely which stack you're dealing with.
        self._get_delta_field = {
            id(self.undostack): lambda d: d.previous,
            id(self.redostack): lambda d: d.current,
        }

        # dict of target_ids to target_objects
        self._tracked = {}  # {id: object}
        # a dictview collection on the keys of the tracked objects for easy access to the target ids
        self._ids = self._tracked.keys()

        # mapping of ids to a full description of the item attributes at the time tracking began. Used for the final undo.
        self._initialstates = {} # {id: {attr:val, ...}, ...}
        # mapping of ids to a full description of the item attributes at the time of the last save. Used for the detecting 'manual' undos.
        # todo: maybe it would be better to just check a few items earlier in the undo stack to see if the target has been reverted...
        self._cleanstates = {} # {id: {attr:val, ...}, ...}

        # -----------------------------------------------
        # register initial type if one was passed
        # -----------------------------------------------

        if target_type and keyfunc and len(slots)>0:
            self.register(target_type, keyfunc, *slots,
                          attrgetter=attrgetter,
                          attrsetter=attrsetter,
                          descriptions=descriptions)

        # if attrgetter is not None:
        #     assert callable(attrgetter)
        #     self._getattr = lambda tid, n: attrgetter(self._tracked[tid], n)
        # else:
        #     self._getattr = lambda t, n: getattr(self._tracked[t], n)
        #
        # if attrsetter is not None:
        #     assert callable(attrsetter)
        #
        #     def __sattr(tid, attr, val):
        #         self._tracked[tid] = attrsetter(self._tracked[tid], attr, val)
        #
        #     self._setattr = lambda t, n, v: __sattr(t, n, v)
        # else:
        #     self._setattr = lambda t, n, v: setattr(self._tracked[t], n, v)


    @property
    def max_undos(self):
        return len(self.undostack)

    @property
    def max_redos(self):
        return len(self.redostack)

    @property
    def total_stack_size(self):
        return self.max_undos+self.max_redos

    @property
    def num_tracked(self):
        return len(self._ids)

    def __getitem__(self, target_id):
        return self._tracked[target_id]

    @property
    def __allmappings(self):
        """
        :return: a tuple containing references to each of this tracker's {target_id: ...} mappings. No specific order is guaranteed.
        """
        return self._tracked, self._initialstates, self._cleanstates

    def save(self):
        """Sets the current stack position as the 'clean' state"""
        # since max_undos describes the 'lower half' of the stack below the current state, its value can be thought of as the position of an 'undo-cursor'.  Saving sets the 'save-cursor' to match the undo-cursor.
        self._savepoint=self.max_undos

    @property
    def isclean(self):

        return self._savepoint==self.max_undos

    @property
    def steps_to_revert(self):
        """Undo steps needed to return the most recent save point. If a negative value is returned, that means **redo**-steps are required, instead"""
        if self._savepoint < 0:
            # todo: make a better exception for this
            raise IndexError("No valid savepoint is active.")
        return self.max_undos - self._savepoint

    ##===============================================
    ## Registering types
    ##===============================================
    def register(self, target_type, keyfunc, *slots, attrgetter=None, attrsetter = None, descriptions = None):
        """

        :param target_type:
            a type (class or baseclass) that added targets may be an instance of.
        :param (object)->Any keyfunc:
            a callable object that takes an instance of the `target_type` and returns a unique id value that can be used to distinguish that instance from all other tracked targets (must be unique re: ALL other tracked items, not just items of the same type)
        :param tuple[str] slots:
            each `slots` argument is the name of an attribute that instances of `target_type` may possess; only changes to registered slots will be tracked.

        :param (object, str)->Any attrgetter:
            if specified, must be a callable object that takes two parameters--an instance of `target_type`; and the name of a property or attribute--and returns the value of that attribute for the passed instance. This callback will be used instead of getattr() to get values from tracked targets.
        :param (object, str, Any)->object attrsetter:
            if specified, must be a callable object that takes three parameters--an instance of `target_type`; the name of a property or attribute; and some value--and updates that attribute on the instance to match the passed value. It should then return the modified object. This callback will be used instead of setattr() to set values on tracked targets.

        :param dict[str, str] descriptions:
            if provided, should be a mapping of attribute names (each of which must be specified in `*slots`) to strings that will be inserted as the default description for changes to the corresponding attribute on instances of this `target_type`. If not specified, the description text defaults to "Change <attrname>". The description will most likely be displayed in a user-facing menu as 'Undo/Redo <desc>', so the default would be e.g. "Undo Change attributename". Which is very generic. It may, however, be enough for some simple cases.

            Default descriptions can be modified at any time using the ``registerDescription()`` method, and individual changes can be passed a specialized description text when pushing them to the stack, allowing very fine control over the displayed text.
        """
        # copy slots over to a tuple keyed by the target type
        self._slots[target_type] = tuple(s for s in slots)

        assert callable(keyfunc)
        # will be used to get a unique id from passed targets
        self._keyfuncs[target_type] = keyfunc

        # default descriptions to use when adding a new Delta.
        # New defaults can be registered later, and the text can be
        # overridden for an individual change when it is pushed.
        self._descriptions[target_type] = {
            s:
                descriptions[s]
                    if s in descriptions
                else "Change ".format(s)
            for s in slots
        }

        # -----------------------------------------------
        # define attribute getter/setter
        # -----------------------------------------------

        if attrgetter is not None:
            assert callable(attrgetter)
            self.attr_getters[target_type] = lambda tid, n: attrgetter(self._tracked[tid], n)
        else:
            self.attr_getters[target_type] = lambda t, n: getattr(self._tracked[t], n)

        if attrsetter is not None:
            assert callable(attrsetter)
            def __sattr(tid, attr, val):
                self._tracked[tid] = attrsetter(self._tracked[tid], attr, val)

            self.attr_setters[target_type] = lambda t, n, v: __sattr(t, n, v)
        else:
            self.attr_setters[target_type] = lambda t, n, v: setattr(self._tracked[t], n, v)

    ##==============
    ## Attr get/set
    ##==============
    def get_attr(self, target, attr_name):
        t = type(target)
        tid = self._targetID_fortype(target, t)
        return self._get_attr(t, tid, attr_name)

    def _get_attr(self, target_type, target_id, attr_name):
        return self.attr_getters[target_type](target_id, attr_name)

    def set_attr(self, target, attr_name, value):
        t = type(target)
        tid = self._targetID_fortype(target, t)
        self._set_attr(t, tid, attr_name, value)

    def _set_attr(self, target_type, target_id, attr_name, value):
        self.attr_setters[target_type](target_id, attr_name, value)

    # get id
    def _targetID(self, target):
        """Get the id for the target by calling the key function for the target's type"""
        return self._keyfuncs[type(target)](target)

    def _targetID_fortype(self, target, target_type):
        """Can be used to avoid lookup of a target's type if it is already know, or to 'fake' a target's type if needed for some reason"""
        return self._keyfuncs[target_type](target)


    bstr = (str, bytes)
    #
    # def pushNew(self, target, *args, desc=None):
    #     """Use the first time a change is added for an object;
    #     this causes the tracker to register `target` as a tracked item and begin managing its undo/redo state.
    #
    #     For subsequent changes to this target, use the ``push()`` method
    #
    #     :param target:
    #         the actual object to tracked. To prevent state corruption, any changes to the target should only be done through the DiffTracker after tracking has begun.
    #     :param target_id:
    #         must be a unique, hashable value that can be used to identify this object among all the other tracked items
    #     :param args: see description for the ``push()`` method.
    #     """
    #     target_id = self._targetID(target)
    #
    #     if target_id not in self._ids:
    #         self._tracked[target_id] = target
    #         self._initialstates[target_id] = \
    #             self._cleanstates[target_id] = \
    #             self._get_current_state(target_id)
    #
    #     self.push(target_id, *args, desc=None)


    def _start_tracking(self, target, target_id):
        self._tracked[target_id] = target
        self._initialstates[target_id] = \
            self._cleanstates[target_id] = \
            self._get_current_state(target_id)

    def push(self, target, *args, desc=None):
        """Basically an overloaded method for recording changes in several ways (Change, Delta, DeltaGroup)
            * ``push(target, attrname, prev_value, curr_value, desc=None)``
            * ``push(target, attrname, curr_value, desc=None)``
            * ``push(target, Delta, description=None)``
        or
            * ``push(List[targets], List[Delta], desc=None)``
            * ``push(List[targets], List[tuple(attrname, prev_value, new_value)], desc=None)``
            * ``push(List[targets], List[tuple(attrname, new_value)], desc=None)``

        :param target: in all cases except for the last few (List[targets]), this is the target object of the change.

        The latter cases are for pushing a 'Delta Group' to the stack. A 'Delta Group' is simply a list of regular revision deltas (of arbitrary length, and can contain targets of mixed types) that will be undone/redone as a group: a single undo or redo operation will undo or redo every change recorded by the group deltas.

        For these Delta Group cases, the `target` argument to push should be a list or other flat iterable of all the changed targets in the group, in the order the changes are meant to happen. Each item in this iterable should correspond by index to an item in the second argument, described below.


        :param args:
            For the forms of push that take a single `target` argument, this should either be three arguments in the order (attribute_name, previous_value, current_value); two arguments in the order (attribute_name, current_value); or a ``Delta`` object with the corresponding fields set.

            For the Delta Group forms, the second argument (the actual 'Delta Group') is another list composed of either:
            ``Delta`` objects describing the changes per target;
            3-tuples with the attribute name, previous value, and updated value all provided;
            or 2-tuples with only the attribute name and new value provided. For this final situation, the previous value will be read from the target object before the change is made.

        :param str desc:
            Each overload also takes an optional `desc` argument which can be used to override the default text description of the change being made. Note that for Delta Groups, if `desc` is not provided, the default description will be taken from the type and changed attribute of the final target in the group.
        """

        # ttype = type(target)
        # target_id = self._targetID_fortype(target, ttype)

        # if target_id not in self._ids:
        #     self._start_tracking(target, target_id)
            # self._tracked[target_id] = target
            # self._initialstates[target_id] = \
            #     self._cleanstates[target_id] = \
            #     self._get_current_state(target_id)

        # sitem = self._push(*args, target_id=target_id, target_type=ttype, desc=desc) #type: RevisionTracker.stackitem

        sitem = self._push(*args, target=target, desc=desc)

        # self._truncate_redos()
        # adding a new change invalidates the redos
        self.redostack.clear()

        # but we add this right back on so that we can just call redo()
        self.redostack.append(sitem)
        # now need to actually apply the change
        self.redo()

    def pushGroup(self, *changes, desc=None):
        """Push a grouped block of revisions to the stack. All changes in a group will be undone/redone in a single undo/redo operation.
        :param changes: Each change should be either a 4-tuple with form(target, attr_name, old_val, new_val) or a 3-tuple with form (target, attr_name, new_val). In the latter case, the 'old_val' will be read from the target before the update is made.

        """
        if len(changes)==1: self.push(*changes[0], desc)

        tids = []
        dgroup = []
        ttype = None # for access after loop
        attr = None  # for access after loop
        for t in changes:
            ttype = type(t[0])
            tid = self._targetID_fortype(t[0], ttype)
            if tid not in self._ids:
                self._start_tracking(t[0], tid)

            tids.append(tid)
            assert 2 < len(t) < 5

            attr = t[1]

            dgroup.append(Delta( tid,
                    attr,
                    self._get_attr(ttype, tid, attr) if len(t)==3 else t[2],
                    t[-1]))

        if not desc:
            # take default desc from type and attrname of last
            # seen item in change list
            desc = self._descriptions[ttype][attr]

        self._finish_pushDeltaGroup(tids, dgroup, desc=desc)


    def pushDeltaGroup(self, targets, deltas, desc=None):

        pass

    # def _finish_pushDeltaGroup(self, deltas, desc):





    @singledispatch_m
    def _push(self, *args, **kwargs):
        raise TypeError("Unrecognized type for arguments to push()")

    @_push.register(str)
    @_push.register(bytes) #attribute name (raw change data)
    def _(self, attr, val1, val2=..., *, target, desc=None):
        target_type = type(target)
        target_id = self._targetID_fortype(target, target_type)

        if not desc:
            desc = self._descriptions[target_type][attr]

        if val2 is ...:
            # ... is our `None` placeholder, so that `None` can actually
            # be passed as a value. Thus, this means that val2 was not
            # specified, indicating that val1 is the new value and we should
            # pull the old value from the object itself.
            return self.stackitem(Delta(target_id, attr, self._get_attr(target_type, target_id, attr), val1), desc)

        # otherwise assume val1 is oldval and val2 is newval
        return self.stackitem(target_id, Delta(attr, val1, val2), desc)

    @_push.register(Delta)
    def _(self, delta, *, target, desc=None):
        target_type = type(target)

        if delta.id not in self._ids:
            self._start_tracking(target, delta.id)

        if not desc:
            desc = self._descriptions[target_type][delta.attrname]
        return self.stackitem(delta, desc)

    @_push.register(list)
    def _(self, delta_group, *, target, desc=None):
        """
        :param delta_group: list[Delta|tuple(str,Any,Any)|tuple(str,Any)]
        :param target: list of targets
        :param desc:
        :return:
        """

        tids = []
        dgroup = []
        ttype = None  # for access after loop
        attr = None  # for access after loop
        for t,d in zip(target, delta_group):
            ttype = type(t)

            # preconstructed Deltas
            if isinstance(d, Delta):
                attr = d.attrname
                dgroup.append(d)
                tids.append(d.id)
                if d.id not in self._ids:
                    self._start_tracking(t, d.id)

            # tuples w/ raw change data
            else:
                #verify appropriate number of elements
                assert 1 < len(d) < 4

                tid = self._targetID_fortype(t, ttype)
                if tid not in self._ids:
                    self._start_tracking(t, tid)
                tids.append(tid)

                attr = d[0]

                dgroup.append(
                        Delta(
                            tid,
                            attr,
                            self._get_attr(ttype, tid, attr)
                                if len(d) == 2 # (name, newval)
                            else d[2], # (name, oldval, newval)
                            d[-1])) #always newval

        if not desc:
            # take default desc from type and attrname of last
            # seen item in change list
            desc = self._descriptions[ttype][attr]

        return self.stackitem(dgroup, desc)


        # if not desc:
        #     desc = self._descriptions[delta_group[-1].attrname]
        #
        # # convert list to tuple for hashability
        # return self.stackitem(target_id, tuple(delta_group), desc)




        # record the most recently touched target
        # self.undostack.append(self.stackitem(target_id, desc))

    def _get_current_state(self, target_id):
        """Returns a dictionary of {attribute_name: value} pairs for the current value of each attribute of the target that matches one of the tracker's registered 'slots'."""
        return {s: self.get_attr(target_id, s)
                for s in self._slots}

    ##===============================================
    ## Undo/Redo
    ##===============================================

    def _do(self, steps=1):
        if steps < 0:
            steps, fromstack, tostack = min(abs(steps), self.max_undos), self.undostack, self.redostack
        else:
            steps, fromstack, tostack = min(steps, self.max_redos), self.redostack, self.undostack
        if not steps:  # if steps==0 or maxops == 0
            return False

        self._apply_changes(
                self._accum_changes(
                        fromstack,
                        tostack,
                        steps))
        return True


    def undo(self, steps=1):
        return self._do(-steps)

    redo = _do

    ##===============================================
    ## Helpers
    ##===============================================

    def _apply_changes(self, changed):

        for tid, changes in changed.items():
            for prop, val in changes.items():
                self.set_attr(tid, prop, val)

    def _accum_changes(self, fromstack, tostack, steps):
        """
        For `steps` iterations, this pops the last item off of `fromstack` and collects the change information stored inside, overwriting changes to the same attribute of the same target with the most recently encountered value. That information is stored and returned in an ordered dictionary keyed by the target id. This odict can be iterated through afterwards to apply the accumulated changes to the appropriate targets

        :param fromstack:
        :param tostack:
        :param steps:
        :return:
        """

        changed = collections.OrderedDict() # {target: {attr: value, ...}, ...}

        for s in range(steps):
            sitem = fromstack.pop()
            tid, delta, desc = sitem

            if not isinstance(delta, Delta):
                # then it's a delta group
                for d in delta: #type: Delta
                    val = self._get_delta_field[id(fromstack)](d)
                    try:
                        changed[tid].update({d.attrname: val})
                    except KeyError:
                        changed[tid] = {d.attrname: val}

                # we always reverse the group before adding it to the other stack so that 'going the other way' will iterate over the group in the correct order.
                sitem = sitem._replace(delta=tuple(reversed(delta)))
            else:
                # whether we pull the previous or current
                # field from the Delta depends on whether this
                # is an undo or a redo, which we don't know due
                # to the genericn nature of this function. However,
                # we can use the id() of `fromstack` to query
                # a predefined mapping to determine the answer
                # for us.
                val = self._get_delta_field[id(fromstack)](delta)
                try:
                    changed[tid].update({delta.attrname: val})
                except KeyError:
                    changed[tid] = {delta.attrname: val}

            # now add this stackitem to the other stack
            tostack.append(sitem)
        return changed

    def revertAll(self):
        """Undo every change in the undostack"""
        return self.undo(self.max_undos)

    def revertToSave(self):
        """Undo (or redo) until the latest save point is reached. Returns true on success, or False if no valid save point can be determined."""
        try:
            steps = self.steps_to_revert
        except IndexError:
            return False

        return self.undo(steps)


    def revertItem(self, target_id, *, remove_after=False):
        """
        This is not technically an 'undo'; it does not walk the revision stack, but instead updates the target so that its current attributes match the values from its initial state. The `revert` itself is pushed to the revision stack and treated as a normal operation that can itself be subject to Undo/Redo.

        If, however, the optional, kw-only param `remove_after` is set to ``True``, all references to the object will be **removed** from the tracker after its attributes are set and will need to be re-added using ``pushNew()`` if it is decided to allow undo/redo of the object again.

        :param target_id:
        """
        # compare current target attributes to initial state, and push a delta group of those which need changing to match initial state.
        istate = self._initialstates[target_id]
        dgroup = []
        for s in self._slots:
            currval = self.get_attr(target_id, s)
            if istate[s] != currval:
                dgroup.append(Delta(s, currval, istate[s]))

        if dgroup: self.push(target_id, dgroup, desc="Revert Item")

        if remove_after:
            self.untrack(target_id)

    def untrack(self, target_id):
        """Stop tracking the object with the specified id. All references to the object will be removed from the tracker and its revision history will be lost. The object itself will not be affected."""

        for coll in self.__allmappings:
            try:
                del coll[target_id]
            except KeyError:
                pass

        # rotate through the deques and remove items w/ this id
        for d in [self.redostack, self.undostack]:
            for _ in range(len(d)):
                sitem=d.pop()
                if sitem.id != target_id:
                    d.appendleft(sitem)











class ObjectDiffTracker:

    stackitem = collections.namedtuple("stackitem", "id description")
    """These make up the elements of the master undo stack; they hold a reference to the object that was modified for a specific change operation, as well as a text description of the change that can be displayed e.g. in a menu"""

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

        # default descriptions to use when adding a new Delta. New defaults can be registered, and the text can be overridden for an individual change when it is created.
        self._descriptions = {s:"Change ".format(s) for s in slots}
        #todo: actually use descriptions

        # -----------------------------------------------
        # Mappings and collections
        # -----------------------------------------------

        # dict of target_ids to target_objects
        self._tracked = {}
        # a dictview collection on the keys of the tracked objects for easy access to the target ids
        self._ids = self._tracked.keys()

        # dict of target_ids to target revision stacks (list of Deltas)
        self._revisions = {}
        # mapping of ids to a full description of the item attributes at the time tracking began. Used for the final undo.
        self._initialstates = {}
        # mapping of ids to a full description of the item attributes at the time of the last save. Used for the detecting 'manual' undos.
        #todo: maybe it would be better to just check a few items earlier in the undo stack to see if the target has been reverted...
        self._cleanstates = {}

        # the 'revision cursors'
        # mapping of [target_id: int], where the value is the index in the target's revisions stack corresponding to the Delta object that describes the target's current revision state.
        self._revcur = {}

        # each stack will also need it's own savepoint cursor;
        # these point to the stack index that was current the last
        # time a save command was issued (or the program loaded)
        self._savecur = {}

        #----------------------
        # Master Stack
        #----------------------
        self._masterstack = [] #type: list[ObjectDiffTracker.stackitem]
        self._mastercursor = -1

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

    @property
    def __allmappings(self):
        """
        :return: a tuple containing references to each of this tracker's {target_id: ...} mappings. No specific order is guaranteed.
        """
        return self._tracked, self._revisions, self._initialstates, self._cleanstates, self._revcur, self._savecur

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
        """
        for tid, cur in self._revcur.items():
            self._savecur[tid] = cur

    def is_clean(self, target_id) -> bool:
        """Returns False if any revisions have been made to the target since the last savepoint"""

        return self._savecur[target_id] == self._revcur[target_id]

    def all_clean(self) -> bool:
        """Returns True iff every tracked object evaluates as clean. Short circuits on finding first non-clean obj"""
        return any(not self.is_clean(t) for t in self._ids)

    def _steps_to_revert(self, target_id) -> int:
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
        """Stop tracking the object with the specified id. All references to the object will be removed from the tracker and its revision history will be lost. The object itself will not be affected."""

        for coll in self.__allmappings:
            try:
                del coll[target_id]
            except KeyError:
                pass

    def resetTracker(self):
        """Forget all tracked objects. Does not revert or otherwise affect state of tracked objects. Does not change the registered "slots", default descriptions, or defined attr-getter/-setter callbacks."""
        for coll in self.__allmappings:
            coll.clear()
        self._masterstack.clear()

    def registerDescription(self, attrname, description):
        """Set a new default description text to be used for changes to the specified attribute name"""
        if attrname in self._slots and description is not None:
            self._descriptions[attrname] = description

    ##===============================================
    ## Tracking changes
    ##===============================================
    bstr = (str, bytes)
    def pushNew(self, target, target_id, *args):
        """Use the first time a change is added for an object; this causes the tracker to register `target` as a tracked item and begin managing its undo/redo state.

        For subsequent changes to this target, use the ``push()`` method

        :param target:
            the actual object to tracked. To prevent state corruption, any changes to the target should only be done through the DiffTracker after tracking has begun.
        :param target_id:
            must be a unique, hashable value that can be used to identify this object among all the other tracked items
        :param args: see description for the ``push()`` method.
        """

        if target_id not in self._tracked:
            self._tracked[target_id] = target
            self._revisions[target_id] = []
            self._revcur[target_id] = self._savecur[target_id] = -1
            self._initialstates[target_id] = \
                self._cleanstates[target_id] = \
                self._get_current_state(target_id)

        self.push(target_id, *args)

    def push(self, target_id, *args):
        """Basically an overloaded method for recording changes in several ways (Change, Delta, DeltaGroup)
            * ``push(target_id, attrname, prev_value, curr_value, description=None)``
            * ``push(target_id, Delta, description=None)``
            * ``push(target_id, Iterable(Delta), description=None)``

        :param args:
            should either be three arguments in the order (attribute_name, previous_value, current_value); a ``Delta`` object with the corresponding fields set; or several ``Delta`` objects contained in an ordered iterable such as a list. All the changes in a 'Delta group' will be undone/redone by a single undo or redo operation.
            Each overload also takes an optional `description` argument which can be used to override the default text description for this type of change.
        """
        if isinstance(args[0],self.bstr): #prop name
            attrname, desc=self._addChange(target_id, *args)
        elif isinstance(args[0], Delta):
            attrname, desc=self._addDelta(target_id, *args)
        elif isinstance(args[0], collections.Iterable):
            attrname, desc=self._addDeltaGroup(target_id, *args)
        else:
            raise TypeError("Unrecognized type for arguments to push()")

        # now need to actually apply the change
        self.redo(target_id)

        if not desc:
            desc = self._descriptions[attrname]

        # record the most recently touched target
        self._masterstack.append(self.stackitem(target_id, desc ))

    def _get_current_state(self, target_id):
        """Returns a dictionary of {attribute_name: value} pairs for the current value of each attribute of the target that matches one of the tracker's registered 'slots'."""
        return { s:self.get_attr(target_id, s)
                    for s in self._slots }

    def pushUpdate(self, target_id, attr, new_val, description=None):
        """Can be used instead of the `push()` method for adding a change to the target's revision stack. The current value for the attribute will be queried from the target and a Delta object created dynamically"""
        self._truncate_redos(target_id)
        self._revisions[target_id].append(Delta(attr, self.get_attr(target_id, attr), new_val))
        self.redo(target_id)

        if not description:
            description = self._descriptions[attr]

        self._masterstack.append(self.stackitem(target_id, description))


    def _addChange(self, target_id, attr, old_val, new_val, description=None):
        """
        Record a change operation to the tracked object specified by `target_id`
        """
        self._truncate_redos(target_id)
        self._revisions[target_id].append(Delta(attr, old_val, new_val))
        return attr, description

    def _addDelta(self, target_id, delta, description=None):
        """
        Record a change operation to the tracked object specified by `target_id`;
        the effect of the operation is given by `delta`, containing the name, old value, and new value of the updated attribute.

        :param target_id:
        :param delta:
        """
        assert isinstance(delta, Delta)
        self._truncate_redos(target_id)
        self._revisions[target_id].append(delta)

        return delta.attrname, description


    def _addDeltaGroup(self, target_id, deltas, description=None):
        """Any Deltas contained within the sequence `deltas` will be
        undone/redone as a single operation when invoked via Undo/Redo

        :param target_id:
        :param deltas: must be an ordered sequence of Delta objects
        """
        self._truncate_redos(target_id)
        self._revisions[target_id].append(deltas)
        return deltas[-1].attrname, description


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
        :return: a dict of {attrname: value, ...} containing which attributes will need to be set to what values to revert the target to the desired state.
        """
        acc_changes = {}  # accumulate the changes as we go backwards/forwards

        revlist = self._revisions[target_id]
        cur = self._revcur[target_id]
        start= cur+max(step,0) # ==cur for undo, ==cur+1 for redo
        end= start+step*num_steps

        # catch trying to undo the first change
        if end < 0:
            # just return the saved initial state, which is already
            # a dict containing a full description of the target's
            # attributes when tracking first began.
            return self._initialstates[target_id]


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
                        (None,
                         c.current, # step==1
                         c.previous # step==-1
                         )[step] # this is what i call a "silly hack"
            else:
                acc_changes[change.attrname] = (None, change.current, change.previous)[step]

        # print("changes: ", acc_changes)

        return acc_changes

    def _apply_opchanges(self, target_id, changes):
        """
         Apply finalized state
         changes to target.


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
        # return True

    def revert(self, target_id, *, remove_after=False):
        """
        This is not technically an 'undo'; it does not walk the revision stack, but instead updates the target so that its current attributes match the values from its initial state. The `revert` itself is pushed to the revision stack and treated as a normal operation that can itself be subject to Undo/Redo.

        If, however, the optional, kw-only param `remove_after` is set to ``True``, all references to the object will be **removed** from the tracker after its attributes are set and will need to be re-added using ``pushNew()`` if it is decided to allow undo/redo of the object again.

        :param target_id:
        """
        # compare current target attributes to initial state, and push a delta group of those which need changing to match initial state.
        istate = self._initialstates[target_id]
        dgroup = []
        for s in self._slots:
            currval = self.get_attr(target_id, s)
            if istate[s] != currval:
                dgroup.append(Delta(s, currval, istate[s]))

        if dgroup: self.push(target_id, dgroup)

        if remove_after:
            self.untrack(target_id)



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
        # stat = self._apply_opchanges(target_id, acc_changes)
        self._apply_opchanges(target_id, acc_changes)
        self._revcur[target_id] += _norm*_steps


        # return stat
        return True

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

    ##===============================================
    ## Master Undo/Redo
    ##===============================================

    def Undo(self, steps=1):
        """
        Using the ids from the master stack of recently changed targets, perform a number of undo operations equal to the value of `steps` on the recorded targets as they are encountered, starting at the current master cursor position and iterating backwards.
        :param steps:
        :return:
        """

        for i in range(steps):
            mru = self._masterstack[self._mastercursor-i]
            if not self.undo(mru.id):
                self._mastercursor -= i
                break
        else:
            self._mastercursor -= steps

    def Redo(self, steps=1):
        for i in range(steps):
            mru = self._masterstack[self._mastercursor+i]
            if not self.redo(mru.id):
                self._mastercursor += i
        else:
            self._mastercursor += steps

    @property
    def master_stack_size(self):
        return len(self._masterstack)

    @property
    def master_cursor(self):
        return self._mastercursor


