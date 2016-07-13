# from collections import namedtuple
# TModEntry = namedtuple("TModEntry", ['enabled', 'name', 'modid', 'version', 'directory', 'ordinal'])

class ModEntry:
    __slots__ = ('enabled', 'name', 'modid', 'version',
                 'directory', 'ordinal', 'error')
    _fields= __slots__


    def __init__(self, enabled=None, name=None, modid=None, version=None, directory=None, ordinal=None, error=None):
        self.enabled   = enabled
        self.name      = name
        self.modid     = modid
        self.version   = version
        self.directory = directory
        self.ordinal   = ordinal
        # Error is a bitwise-combination of MOD_ERROR types
        self.error     = error

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
        return self.__class__.__name__ + "(enabled={0.enabled}, name='{0.name}', modid={0.modid}, version='{0.version}', directory='{0.directory}', ordinal={0.ordinal}, error={0.error})".format(self)
