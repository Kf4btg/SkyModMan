from skymodman.managers import undo
from skymodman.managers.undo import RevisionTracker as RevTrak
from skymodman import ModEntry

import pytest
import random
from unittest import mock

def mock_mod_entry():
    me = mock.Mock(spec=ModEntry)
    me.enabled = 1
    me.name = "Mod Name"
    me.directory = "Mod Name HD v1_01HDWHOA"
    me.modid = 15602
    me.version = "v1.0.1"
    me.ordinal = 42

    return me

@pytest.fixture(scope='module')
def modentry():
    return ModEntry(enabled=1, name="Mod Name", modid = 15602, version = "v1.0.1", directory = "Mod Name HD v1_01HDWHOA", ordinal = 42)

@pytest.fixture
def new_modentry():
    return ModEntry(enabled=1, name="Mod Name",
                    modid=15602, version="v1.0.1",
                    directory="Mod Name HD v1_01HDWHOA",
                    ordinal=42)

@pytest.fixture(scope='module')
def key():
    me = mock_mod_entry()
    return me.directory

@pytest.fixture(scope='module')
def tracker():
    testattrsetter = lambda m, n, v: m._replace(**{n: v})

    return undo.RevisionTracker(ModEntry, lambda e: e.directory, *ModEntry._fields, attrsetter=testattrsetter)
    # return undo.RevisionTracker()

class Thing:pass

def random_mock_modentry():
    # me = mock.MagicMock(spec=ModEntry, instance=True)
    # me = mock.Mock()
    me = Thing()
    me.enabled=random.randint(0,1)
    me.directory = random.sample(testwords, random.randint(4,7))
    me.name = " ".join(random.sample(me.directory, random.randint(1,4)))
    me.directory = " ".join(me.directory)
    me.modid = random.randrange(50000)
    _v1 = random.choice([""]*15+["v"]*5+["b"])
    _v2 = ".".join([str(random.randint(0,20)) for _ in range(random.randint(1,3))])
    me.version = _v1+_v2
    me.ordinal = random.randint(1,255)

    return ModEntry(me.enabled, me.name, me.modid, me.version, me.directory, me.ordinal)

def test_tracker_init_noargs():
    t = RevTrak()

    assert t._savepoint   == \
    len(t._descriptions)  == \
    len(t._slots)         == \
    len(t._keyfuncs)      == \
    len(t.undostack)      == \
    len(t.redostack)      == \
    len(t._tracked)       == \
    len(t._initialstates) == \
    t.max_redos           == \
    t.max_undos           == \
    t.num_tracked         == \
    t.steps_to_revert     == 0

    assert not t.can_redo
    assert not t.can_undo

    with pytest.raises(KeyError):
        t[0]

    assert t.isclean

def test_tracker_init_withargs(new_modentry):

    t = undo.RevisionTracker(ModEntry, lambda e: e.directory, *ModEntry._fields)

    assert ModEntry in t._types

    for a in ["enabled", "name", "modid", "version", "ordinal"]:
        assert a in t._slots[ModEntry]
        assert t._descriptions[ModEntry][a] == "Change {}".format(a)

    # test key function
    assert t.getID(new_modentry) == "Mod Name HD v1_01HDWHOA"


def test_tracker_init_description():
    t = undo.RevisionTracker(ModEntry, lambda e: e.directory, *ModEntry._fields, descriptions={
        "enabled": "Turning of the Onoroff",
        "ordinal": "Make the When Different",
        "name": "Switchup whatcha call me"})

    for s,d in t._descriptions[ModEntry].items():
        if s=="enabled":
            assert d=="Turning of the Onoroff"
        elif s=="ordinal":
            assert d=="Make the When Different"
        elif s=="name":
            assert d=="Switchup whatcha call me"
        else:
            assert d=="Change {}".format(s)



def test_tracker_init(modentry, tracker:RevTrak):

    assert isinstance(modentry, ModEntry)

    metype = modentry.__class__
    assert metype == ModEntry
    assert metype in tracker._types


    for a in ["enabled", "name", "modid", "version", "ordinal"] :
        assert a in tracker._slots[metype]
        assert tracker._descriptions[metype][a] == "Change {}".format(a)

    assert tracker.max_undos == 0
    assert tracker.max_redos == 0

    d=mock.Mock()
    d.previous = "previous"
    d.current = "current"

    assert tracker._get_delta_field[id(tracker.undostack)](d)=="previous"
    assert tracker._get_delta_field[id(tracker.redostack)](d)=="current"

    assert tracker._tracked == tracker._initialstates == tracker._cleanstates == {}

def test_register_desc(tracker:RevTrak):
    for a, d in {"enabled": "Turning of the Onoroff",
        "ordinal": "Make the When Different",
        "name": "Switchup whatcha call me"}.items():
        tracker.registerDescription(ModEntry, a, d)

    for a, d in tracker._descriptions[ModEntry].items():
        if a == "enabled":
            assert d == "Turning of the Onoroff"
        elif a == "ordinal":
            assert d == "Make the When Different"
        elif a == "name":
            assert d == "Switchup whatcha call me"
        else:
            assert d == "Change {}".format(a)


