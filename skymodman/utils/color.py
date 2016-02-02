from collections import namedtuple

def _bound(value, lower, upper):
    if value < lower: return lower
    if value > upper: return upper
    return value

class Color(namedtuple("Color", "R G B")):
    """"
    Just a very simple RGB color representation with ability to convert
    to/from hex-notation. Thanks to its generic nature, it can easily be
    extended to accomodate more components and all the methods should
    still work without having to override them to add the new component

    """
    __slots__ = ()

    # Restrict the values between 0 and 255
    def __new__(cls, *args):
        return super().__new__(cls,
                               *(_bound(a, 0, 255)
                                 for a in args))


    @classmethod
    def from_hexstr(cls, hexstr):
        """

        :param str hexstr: must be a string of 6 or 3 characters (7 or 4 if prepended with '#'), each a valid hex digit.  The string 'ABC' is interpreted as shorthand for 'AABBCC'. Case is unimportant, and need not even be consistent: 'aaBBcc' == 'AabBCc'
        :return: a new Color initialized from the converted values of `hexstr`
        """
        hexstr = hexstr.strip().lstrip("#")

        len_str = len(hexstr)
        num_fld = len(cls._fields)
        if len_str == num_fld: # ABC
            step, rpt = 1, 2
        else: # AABBCC
            step, rpt = 2, 1

        flds = tuple(int(hexstr[step*i:step*i+step]*rpt, 16)
                     for i in range(num_fld))

        return cls._make(flds)

    def to_hexstr(self, case='X'):
        """
        Returns a hexadecimal-representation of the color, using uppercase letters by default. Pass 'x' for the `case` argument to use lowercase letters:

        >>> Color(255,255,0).to_hexstr()
        'FFFF00'
        >>> Color(255,255,0).to_hexstr('x')
        'ffff00'

        This is NOT the same as hex(Color(...)), though the only difference is that hex() prepends '0x' to the hex string (and is usually lowercase):

            >>> hex(Color(255,255,0)
            '0xffff00'


    .. note:: ``Color.__str__()`` is an alias for ``Color.to_hexstr('X')`` (the default uppercase representation). ``Color.__repr___()`` still returns the default namedtuple __repr__:

            >>> str(Color(255,255,0))
            'FFFF00'
            >>> repr(Color(255,255,0))
            'Color(R=255, G=255, B=0)'
        ..
        """
        if case not in 'Xx': case='X'

        return "".join("{0.%s:02%s}" % (f, case) for f in self._fields).format(self)

    def __str__(self):
        return self.to_hexstr()

    def __hex__(self):
        return '0x'+str(self)

    def __int__(self):
        return int(str(self), 16)

    def __eq__(self, other):
        if not hasattr(other, "__int__"):
            return NotImplemented
        return int(self) == int(other)

    def __lt__(self, other):
        if not hasattr(other, "__int__"):
            return NotImplemented
        return int(self) < int(other)



if __name__ == '__main__':
    c = Color(55,66,77)
    print(c.to_hexstr('x'))
    assert c.to_hexstr() == '37424D'

    c2 = Color.from_hexstr('37424d')
    c3 = Color.from_hexstr('#37424D')
    print(c2)
    print(c3)

    assert c2.R == c3.R == c.R == 55
    assert c2.G == c3.G == c.G == 66
    assert c2.B == c3.B == c.B == 77

    print(str(c))
    print(repr(c))

    print (Color(2001, 256, -1))

    assert Color(-1, -1, -1) == Color(0, 0, 0)
    assert Color(256, 256, 256) == Color(255, 255, 255)

    assert Color.from_hexstr("#ABC") == Color.from_hexstr("#AABBCC")

    print (repr(Color.from_hexstr('ABC')))
    print (repr(Color.from_hexstr('012')))

