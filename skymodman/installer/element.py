from skymodman.thirdparty.untangle import untangle

class Element(untangle.Element):
    """
    Customized version of the basic Element type in untangle that
    doesn't throw as many errors on non-existing values and removes
    white space in cdata better.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # part of a hack to prevent empty lines from filling up all
        # the 'cdata' attributes
        self.prev2=""
        self.prev1=""

    @property
    def attributes_(self)->dict:
        return self._attributes

    def get_attribute(self, key, default=None):
        value = super().get_attribute(key)

        return default if value is None else value

    def __getattr__(self, key):
        try:
            return super().__getattr__(key)
        except AttributeError:
            return []

    def iter_all(self):
        """
        Recursively iterate over this element and all its children

        """
        yield self
        if len(self):
            for c in self.children:
                yield from c.iter_all()

    def add_cdata(self, cdata):
        """
        Squeezes blank lines together
        :param cdata:
        """
        if cdata.isspace():
            if self.prev1=="": return
            if self.prev1=="\n" \
                    and self.prev2 in ["","\n"]: return
            cdata='\n' # reduce all blank lines to a bare newline

        super().add_cdata(cdata)

        self.prev2=self.prev1
        self.prev1=cdata.strip(" \r")

    def attribute_pairs(self):
        """

        :yields: the attributes of the element as (key, value) tuples
        """
        yield from ((k,v) for k,v in self._attributes.items())