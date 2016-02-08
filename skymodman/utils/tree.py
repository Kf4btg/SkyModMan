from collections import defaultdict
import json

def Tree():
    """Return an instance of an autovivifying Tree"""
    # return defaultdict(Tree)
    return AutoTree(Tree)

def tree_insert(tree, key_list, value=None, leaf_list_key="_files"):
    """
    Given an ordered list of key names, descend down the tree by key, creating child branches (aka tree-levels, aka sub-dictionaries, aka child-trees,...) as needed.

    A "tree" is defined as a normal python dict modified to create new empty dicts (trees) if attempting to retrieve a key which does not exist (a process known as autovivification). Any object that meets that condition can be passed for `tree`. At any level of the tree, accessing items on that level should behave as per normal dictionary function.

    If `value` is None, the final element of the created branch will be an empty tree (unless the node specified by the final key already existed, in which case it will be unaltered and this method was a noop).

    If `value` is non-None, then upon reaching or creating the final branch component, if no key with the value given by `leaf_list_key` exists as direct child (i.e., can be accessed as::

             tree[...][key_list[-1]][leaf_list_key]

    using the components from `key_list`), then an empty list will be created under that key value and value placed into it.  If the key `leaf_list_key` already exists, then it will be assumed that the list has already been created and contains elements, so an attempt to append `value` to that list will be made. Should the attempt fail, exceptions will be raised. Thus it is important to choose a value for `leaf_list_key` that will not conflict with the keys of any child trees on the same branch level.

    .. note:: This method was designed with the assumption that all keys are strings and no complex types (e.g. lists, dicts, tuples, etc.) will be stored as values. Violating these assumptions may result in undefined (read: broken) behavior.


    :param tree: a dict that supports autovivification with empty versions of itself; for example:

        >>> tree = lambda: defaultdict(tree)
        >>> t=tree()

    :param key_list:
    :param value:
    :param leaf_list_key:
    """
    for k in key_list:
        tree=tree[k]
    if value is not None:
        if leaf_list_key in tree:
            tree[leaf_list_key].append(value)
        else:
            tree[leaf_list_key]=[value]



def tree_toString(tree, indent=1):
    """Return representation of tree structure in json-compatible string"""
    return json.dumps(tree, indent=indent)


class AutoTree(defaultdict):
    """
    A simple tree convenience class that includes the tree insert and tostring operations as instance methods.
    This should not be instantiated directly: use mytree = tree.Tree() to create an instance of this type.
    """

    def __call__(self, *args, **kwargs):
        return AutoTree(*args, **kwargs)

    def insert(self, key_list, value=None, leaf_list_key="_files"):
        """
            Given an ordered list of key names, descend down the tree by key, creating child branches (aka tree-levels, aka sub-dictionaries, aka child-trees,...) as needed.

            If `value` is None, the final element of the created branch will be an empty tree (unless the node specified by the final key already existed, in which case it will be unaltered and this method was a noop).

            If `value` is non-None, then upon reaching or creating the final branch component, if no key with the value given by `leaf_list_key` exists as direct child (i.e., can be accessed as::

                     tree[...][key_list[-1]][leaf_list_key]

            using the components from `key_list`), then an empty list will be created under that key value and value placed into it.  If the key `leaf_list_key` already exists, then it will be assumed that the list has already been created and contains elements, so an attempt to append `value` to that list will be made. Should the attempt fail, exceptions will be raised. Thus it is important to choose a value for `leaf_list_key` that will not conflict with the keys of any child trees on the same branch level.

            .. note:: This method was designed with the assumption that all keys are strings and no complex types (e.g. lists, dicts, tuples, etc.) will be stored as values. Violating these assumptions may result in undefined (read: broken) behavior.

            :param key_list:
            :param value:
            :param leaf_list_key:
            """
        tree = self
        for k in key_list:
            tree = tree[k]
        if value is not None:
            if leaf_list_key in tree:
                tree[leaf_list_key].append(value)
            else:
                tree[leaf_list_key] = [value]

    def __str__(self):
        return json.dumps(self, indent=1)

    def to_string(self, indent=1):
        """Return representation of tree structure in json-compatible string"""
        return json.dumps(self, indent=indent)

