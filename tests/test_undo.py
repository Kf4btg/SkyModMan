from skymodman.managers import undo
from skymodman import ModEntry

import pytest
import random
from unittest import mock

@pytest.fixture()
def mock_mod_entry():
    me = mock.Mock(spec=ModEntry)
    me.enabled = 1
    me.name = "Mod Name"
    me.directory = "Mod Name HD v1_01HDWHOA"
    me.modid = 15602
    me.version = "v1.0.1"
    me.ordinal = 42

    return me

# @pytest.fixture(scope='module')
# def ref_mme():
#     "Reference mock modentry"
#     me = mock.Mock(spec=ModEntry)
#     me.enabled = 1
#     me.name = "Mod Name"
#     me.directory = "Mod Name HD v1_01HDWHOA"
#     me.modid = 15602
#     me.version = "v1.0.1"
#     me.ordinal = 42
#
#     return me

@pytest.fixture(scope='module')
def key():
    me = mock_mod_entry()
    return me.directory


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


@pytest.fixture(scope='module')
def tracker():
    odt = undo.ObjectDiffTracker(ModEntry, "enabled", "name", "modid", "version", "ordinal")
    return odt


def test_new_tracker(tracker):
    assert tracker._type == ModEntry
    for a in ["enabled", "name", "modid", "version", "ordinal"]:
        assert a in tracker._slots

    with pytest.raises(KeyError):
        assert tracker.stack_size(1)

    assert not tracker._tracked
    assert not tracker._revisions
    assert tracker._getattr is getattr
    assert tracker._setattr is setattr
    assert not tracker._revcur
    assert not tracker._savecur


def test_add_tracked(mock_mod_entry, tracker):

    # me = random_mock_modentry()
    me = mock_mod_entry
    new_name = "Rather Boring Name"
    old_name = me.name

    tracker.addNew(me, me.directory, "name", me.name, new_name )

    assert tracker._tracked[me.directory] is me

    assert tracker.stack_size(me.directory) == 1
    assert tracker.max_undos(me.directory)  == 1
    assert tracker.max_redos(me.directory)  == 0

    assert tracker._savecur[me.directory] < 0
    assert not tracker.is_clean(me.directory)

    assert tracker._revisions[me.directory][0].attrname=="name"
    assert tracker._revisions[me.directory][0].previous==old_name
    assert tracker._revisions[me.directory][0].current==new_name

    # check that it actually changed this object
    assert tracker._revisions[me.directory][0].current==me.name
    for s in tracker._slots:
        assert getattr(tracker._tracked[me.directory], s) == \
               getattr(me, s)




def test_more_revisions(key, mock_mod_entry, tracker:undo.ObjectDiffTracker):

    me  = mock_mod_entry

    tracker.add(key, "enabled", me.enabled, 0)
    tracker.add(key, "ordinal", me.ordinal, 100)
    tracker.add(key, undo.Delta("version", me.version, "v2.0"))

    assert tracker.max_undos(key) == tracker.stack_size(key) == 4
    assert tracker.max_redos(key) == 0



def test_set_savepoint(key, tracker: undo.ObjectDiffTracker):

    assert tracker._savecur[key]==-1
    assert not tracker.is_clean(key)
    assert tracker._steps_to_revert(key) == 4

    # cheat by moving cursor artificially
    tracker._savecur[key] = 2
    assert not tracker.is_clean(key)
    assert tracker._steps_to_revert(key) == 1
    # these invariant wrt savepoint
    assert tracker.max_undos(key) == tracker.stack_size(key) == 4
    assert tracker.max_redos(key) == 0

    # current end of list
    tracker.save()
    assert tracker._savecur[key] == 3
    assert tracker._steps_to_revert(key) == 0
    assert tracker.is_clean(key)

# before testing: (3, True, 0, 4, 0), savepoint == 3
cursor_change_params = [(2,False,-1,3,1),
                        (1,False,-2,2,2),
                        (0,False,-3,1,3),
                        (3, True, 0,4,0) # reset to pre-test state
                        ]

