# from collections import namedtuple
# TModEntry = namedtuple("TModEntry", ['enabled', 'name', 'modid', 'version', 'directory', 'ordinal'])
from skymodman import Manager


class ModEntry:
    __slots__ = ('enabled', 'name', 'modid', 'version',
                 'directory', 'ordinal', 'managed', 'error')
    _fields= __slots__


    def __init__(self, enabled=None, name=None, modid=None,
                 version=None, directory=None, ordinal=None,
                 managed=None, error=None):
        self.enabled   = enabled
        self.name      = name
        self.modid     = modid
        self.version   = version
        self.directory = directory
        self.ordinal   = ordinal
        self.managed   = managed
        # Error is a bitwise-combination of MOD_ERROR types
        self.error     = error


    @property
    def filelist(self):
        """Return the list of files contained by this mod."""
        # recently-queried mods are cached by modmanager
        return Manager().get_mod_file_list(self.directory)
        # return self._files

    @property
    def filetree(self):
        """Return the files contained by this mod as a tree"""
        return Manager().get_mod_file_tree(self.directory)


    # @filelist.setter
    # def filelist(self, value):
    #     self._files = list(value)


    ##=============================================
    ## Namedtuple interface parity
    ##=============================================

    def _replace(self, **kwargs):
        for k,v in kwargs.items():
            try:
                setattr(self, k, v)
            except AttributeError: pass

    @classmethod
    def _make(cls, iterrible):
        if hasattr(iterrible, "keys"):
            return cls(**iterrible)
        else:
            return cls(*iterrible)


    def __repr__(self):
        return self.__class__.__name__ + "(enabled={0.enabled}, name='{0.name}', modid={0.modid}, version='{0.version}', directory='{0.directory}', ordinal={0.ordinal}, managed={0.managed}, error={0.error})".format(self)
