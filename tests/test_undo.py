from skymodman.managers import undo
from skymodman import ModEntry

import pytest
import random
from unittest import mock

@pytest.fixture()
def mock_mod_entry():
    me = mock.Mock(spec=ModEntry)
    me.enabled = True
    me.name = "Mod Name"
    me.directory = "Mod Name HD v1_01HDWHOA"
    me.modid = 15602
    me.version = "v1.0.1"
    me.ordinal = 23
    return me

# class Thing:pass

def random_mock_modentry():
    # random.shuffle(testwords)
    me = mock.Mock(spec=ModEntry)
    # me = Thing()
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
    # return ModEntry(me.enabled, me.name, me.modid, me.version, me.directory, me.ordinal)



def test_tracker_init(mock_mod_entry):
    me = mock_mod_entry

    assert isinstance(me, ModEntry)

    odt = undo.ObjectDiffTracker(me.__class__, "enabled", "name", "modid", "version", "ordinal")

    assert odt._type == ModEntry

    for a in ["enabled", "name", "modid", "version", "ordinal"] :
        assert a in odt._slots


@pytest.fixture
def tracker():
    me = mock.Mock(spec=ModEntry)
    odt = undo.ObjectDiffTracker(me.__class__, "enabled", "name", "modid", "version", "ordinal")
    assert odt._type == ModEntry
    for a in ["enabled", "name", "modid", "version", "ordinal"]:
        assert a in odt._slots
    return odt


def test_new_tracker(tracker):

    with pytest.raises(KeyError):
        assert tracker.stack_size(1)

    assert not tracker._tracked
    assert not tracker._revisions
    assert not tracker._callback
    assert not tracker._revptr


def test_add_tracked(tracker):

    me = random_mock_modentry()
    new_name = "Rather Boring Name"

    tracker.addNew(me, me.directory, "name", me.name, new_name )


    assert tracker._savepoint < 0
    assert tracker.stack_size(me.directory) == 1
    assert tracker.max_undos(me.directory)  == 1
    assert tracker.max_redos(me.directory)  == 0
    assert tracker.is_clean(me.directory)   == False

    assert tracker._revisions[me.directory][0].attrname=="name"
    assert tracker._revisions[me.directory][0].previous==me.name
    assert tracker._revisions[me.directory][0].current==new_name



testwords=[ "Dawnguard", "HearthFires", "Unofficial", "Skyrim", "Legendary", "Edition", "Patch", "Clothing", "and", "Clutter", "Fixes", "Cutting", "Room", "Floor", "Guard", "Dialogue", "Overhaul","Invisibility", "Eyes", "Fix", "Weapons", "and", "Armor", "Fixes", "Complete", "Crafting", "Overhaul", "Remade" , "Realistic","Water","Two" ,"Content", "Addon" , "Explosive","Bolts","Visualized" , "Animated", "Weapon", "Enchants" , "Deadly","Spell","Impacts" , "dD", "-", "Enhanced", "Blood", "Main" , "Book", "Covers", "Skyrim" , "Improved", "Combat", "Sounds", "v2.2" , "Bring", "Out", "Your", "Dead", "-","Legendary", "Edition", "The","Choice","Is","Yours" , "The", "Paarthurnax", "Dilemma" , "Better", "Quest", "Objectives" ,]
# "aMidianBorn",


# if __name__ == '__main__':
#     for i in range(5):
#         print (random_mock_modentry())