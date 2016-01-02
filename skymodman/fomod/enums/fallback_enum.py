from enum import Enum, EnumMeta

class FallbackEnumMeta(EnumMeta):
    """
    Returns the value of the enum item pointed to by
    FallbackEnum()._default when lookup of an invalid
    value is requested.
    """
    def __call__(cls, value, *args, **kw):
        try:
            return super().__call__(value, *args, **kw)
        except ValueError:
            return cls[cls._default]

class FallbackEnum(Enum, metaclass=FallbackEnumMeta):
    """
    An enum that will return a fallback member if lookup is
    attempted with an invalid value. By default, the first
    member added to the enum will be the fallback, by a different
    member can be set as the fallback with using
    MyEnum.mymember.setAsFallback()
    """
    def __init__(self, *args):
        cls = self.__class__
        if len(cls.__members__)==0:
            cls._default = self.name
            #~ setattr(cls, '_default', self.name)

    def setAsFallback(self):
        """
        set this enum member as the fallback member.
        """
        cls = self.__class__
        cls._default = self.name
        # cls.__setattr__('_default', self.name)