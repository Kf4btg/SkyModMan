# from collections import namedtuple

# TModEntry = namedtuple("ModEntry", ['enabled', 'name', 'modid', 'version', 'directory', 'ordinal'])

class ModEntry:
    __slots__ = 'enabled', 'name', 'modid', 'version', 'directory', 'ordinal'

    def __init__(self, enabled=None, name=None, modid=None, version=None, directory=None, ordinal=None):
        self.enabled   = enabled
        self.name      = name
        self.modid     = modid
        self.version   = version
        self.directory = directory
        self.ordinal   = ordinal

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

    @property
    def _fields(self):
        return ('enabled', 'name', 'modid', 'version', 'directory', 'ordinal')