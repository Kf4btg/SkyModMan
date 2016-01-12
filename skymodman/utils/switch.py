import operator as op

def _varicomp(c, v):
    """Allows passing a different callable-comparator for each case"""
    return c(v)

def _in_or_is(c, v, eq=op.eq, con=op.contains):
    """First tries to see if v is a member of c; if c is not a container, then checks equality"""
    try:
        return con(c,v)
    except TypeError:
        return eq(c,v)

# combines the two above
# (the "contains" check could still possibly causes issues with strings...)
def _call_or_in_or_is(c,v,eq=op.eq, con=op.contains):
    """tries to call c with the value of v;
    if c is not callable, checks if v is contained by c;
    if c is not a container, then checks if c==v"""
    try:
        return c(v)
    except TypeError:
        try:
            return con(c, v)
        except TypeError:
            return eq(c, v)


def switch(value, comp=op.eq):
    return [lambda match: comp(match, value)]

if __name__ == '__main__':
    j=4
    cas = ["a", "11", "5", [25, "4", "5", "g"], "3", "&"]
    ops = [ord, int, int, [lambda v: j+v**2, lambda v: ord(str(v)[:1]), lambda v: None, type], int, ord]

    # for case in switch(g):
    # g=5
    # for case in switch(g, _in_or_is):
    #     if case(3):
    #         print(0)
    #         break
    #     if case(["4", 5, 90]):
    #         print(1)
    # for case in switch(g, _varicomp):
    #     if case(lambda gv: gv**2==25):
    #         print("squared")
    #         break
    #     if case(lambda gv: gv * 2 == 24):
    #         print ("doubled")
    #         break

    def thing(val):
        for case in switch(val, _call_or_in_or_is):
            if case(3):
                print(0)
                break
            if case(["4", 5, 90]):
                print("listed")
                break
            if case(lambda gv: gv * 2 == 24):
                print("doubled")
                break
        else:
            print("nada")

    thing("4")
    thing("3")
    thing(3)
    thing(12)
