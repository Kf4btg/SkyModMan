import collections
from contextlib import suppress

from skymodman.utils import singledispatch_m

Delta = collections.namedtuple("Delta",
                               "id attrname previous current")

_bstr = (str, bytes)


class RevisionTracker:
    stackitem = collections.namedtuple("stackitem",
                                       "delta description")
    """These make up the elements of the master undo stack; they hold a reference to the object that was modified for a specific change operation, as well as a text description of the change that can be displayed e.g. in a menu"""

    def __init__(self, target_type=None,
                 keyfunc=None, *slots,
                 attrgetter=None, attrsetter=None,
                 descriptions=None):
        """Initialize the Revision Tracker, allowing the pushing of change
            operations and performing undo/redo commands.

            To register a type during construction, pass values for the optional
            arguments: at a minumum `target_type`, `keyfunc`, and some number of
            `slots` must be provided to register a type. Types can also be
            registered after construction with the ``register()`` method. See that
            method for descriptions of the parameters."""

        self._savepoint = 0

        # -----------------------------------------------
        # Mappings and collections
        # -----------------------------------------------
        self._descriptions = {}

        self._slots    = {}  # dict[type, tuple[str]]
        self._keyfuncs = {}  # dict[type, func(type)->id]
        self._types    = self._keyfuncs.keys()

        self.attr_getters = {}  # dict[type, func(object, str)->val]
        self.attr_setters = {}  # dict[type, func(object, str, val)]

        self.undostack = collections.deque()  # type: collections.deque[RevisionTracker.stackitem]
        self.redostack = collections.deque()  # type: collections.deque[RevisionTracker.stackitem]

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
        self._initialstates = {}  # {id: {attr:val, ...}, ...}
        # mapping of ids to a full description of the item attributes at the time of the last save. Used for the detecting 'manual' undos.
        # todo: maybe it would be better to just check a few items earlier in the undo stack to see if the target has been reverted...
        self._cleanstates = {}  # {id: {attr:val, ...}, ...}

        # -----------------------------------------------
        # register initial type if one was passed
        # -----------------------------------------------

        if target_type and keyfunc and len(slots) > 0:
            self.registerType(target_type, keyfunc, *slots,
                              attrgetter=attrgetter,
                              attrsetter=attrsetter,
                              descriptions=descriptions)

    @property
    def max_undos(self):
        return len(self.undostack)

    @property
    def can_undo(self):
        return self.max_undos > 0

    @property
    def max_redos(self):
        return len(self.redostack)

    @property
    def can_redo(self):
        return self.max_redos > 0

    @property
    def total_stack_size(self):
        return self.max_undos + self.max_redos

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
        self._savepoint = self.max_undos

    @property
    def isclean(self):

        return self._savepoint == self.max_undos

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
    def registerType(self, target_type, keyfunc, *slots,
                     attrgetter=None, attrsetter=None,
                     descriptions=None):
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

        if descriptions:
            self._descriptions[target_type] = {
                s:
                    descriptions[s]
                    if s in descriptions
                    else "Change {}".format(s)
                for s in self._slots[target_type]
                }
        else:
            self._descriptions[target_type] = {
                s: "Change {}".format(s)
                for s in self._slots[target_type]
                }

        # -----------------------------------------------
        # define attribute getter/setter
        # -----------------------------------------------

        if attrgetter is not None:
            assert callable(attrgetter)
            self.attr_getters[target_type] = lambda tid, n: attrgetter(
                                                    self._tracked[tid], n)
        else:
            self.attr_getters[target_type] = lambda t, n: getattr(
                                                    self._tracked[t], n)

        if attrsetter is not None:
            assert callable(attrsetter)

            def __sattr(tid, attr, val):
                self._tracked[tid] = attrsetter(self._tracked[tid],
                                                attr, val)

            self.attr_setters[target_type] = lambda t, n, v: __sattr(
                                                    t, n, v)
        else:
            self.attr_setters[target_type] = lambda t, n, v: setattr(
                                                    self._tracked[t], n, v)

    ##===============================================
    ## Register New Default Descriptions
    ##===============================================

    def registerDescription(self, target_type, attrname, description):
        """Set a new default description text to be used for changes to the specified attribute name"""

        if attrname in self._slots[
            target_type] and description is not None:
            self._descriptions[target_type][attrname] = description

    ##==============
    ## Attr get/set
    ##==============

    def get_attr(self, attr_name, target_id, target_type=None):
        if target_type:
            return self.attr_getters[target_type](target_id,
                                                  attr_name)
        else:
            return self.attr_getters[type(self[target_id])](target_id,
                                                            attr_name)

    def set_attr(self, attr_name, value, target_id):
        self.attr_setters[type(self[target_id])](target_id,
                                                 attr_name,
                                                 value)

    def getID(self, target, target_type=None):
        """Get the id for `target` object by calling the key function for the target's type. If the `target_type` is specified, type lookup of the target will be skipped and the value for `target_type` used instead. This can be used to avoid lookup of a target's type if it is already know, or to 'fake' a target's type if needed for some reason"""
        if target_type:
            return self._keyfuncs[target_type](target)

        return self._keyfuncs[type(target)](target)

    def getTarget(self, target_id):
        return self._tracked[target_id]

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
            * ``push(List[targets], List[{"id"=..., "attrname"=..., "previous"=..., "current"=...}, ...], desc=None)``
            * ``push(List[targets], List[tuple(target_id, attrname, new_value)], desc=None)``

        :param target: in all cases except for the last few (List[targets]), this is the target object of the change.

        The latter cases are for pushing a 'Delta Group' to the stack. A 'Delta Group' is simply a list of regular revision deltas (of arbitrary length, and can contain targets of mixed types) that will be undone/redone as a group: a single undo or redo operation will undo or redo every change recorded by the group deltas.

        For these Delta Group cases, the `target` argument to push should be a list or other flat iterable of all the changed targets in the group. If multiple changes in the group involve the same target, that target still only needs to appear once in the targets list. The change operations are given in the second argument, described below.


        :param args:
            For the forms of push that take a single `target` argument, this should either be three arguments in the order (attribute_name, previous_value, current_value); two arguments in the order (attribute_name, current_value); or a ``Delta`` object with the corresponding fields set.

            For the Delta Group forms, the second argument (the actual 'Delta Group') is another list composed of either:
            ``Delta`` objects describing the changes per target;
            4-tuples with the target_id, attribute name, previous value, and updated value all provided;
            or 3-tuples with only the target_id, attribute name, and new value provided. For this final situation, the previous value will be read from the target object before the change is made.
            Be sure that each target_id given has a corresponding target in the list passed for the `target` argument.

        :param str desc:
            Each overload also takes an optional `desc` argument which can be used to override the default text description of the change being made. Note that for Delta Groups, if `desc` is not provided, the default description will be taken from the type and changed attribute of the final target in the group.
        """

        sitem = self._push(*args, target=target, desc=desc)
        return self._appendAndDo(sitem)

    def _appendAndDo(self, stackitem):
        # adding a new change invalidates the redos
        self.redostack.clear()

        # but we add the new item right back on so that we can just call redo()...
        self.redostack.append(stackitem)
        # ... to actually apply the change
        return self.redo()

    @singledispatch_m
    def _push(self, *args, **kwargs):
        raise TypeError("Unrecognized type for arguments to push()")

    @_push.register(str)
    @_push.register(bytes)  # attribute name (raw change data)
    def _(self, attr, val1, val2=..., *, target, desc=None):
        target_type = type(target)
        target_id = self.getID(target, target_type)

        if target_id not in self._ids:
            self._start_tracking(target, target_id)

        if not desc:
            desc = self._descriptions[target_type][attr]

        if val2 is ...:
            # ... is our `None` placeholder, so that `None` can actually
            # be passed as a value. Thus, this means that val2 was not
            # specified, indicating that val1 is the new value and we should
            # pull the old value from the object itself.
            return self.stackitem(Delta(target_id, attr,
                                        self.get_attr(attr, target_id,
                                                      target_type),
                                        val1), desc)

        # otherwise assume val1 is oldval and val2 is newval
        return self.stackitem(Delta(target_id, attr,
                                    val1, val2), desc)

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

        if not (isinstance(target, (list, set))):
            # if this is not a list-like thing
            target = [target]  # ... make it so.

        targs_byid = {}
        # make an {id:target} dict
        for targ in target:
            targs_byid[self.getID(targ)] = targ

        dgroup = []
        ttype = None  # for access after loop
        attr = None  # for access after loop
        # for t,d in zip(target, delta_group):
        for d in delta_group:

            # preconstructed Deltas
            if isinstance(d, Delta):
                attr = d.attrname
                dgroup.append(d)
                t = targs_byid[d.id]
                ttype = type(t)

                if d.id not in self._ids:
                    self._start_tracking(t, d.id)


            # let's assume for now it's a mapping of form :
            # {'id' = ..., 'attrname' = ..., 'previous' = ..., 'current' = ...}
            # or
            # {'id'=..., 'attrname'=..., 'current'=...}
            elif isinstance(d, collections.Mapping):
                target_id = d['id']
                t = targs_byid[target_id]

                if target_id not in self._ids:
                    self._start_tracking(t, target_id)

                attr = d['attrname']
                ttype = type(t)
                dgroup.append(
                        Delta(target_id, attr,
                              d['previous'] if 'previous' in d
                              else self.get_attr(attr, target_id,
                                                 ttype),
                              d['current']))

            else:
                # uhhh... tuples? sure. tuples w/ raw change data.
                # (target_id, attrname, new_value) or
                # (target_id, attrname, old_value, new_value)
                # this isn't very type safe...but we'll try our best to make sure.
                # verify appropriate number of elements
                assert 2 < len(d) < 5
                target_id = d[0]
                t = targs_byid[target_id]
                if target_id not in self._ids:
                    self._start_tracking(t, target_id)

                ttype = type(t)
                attr  = d[1]
                prev  = d[2] if len(d) == 4 \
                        else self.get_attr(attr, target_id, ttype)
                curr  = d[-1]

                dgroup.append(Delta(target_id, attr, prev, curr))

        if not desc:
            # take default desc from type and attrname of last
            # item seen in change list
            desc = self._descriptions[ttype][attr]

        return self.stackitem(dgroup, desc)

    def _get_current_state(self, target_id):
        """Returns a dictionary of {attribute_name: value} pairs for the current value of each attribute of the target that matches one of the tracker's registered 'slots'."""
        return {s: self.get_attr(s, target_id)
                for s in self._slots[type(self[target_id])]}

    ##===============================================
    ## Undo/Redo
    ##===============================================

    def _do(self, steps=1):
        if steps < 0:
            steps, fromstack, tostack = min(abs(steps),
                    self.max_undos), self.undostack, self.redostack
        else:
            steps, fromstack, tostack = min(steps,
                    self.max_redos), self.redostack, self.undostack
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
                self.set_attr(prop, val, tid)

    def _accum_changes(self, fromstack, tostack, steps):
        """
        For `steps` iterations, this pops the last item off of `fromstack` and collects the change information stored inside, overwriting changes to the same attribute of the same target with the most recently encountered value. That information is stored and returned in an ordered dictionary keyed by the target id. This odict can be iterated through afterwards to apply the accumulated changes to the appropriate targets

        :param fromstack:
        :param tostack:
        :param steps:
        :return:
        """

        changed = collections.OrderedDict()  # {target: {attr: value, ...}, ...}

        for s in range(steps):
            sitem = fromstack.pop()
            delta, desc = sitem

            if not isinstance(delta, Delta):
                # assume it's a delta group
                for d in delta:  # type: Delta
                    tid = d.id
                    val = self._get_delta_field[id(fromstack)](d)
                    try:
                        changed[tid].update({d.attrname: val})
                    except KeyError:
                        changed[tid] = {d.attrname: val}

                # we always reverse the group before adding it to the other
                # stack so that 'going the other way' will iterate over
                # the group in the correct order.
                sitem = sitem._replace(delta=tuple(reversed(delta)))
            else:
                # whether we pull the previous or current
                # field from the Delta depends on whether this
                # is an undo or a redo, which we don't know due
                # to the genericn nature of this function. However,
                # we can use the id() of `fromstack` to query
                # a predefined mapping to determine the answer
                # for us.
                tid = delta.id
                val = self._get_delta_field[id(fromstack)](delta)
                try:
                    changed[tid].update({delta.attrname: val})
                except KeyError:
                    changed[tid] = {delta.attrname: val}

            # now push this stackitem to the other stack
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

    def revertItem(self, target, *, remove_after=False):
        """
        This is not technically an 'undo'; it does not walk the revision stack, but instead updates the target so that its current attributes match the values from its initial state. The `revert` itself is pushed to the revision stack and treated as a normal operation that can itself be subject to Undo/Redo.

        If, however, the optional, kw-only param `remove_after` is set to ``True``, all references to the object will be **removed** from the tracker after its attributes are set and will need to be re-added using ``pushNew()`` if it is decided to allow undo/redo of the object again.

        :param target:
        """
        # compare current target attributes to initial state,
        # and push a delta group of those which need changing
        # to match initial state.

        target_id = self.getID(target)

        istate = self._initialstates[target_id]
        dgroup = []
        for s in self._slots:
            currval = self.get_attr(s, target_id, type(target))
            if istate[s] != currval:
                dgroup.append(Delta(target_id, s, currval, istate[s]))

        if dgroup:
            self._appendAndDo(
                self.stackitem(dgroup, desc="Revert Item Changes"))

        if remove_after:
            self.untrack(target_id)

    def untrack(self, target):
        """Stop tracking the object with the specified id. All references to the object will be removed from the tracker and its revision history will be lost. The object itself will not be affected."""

        target_id = self.getID(target)

        for coll in self.__allmappings:
            with suppress(KeyError):
                del coll[target_id]

        # rotate through the deques and remove items w/ this id
        for d in [self.redostack, self.undostack]:
            for _ in range(len(d)):
                sitem = d.pop()  # type: RevisionTracker.stackitem

                if isinstance(sitem.delta, Delta):
                    if sitem.delta.id != target_id:
                        d.appendleft(sitem)

                else:  # delta group
                    newgroup = tuple(
                        filter(lambda g: g.id != target_id,
                               sitem.delta))

                    # if there's anything left
                    if len(newgroup) > 0:
                        if len(newgroup) < len(sitem.delta):
                            # if we filtered out some items
                            d.appendleft(
                                sitem._replace(delta=newgroup))
                        else:
                            # nothing was filtered, just put the original back on
                            d.appendleft(sitem)
