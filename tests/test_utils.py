# from skymodman.utils import allcombos, reduceall
from skymodman.utils.fsutils import check_path

import pytest

testpaths = [("", False), (".", True), ("/", True),
             ("/home/../home/../", True), ("~", False),
             ("~/Desktop", False), ("/nadadontexist", False),
             ("/..", True)]

testpaths2 = [("", False), (".", True), ("~", True),
              ("~/../", True), ("~/Desktop", True),
              ("~/~", False), ("~/notathingnotexistinghere", False),
              ("~/../~", False)]

idfn = lambda v: str(v)

@pytest.mark.parametrize("path, expect", testpaths, ids=idfn)
def test_checkpath_noexpand(path, expect):
    assert bool(check_path(path)) == expect


@pytest.mark.parametrize("path,expect", testpaths2, ids=idfn)
def test_checkpath_expand(path, expect):
    assert bool(check_path(path, True)) == expect


# def test_allcombos():
#
#     it = ['a','b','c']
#     exp_res = [('a',), ('b',), ('c',),
#                ('a','b'), ('a','c'),
#                ('b','c'), ('a','b','c')]
#
#     assert [t for t in allcombos(it)] == exp_res
#
#     assert [t for t in allcombos('abc')] == exp_res
#
# def test_reduceall():
#     import operator
#
#     op = operator.mul
#     lol = [(1, 2), (2, 3, 4), (3, 4, 5, 6)]
#     expres = [2, 24, 360]
#
#     assert list(reduceall(op, lol)) == expres