def test_push_new(modentry, tracker:RevTrak):
    tracker.push(modentry, "name", "Rather Boring Name")

    me = tracker[modentry.directory] #type:ModEntry

    assert me.ordinal == modentry.ordinal
    assert me.enabled == modentry.enabled
    assert me.modid == modentry.modid
    assert me.version == modentry.version

    assert me.name != modentry.name
    assert me.name=="Rather Boring Name"

    assert tracker.max_redos == 0
    assert tracker.max_undos == 1


def test_push_more(modentry, tracker:RevTrak):
    tid = modentry.directory

    # test different push() overloads
    tracker.push(modentry, "enabled", modentry.enabled, 0)
    tracker.push(modentry, "ordinal", 100)
    tracker.push(modentry, undo.Delta(tid, "version", modentry.version, "v2.0"))


    me = tracker[modentry.directory] #type:ModEntry
    assert me.enabled==0
    assert me.ordinal == 100
    assert me.version == "v2.0"
    assert me.name == "Rather Boring Name"
    assert me.modid == modentry.modid # unchanged

    assert len(tracker._types) == 1

    assert tracker.max_redos == 0
    assert tracker.max_undos == 4


dgroup_params = [("name", "Super Awesome Name"),
                 ("version", "vWhat.0"),
                 ("ordinal", 255)]


def test_push_group(modentry, tracker:RevTrak):
    current = tracker[modentry.directory]

    # dict
    dgroup = [dgroup_dict(id=modentry.directory, attrname=p[0], prev=getattr(current, p[0]), curr=p[1]) for p in dgroup_params ]
    assert len(dgroup) == 3
    assert all(isinstance(d, dict) for d in dgroup)
    tracker.push(current, dgroup)


    assert tracker.max_redos == 0
    assert tracker.max_undos == 5

    check_obj_state(modentry.directory, tracker, 15602, 0, 255, "vWhat.0", "Super Awesome Name")

    tracker.undo(1)
    check_obj_state(modentry.directory, tracker, 15602, 0, 100, "v2.0", "Rather Boring Name")

    assert tracker.max_redos == 1
    assert tracker.max_undos == 4

    # dict no prev
    dgroup = [dgroup_dict(id=modentry.directory, attrname=p[0], curr=p[1]) for p in
              dgroup_params]
    tracker.push(current, dgroup)
    check_obj_state(modentry.directory, tracker, 15602, 0, 255, "vWhat.0", "Super Awesome Name")
    assert tracker.max_redos == 0
    assert tracker.max_undos == 5

    assert tracker.undo()
    check_obj_state(modentry.directory, tracker, 15602, 0, 100, "v2.0", "Rather Boring Name")

    ## tuple no prev
    dgroup = [dgroup_tuple(id=modentry.directory, attrname=p[0], curr=p[1]) for p in
              dgroup_params]
    tracker.push(current, dgroup)
    check_obj_state(modentry.directory, tracker, 15602, 0, 255, "vWhat.0", "Super Awesome Name")

    assert tracker.undo()
    check_obj_state(modentry.directory, tracker, 15602, 0, 100, "v2.0", "Rather Boring Name")

    ## tuple
    dgroup = [dgroup_tuple(id=modentry.directory, attrname=p[0], prev=getattr(current, p[0]), curr=p[1]) for p in dgroup_params ]
    tracker.push(current, dgroup)
    check_obj_state(modentry.directory, tracker, 15602, 0, 255, "vWhat.0", "Super Awesome Name")


    assert tracker.undo()
    check_obj_state(modentry.directory, tracker, 15602, 0, 100, "v2.0", "Rather Boring Name")

    ## delta
    dgroup = [dgroup_delta(id=modentry.directory, attrname=p[0], prev=getattr(current, p[0]), curr=p[1]) for p in
              dgroup_params]
    tracker.push(current, dgroup)
    check_obj_state(modentry.directory, tracker, 15602, 0, 255, "vWhat.0", "Super Awesome Name")

    assert tracker.max_redos == 0
    assert tracker.max_undos == 5







    # for change in [
    #     ("name", current.name, "Super Awesome Name"),
    #     ("version", current.version, "vWhat.0"),
    #     ("ordinal", current.ordinal, 255)]:
    #     dgroup.append((modentry.directory, ) + change)

    # assert len(dgroup) == 3
    # assert all(isinstance(d, undo.Delta) for d in dgroup)

    # tracker.push(current, dgroup)


    # check_obj_state(modentry.directory, tracker, 15602, 0, 255, "vWhat.0", "Super Awesome Name")

