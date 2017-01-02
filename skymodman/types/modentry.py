from collections import OrderedDict

from skymodman import Manager

class ModEntry:
    __slots__ = ('directory', 'name', 'modid', 'version',
                 'enabled', 'managed')
    _fields= __slots__ # to match the namedtuple interface

    # set this to associate all ModEntry objects with a ModCollection
    # instance; when set, the entries can use the collection to look up
    # their ordinal
    collection = None
    """:type: skymodman.types.modcollection.ModCollection"""


    def __init__(self, directory=None, name=None,
                 modid=None, version=None, enabled=None,
                 managed=None):
        """

        :param int enabled: 0/1; togglable by user
        :param str name: Customizable by user
        :param int modid: Nexus id (might need to rename this field)
        :param str version: arbitrary, set by mod author
        :param str directory: arbitrary, must be unique among all other
            mod entries
        :param int managed: 0/1, determined by installation location
        """

        # TODO: it really sounds like the 'ordinal' should be external to the mod entry and looked up on query

        self.directory = directory
        self.name      = name
        self.modid     = modid
        self.version   = version
        self.enabled   = enabled
        self.managed   = managed
        # Error is a bitwise-combination of constants.enums.ModError values
        # self.error     = error

    @property
    def key(self):
        """Return a unique identifier for this modentry; for managed
        mods, that will be the name of the mod's directory in the mod-
        storage folder. For unmanaged vanilla "mods", it will likely be
        something like the name of the DLC (e.g. 'HearthFires'). For
        unmanaged, non-vanilla mods (files discovered in the skyrim
        data folder that were manually installed by the user), it will
        be the name of the main plugin."""

        # at the moment, we're still calling this 'directory'
        return self.directory

    @property
    def ordinal(self):
        """Query the ModCollection (assuming one has been set) to
        find out the current ordering of this mod entry"""
        try:
            return ModEntry.collection.index(self.key)
        except AttributeError:
            # if no collection is yet associated, always return -1
            return -1

    @property
    def filelist(self):
        """Return the list of files contained by this mod."""
        # recently-queried mods are cached by modmanager
        try:
            return Manager().get_mod_file_list(self.key)
        except AttributeError:
            # no manager, somehow
            return []

    @property
    def filetree(self):
        """Return the files contained by this mod as a tree"""
        try:
            return Manager().get_mod_file_tree(self.key)
        except AttributeError:
            return None


    # @filelist.setter
    # def filelist(self, value):
    #     self._files = list(value)


    ##=============================================
    ## Namedtuple interface parity
    ##=============================================

    def _replace(self, **kwargs):
        """Change the value of one or more of this objects attributes.
        If an attribute does not exist, the attempt to set it will fail
        silently."""
        for k,v in kwargs.items():
            try:
                setattr(self, k, v)
            except AttributeError: pass

    @classmethod
    def _make(cls, iterrible):
        """Create a new instance of this class initialized from the
        given iterable (either a Mapping or a Sequence)."""
        if hasattr(iterrible, "keys"):
            return cls(**iterrible)
        else:
            return cls(*iterrible)

    def _asdict(self):
        """Convert the ModEntry to an OrderedDict instance"""

        return OrderedDict((f, getattr(self, f)) for f in self._fields)

    def __iter__(self):
        """allows this object to be converted to tuple (or list, or other
        sequence type)"""

        # yield ordinal first; this is to allow the ordinal to still
        # be stored in the database, though the individual mods don't
        # really care about it.
        # yield self.ordinal
        # use _fields to ensure proper order
        yield from (getattr(self, f) for f in self._fields)

    def __repr__(self):
        sparts = [self.__class__.__name__, "("]

        fparts = []
        for f in self._fields:
            v=getattr(self, f)
            fparts.append(f"{f}={v!r}")

        sparts.append(", ".join(fparts))
        sparts.append(")")

        return "".join(sparts)

        # return self.__class__.__name__ + \
        #        "(" + \
        #        ", ".join(
        #            (f + "=" + getattr(self,f) for f in self._fields)
        #        ) + ")"
        # return self.__class__.__name__ + "(enabled={0.enabled}, name='{0.name}', modid={0.modid}, version='{0.version}', directory='{0.directory}', managed={0.managed})".format(self)
        # return self.__class__.__name__ + "(enabled={0.enabled}, name='{0.name}', modid={0.modid}, version='{0.version}', directory='{0.directory}', ordinal={0.ordinal}, managed={0.managed}, error={0.error})".format(self)

    ##=============================================
    ## comparison
    ##=============================================

    def __eq__(self, other):
        if isinstance(other, ModEntry):
            return other.key == self.key
        return NotImplemented

# if __name__ == '__main__':
#     testmod = ModEntry("testdir", "Test Mod", 143, "ver1", 1, 0)
#
#     print(testmod)
#
#     print(testmod._asdict())