@pytest.mark.parametrize("curpos, x_isclean, x_s2r, x_maxundo, x_maxredo", cursor_change_params)
def test_cursor_change(tracker: undo.ObjectDiffTracker,
                       curpos, x_isclean, x_s2r,
                       x_maxundo, x_maxredo):

    key = mock_mod_entry().directory

    # artificially change revision cursor
    tracker._revcur[key]=curpos
    assert tracker.is_clean(key) == x_isclean
    assert tracker._steps_to_revert(key) == x_s2r

    assert tracker.max_undos(key) == x_maxundo
    assert tracker.max_redos(key) == x_maxredo


#version <- ord <- enabled <- name
mrvtestparams = [(3,
                  15602,       # original
                  0,           # modified
                  100,         # modified
                  "v2.0",      # modified
                  "Rather Boring Name" # modified
                  ),
                 (2,15602,0,100,"v1.0.1","Rather Boring Name"),
                 (1,15602,0,42,"v1.0.1","Rather Boring Name"),
                 (0,15602,1,42,"v1.0.1","Rather Boring Name"),
                 (3,15602,0,100,"v2.0","Rather Boring Name"),
                 ]

tracker_stat_params = [(3, 4, 4, 0, 1, False),
                       (2, 4, 3, 1, 0, True),
                       (1, 4, 2, 2, -1, False),
                       (0, 4, 1, 3, -2, False)
                       ]


def get_mrv(odt):
    me = mock_mod_entry()

    mrv = odt.most_recent_values(me.directory)
    return {
        s: mrv[s] if s in mrv else getattr(me, s) for s in odt._slots
        }

@pytest.mark.parametrize("curpos, x_modid, x_enabled, x_ord, x_version, x_name", mrvtestparams)
def test_most_recent_vals(key,
                          tracker:undo.ObjectDiffTracker,
                          curpos, x_modid, x_enabled,
                          x_ord, x_version, x_name):

     #artificially change cursor position
    tracker._revcur[key] = curpos

    # mrv = tracker.most_recent_values(key)
    currstate = get_mrv(tracker)

    assert currstate["modid"] == x_modid
    assert currstate["enabled"] == x_enabled
    assert currstate["ordinal"] == x_ord
    assert currstate["version"] == x_version
    assert currstate["name"] == x_name


def check_obj_state(key, _tracker, x_modid, x_enabled, x_ord, x_version, x_name):
    curr_obj = _tracker._tracked[key]
    assert curr_obj.modid == x_modid
    assert curr_obj.enabled == x_enabled
    assert curr_obj.ordinal == x_ord
    assert curr_obj.version == x_version
    assert curr_obj.name == x_name


def check_tracker_stats(key, _tracker, x_cur, x_stacksize, x_maxundo, x_maxredo, x_s2r, x_isclean):
    assert _tracker._revcur[key] == x_cur
    assert _tracker.stack_size(key) == x_stacksize
    assert _tracker.max_undos(key) == x_maxundo
    assert _tracker.max_redos(key) == x_maxredo
    assert _tracker._steps_to_revert(key) == x_s2r
    assert _tracker.is_clean(key) == x_isclean


def test_undo(key, tracker:undo.ObjectDiffTracker):

    # cheat save cursor to 2
    tracker._savecur[key] = 2

    # steps==0 case; noop, returns False
    assert not tracker.undo(key,0)

    # current setup
    check_tracker_stats(key,tracker,3,4,4,0,1,False)

    # test that all previous changes were actually
    # made to the tracked object
    check_obj_state(key, tracker, 15602,0,100,"v2.0","Rather Boring Name")

    assert tracker.undo(key) #default 1 step

    #after undo
    check_tracker_stats(key,tracker,2,4,3,1,0,True)

    check_obj_state(key, tracker, 15602, 0, 100,
                    "v1.0.1", #UNDO
                    "Rather Boring Name")



def test_redo(key, tracker:undo.ObjectDiffTracker):

    # steps==0 case; noop, returns False
    assert not tracker.redo(key, 0)

    # should still be clean from last time
    assert tracker.is_clean(key)

    assert tracker.redo(key) #default 1 step

    check_obj_state(key, tracker, 15602, 0, 100,
                    "v2.0", #REDO
                    "Rather Boring Name")

    check_tracker_stats(key, tracker, 3, 4, 4, 0, 1, False)


