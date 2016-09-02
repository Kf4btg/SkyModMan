from enum import Enum

class BitEnum(Enum):
    """
    A type of enum that supports certain binary operations between its
    instances, namely & (bitwise-and) and | (bitwise-or). It also
    defines a bool-conversion where the member with value 0 will
    evaluate False, while all other values evaluate True.

    For this to work properly, the underlying type of the members
    should be int, and the subclass MUST define a "None"-like member
    with value 0.

    If a bitwise operation returns a result that is a valid member
    of the Enum (perhaps a combination you wanted to use often and
    thus defined within the enum itself), that enum member will be
    returned. If the result is not a valid member of this enum, then
    the int result of the operation will be returned instead. This
    allows saving arbitrary combinations for use as flags.

    These aspects allow for simple, useful statements like:

        >>> if some_combined_MyBitEnum_value & MyBitEnum.memberA:
        >>>     ...

    to see if 'MyBitEnum.memberA' is present in the bitwise combination
    'some_combined_MyBitEnum_value'
    """


    def __and__(self, other):
        try:
            try:
                val = other.value
            except AttributeError:
                # then see if its an int(able)
                val = int(other)
            res = self.value & val
        except (ValueError, TypeError):
            return NotImplemented

        try:
            return type(self)(res)
        except ValueError:
            return res

    def __or__(self, other):
        try:
            try:
                val = other.value
            except AttributeError:
                # then see if its an int(able)
                val = int(other)
            res = self.value | val
        except (ValueError, TypeError):
            return NotImplemented

        try:
            return type(self)(res)
        except ValueError:
            return res
        # try:
        #     return type(self)(self.value | other.value)
        # except ValueError:
        #     return type(self)(0)
        # except AttributeError:
        #     return NotImplemented

    def __bool__(self):
        return self.value != 0