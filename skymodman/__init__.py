import sys

# Why can't I figure out the best way to make sure this is available
# where and when I need it. Seems like it should be a common concern.
__manager = None

def Manager():
    """
    Return the globally registered mod manager instance

    :rtype: skymodman.managers.modmanager.ModManager
    """
    if not __manager:
        print("No manager registered", file=sys.stderr)
        return None
    else:
        return __manager

def register_manager(manager):
    """
    If no global manager has yet been registered, register `manager`.
    """
    global __manager
    # only register if none already registered
    if __manager is None:
        __manager = manager
    else:
        print("Manager is already registered", file=sys.stderr)


