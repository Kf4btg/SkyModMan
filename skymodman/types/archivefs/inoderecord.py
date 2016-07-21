class InodeRecord:

    __slots__ = ("parent", "name", "__inode")

    def __init__(self, name, inode, parent_inode):
        """

        :param str name:
        :param int inode:
        :param int parent_inode:
        """
        self.__inode = inode    # immutable
        self.name = name          # mutable
        self.parent = parent_inode  # mutable


    @property
    def inode(self):
        return self.__inode

    def __int__(self):
        return self.__inode
    def __index__(self):
        return self.__inode
    def __lt__(self, other):
        # Despite having a 'name' attribute, these should always be ordered
        # by the value of their main inode
        if not hasattr(other, "__int__"):
            return NotImplemented
        return self.__inode < int(other)