def test_undo(modentry, tracker):

    check_obj_state(modentry.directory, tracker, 15602, 0, 255, "vWhat.0", "Super Awesome Name")

    assert tracker.undo(5)

    # should be back to original values
    check_obj_state(modentry.directory, tracker, modentry.modid, modentry.enabled, modentry.ordinal, modentry.version, modentry.name)


@pytest.fixture(scope='module')
def tracker2():
    track = undo.RevisionTracker()
    testattrsetter = lambda m, n, v: m._replace(**{n: v})

    track.registerType(type(random_mock_modentry()), lambda v: v.directory, *ModEntry._fields, attrsetter=testattrsetter )

    return track

@pytest.fixture(scope='module')
def randentries():
    entries = [random_mock_modentry() for _ in range(5)]

    for e in entries: assert isinstance(e, ModEntry)
    return entries



def test_track_multiple(randentries, tracker2:RevTrak):

    tracker = tracker2

    entries = randentries

    changes = [['modid', lambda v: v+111],
               ['name', lambda v: v+"morename"],
               ['version', lambda v: 'vABC.D'],
               ['enabled', lambda v: int(not v)],
               ['ordinal', lambda v: v+101,]]

    ovals = {}
    for entry, change in zip(entries, changes):
        attr_ = change[0]
        newval_ = change[1](getattr(entry, attr_))

        ovals[entry.directory] = {attr_: getattr(entry, attr_)} # save original value
        tracker.push(entry, attr_, newval_)

    assert tracker.max_redos == 0
    assert tracker.max_undos == 5

    modif = lambda i: tracker[entries[i].directory]

    assert modif(0).modid == ovals[entries[0].directory]['modid'] + 111
    assert modif(1).name == ovals[entries[1].directory]['name'] + 'morename'
    assert modif(2).version == 'vABC.D'
    assert modif(3).enabled == int(not ovals[entries[3].directory]['enabled'])
    assert modif(4).ordinal == ovals[entries[4].directory]['ordinal']+101

    tracker.undo()

    assert tracker.max_redos == 1
    assert tracker.max_undos == 4
    assert modif(4).ordinal == ovals[entries[4].directory]['ordinal']

    tracker.undo(2)
    assert tracker.max_redos == 3
    assert tracker.max_undos == 2

    assert modif(3).enabled == ovals[entries[3].directory]['enabled']
    assert modif(2).version == ovals[entries[2].directory]['version']

    tracker.redo()
    assert tracker.max_redos == 2
    assert tracker.max_undos == 3
    assert modif(2).version == 'vABC.D'


def test_save(randentries, tracker2:RevTrak):
    entries, tracker = randentries, tracker2


    assert tracker.steps_to_revert == 3 == tracker.max_undos
    tracker.save()

    assert tracker.steps_to_revert == 0
    assert tracker.max_undos == 3

    assert tracker.isclean

def test_truncate_redos(tracker2:RevTrak):
    re = random_mock_modentry()
    tracker = tracker2


    assert tracker.max_redos == 2
    tracker.push(re, 'ordinal', re.ordinal*2)

    assert tracker.max_redos == 0
    assert not tracker.isclean

    assert tracker.max_undos == 4
    assert tracker.total_stack_size == 4
    assert tracker.num_tracked == 6





##===============================================
## Helpers
##===============================================
def check_obj_state(key, _tracker, x_modid, x_enabled, x_ord, x_version, x_name):
    curr_obj = _tracker._tracked[key]
    assert curr_obj.modid == x_modid
    assert curr_obj.enabled == x_enabled
    assert curr_obj.ordinal == x_ord
    assert curr_obj.version == x_version
    assert curr_obj.name == x_name

def dgroup_delta(*, id, attrname, prev, curr):
    return undo.Delta(id, attrname, prev, curr)

def dgroup_dict(*, id, attrname, curr, prev=None):
    d = {"id": id, "attrname": attrname, "current": curr}
    if prev:
        d["previous"] = prev
    return d

def dgroup_tuple(*, id, attrname, curr, prev=None):
    if prev:
        return id, attrname, prev, curr
    else:
        return id, attrname, curr





testwords=[ "Dawnguard", "HearthFires", "Unofficial", "Skyrim", "Legendary", "Edition", "Patch", "Clothing", "and", "Clutter", "Fixes", "Cutting", "Room", "Floor", "Guard", "Dialogue", "Overhaul", "Invisibility", "Eyes", "Fix", "Weapons", "and", "Armor", "Fixes", "Complete", "Crafting", "Overhaul", "Remade", "Realistic", "Water", "Two" ,"Content","Addon", "Explosive", "Bolts", "Visualized" , "Animated", "Weapon", "Enchants" , "Deadly", "Spell", "Impacts" , "dD", "-", "Enhanced", "Blood", "Main", "Book", "Covers", "Skyrim", "Improved", "Combat", "Sounds", "v2.2", "Bring", "Out", "Your", "Dead", "-","Legendary", "Edition", "The", "Choice", "Is", "Yours" , "The", "Paarthurnax", "Dilemma", "Better", "Quest", "Objectives",]