def test_seq_undo(key, tracker:undo.ObjectDiffTracker):

        # test multiple undo steps in a row

    assert tracker.undo(key) #cur :: 3->2
    assert tracker.undo(key) #cur :: 2->1
    assert tracker.undo(key) #cur :: 1->0

    check_tracker_stats(key, tracker, *tracker_stat_params[3])

    check_obj_state(key, tracker, *mrvtestparams[3][1:])

def test_seq_redo(key, tracker:undo.ObjectDiffTracker):
       # test multiple redo steps in a row

    assert tracker.redo(key)  # cur :: 0->1
    assert tracker.redo(key)  # cur :: 1->2

    check_tracker_stats(key, tracker, 2, 4, 3, 1, 0, True)

    check_obj_state(key, tracker, 15602,0,100,"v1.0.1","Rather Boring Name")

    assert tracker.redo(key) # 2->3

def test_cannot_redo(key, tracker):

    assert tracker.stack_size(key) \
           == tracker.max_undos(key) \
           == tracker._revcur[key]+1

    assert tracker.max_redos(key) == 0

    assert not tracker.redo(key)

    assert not tracker.redo(key, 65536)


def test_multi_undo(key, tracker:undo.ObjectDiffTracker):
    # test undo multiple steps at once

    assert tracker.undo(key, 3) # cur:: 3->0

    check_tracker_stats(key, tracker, 0, 4, 1, 3, -2, False)

    check_obj_state(key, tracker, 15602,1,42,"v1.0.1","Rather Boring Name")

    assert tracker.redo(key, 2)  # cur:: 0->2
    check_tracker_stats(key, tracker, 2, 4, 3, 1, 0, True)

    check_obj_state(key, tracker, 15602, 0, 100, "v1.0.1", "Rather Boring Name")


def test_save(key, tracker:undo.ObjectDiffTracker):

    assert tracker.is_clean(key)
    assert tracker._revcur[key] == 2
    assert tracker._savecur[key] == 2


    assert tracker.undo(key)

    assert not tracker.is_clean(key)
    assert tracker._revcur[key] == 1
    assert tracker._savecur[key] == 2


    tracker.save()

    assert tracker.is_clean(key)
    assert tracker._revcur[key] == 1
    assert tracker._savecur[key] == 1


    assert tracker.redo(key, 2)

    assert not tracker.is_clean(key)
    assert tracker._revcur[key] == 3
    assert tracker._savecur[key] == 1

    tracker.save()
    assert tracker.is_clean(key)
    assert tracker._revcur[key] == 3
    assert tracker._savecur[key] == 3

def test_truncate_stack(key,tracker:undo.ObjectDiffTracker):

    tracker.undo(2) # back 2: c==1

    assert tracker.max_undos(key)==2
    assert tracker.max_redos(key)==2




testwords=[ "Dawnguard", "HearthFires", "Unofficial", "Skyrim", "Legendary", "Edition", "Patch", "Clothing", "and", "Clutter", "Fixes", "Cutting", "Room", "Floor", "Guard", "Dialogue", "Overhaul", "Invisibility", "Eyes", "Fix", "Weapons", "and", "Armor", "Fixes", "Complete", "Crafting", "Overhaul", "Remade", "Realistic", "Water", "Two" ,"Content","Addon", "Explosive", "Bolts", "Visualized" , "Animated", "Weapon", "Enchants" , "Deadly", "Spell", "Impacts" , "dD", "-", "Enhanced", "Blood", "Main", "Book", "Covers", "Skyrim", "Improved", "Combat", "Sounds", "v2.2", "Bring", "Out", "Your", "Dead", "-","Legendary", "Edition", "The", "Choice", "Is", "Yours" , "The", "Paarthurnax", "Dilemma", "Better", "Quest", "Objectives",]
# "aMidianBorn",


# if __name__ == '__main__':
#     for i in range(5):
#         print (random_mock_modentry())