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

    return undo.RevisionTracker(ModEntry, *ModEntry._fields, attrsetter=testattrsetter)


def random_mock_modentry():
    me = mock.Mock(spec=ModEntry)
    me.enabled=random.randint(0,1)
    me.directory = random.sample(testwords, random.randint(4,7))
    me.name = " ".join(random.sample(me.directory, random.randint(1,4)))
    me.directory = " ".join(me.directory)
    me.modid = random.randrange(50000)
    _v1 = random.choice([""]*15+["v"]*5+["b"])
    _v2 = ".".join([str(random.randint(0,20)) for _ in range(random.randint(1,3))])
    me.version = _v1+_v2
    me.ordinal = random.randint(1,255)

    return me

def test_tracker_init(modentry, tracker:RevTrak):

    assert isinstance(modentry, ModEntry)

    assert tracker._type == modentry.__class__

    for a in ["enabled", "name", "modid", "version", "ordinal"] :
        assert a in tracker._slots
        assert tracker._descriptions[a] == "Change ".format(a)

    assert tracker.max_undos == 0
    assert tracker.max_redos == 0

    d=mock.Mock()
    d.previous = "previous"
    d.current = "current"

    assert tracker._get_delta_field[id(tracker.undostack)](d)=="previous"
    assert tracker._get_delta_field[id(tracker.redostack)](d)=="current"

    assert tracker._tracked == tracker._initialstates == tracker._cleanstates == {}


def test_push_new(modentry, tracker:RevTrak):
    tracker.pushNew(modentry, modentry.directory, "name", "Rather Boring Name")

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
    tracker.push(tid, "enabled", modentry.enabled, 0)
    tracker.push(tid, "ordinal", 100)
    tracker.push(tid, undo.Delta("version", modentry.version, "v2.0"))

    me = tracker[modentry.directory] #type:ModEntry
    assert me.enabled==0
    assert me.ordinal == 100
    assert me.version == "v2.0"
    assert me.name == "Rather Boring Name"
    assert me.modid == modentry.modid # unchanged

    assert tracker.max_redos == 0
    assert tracker.max_undos == 4


def test_push_group(modentry, tracker:RevTrak):
    current = tracker[modentry.directory]

    dgroup = []
    for change in [("name",
                    current.name,
                    "Super Awesome Name"),
                   ("version",
                    current.version,
                    "vWhat.0"),
                   ("ordinal",
                    current.ordinal,
                    255)]:
        dgroup.append(undo.Delta._make(change))

    assert len(dgroup) == 3
    assert all(isinstance(d, undo.Delta) for d in dgroup)

    tracker.push(current.directory, dgroup)

    assert tracker.max_redos == 0
    assert tracker.max_undos == 5

    check_obj_state(modentry.directory, tracker, 15602, 0, 255, "vWhat.0", "Super Awesome Name")

def test_undo(modentry, tracker):

    check_obj_state(modentry.directory, tracker, 15602, 0, 255, "vWhat.0", "Super Awesome Name")

    assert tracker.undo(5)

    # should be back to original values
    check_obj_state(modentry.directory, tracker, modentry.modid, modentry.enabled, modentry.ordinal, modentry.version, modentry.name)


@pytest.fixture(scope='module')
def tracker2():
    return undo.RevisionTracker(ModEntry, *ModEntry._fields)

@pytest.fixture(scope='module')
def randentries():
    entries = [random_mock_modentry() for _ in range(5)]

    for e in entries: assert isinstance(e, ModEntry)
    return entries

def test_track_multiple(randentries, tracker2):

    tracker = tracker2

    entries = randentries

    changes = [['modid', lambda v: v+111],
               ['name', lambda v: v+"morename"],
               ['version', lambda v: 'vABC.D'],
               ['enabled', lambda v: int(not v)],
               ['ordinal', lambda v: v+101,]]

    ovals = {}
    for e,c in zip(entries, changes):
        ovals[e.directory] = {c[0]: getattr(e, c[0])}
        tracker.pushNew(e, e.directory, c[0], c[1](getattr(e, c[0])))

    assert tracker.max_redos == 0
    assert tracker.max_undos == 5

    assert tracker[entries[0].directory] is entries[0]

    assert entries[0].modid == ovals[entries[0].directory]['modid'] + 111
    assert entries[1].name == ovals[entries[1].directory]['name'] + 'morename'
    assert entries[2].version == 'vABC.D'
    assert entries[3].enabled == int(not ovals[entries[3].directory]['enabled'])
    assert entries[4].ordinal == ovals[entries[4].directory]['ordinal']+101

    tracker.undo()

    assert tracker.max_redos == 1
    assert tracker.max_undos == 4
    assert entries[4].ordinal == ovals[entries[4].directory]['ordinal']

    tracker.undo(2)
    assert tracker.max_redos == 3
    assert tracker.max_undos == 2

    assert entries[3].enabled == ovals[entries[3].directory]['enabled']
    assert entries[2].version == ovals[entries[2].directory]['version']

    tracker.redo()
    assert tracker.max_redos == 2
    assert tracker.max_undos == 3
    assert entries[2].version == 'vABC.D'


def test_save(randentries, tracker2:RevTrak):
    entries, tracker = randentries, tracker2


    assert tracker.steps_to_revert == 3 == tracker.max_undos
    tracker.save()

    assert tracker.steps_to_revert == 0
    assert tracker.max_undos == 3





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




testwords=[ "Dawnguard", "HearthFires", "Unofficial", "Skyrim", "Legendary", "Edition", "Patch", "Clothing", "and", "Clutter", "Fixes", "Cutting", "Room", "Floor", "Guard", "Dialogue", "Overhaul", "Invisibility", "Eyes", "Fix", "Weapons", "and", "Armor", "Fixes", "Complete", "Crafting", "Overhaul", "Remade", "Realistic", "Water", "Two" ,"Content","Addon", "Explosive", "Bolts", "Visualized" , "Animated", "Weapon", "Enchants" , "Deadly", "Spell", "Impacts" , "dD", "-", "Enhanced", "Blood", "Main", "Book", "Covers", "Skyrim", "Improved", "Combat", "Sounds", "v2.2", "Bring", "Out", "Your", "Dead", "-","Legendary", "Edition", "The", "Choice", "Is", "Yours" , "The", "Paarthurnax", "Dilemma", "Better", "Quest", "Objectives",]