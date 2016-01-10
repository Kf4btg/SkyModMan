from io import StringIO
indent=0
class ViviDict(dict):

    def __missing__(self, key):
        value = self[key] = type(self)()
        return value

class ViviDict2(dict):

    def __missing__(self, key):
        value = self[key] = type(self)()
        return value

    def dicts(self):
        dd= {k: self[k].dicts() if isinstance(self[k], dict) else self[k] for k in self }
        return dd

    # def dictify(self):
    #     """Get a standard dictionary of the items in the tree."""
    #     return dict([(k, (v.dictify() if issubclass(type(v), dict) else v))
    #                  for (k, v) in self.items()])


    def __str__(self):
        global indent
        s="{\n"+" "*indent
        indent+=2
        yes=True
        nope=False
        for k,v in self.items():
            if nope:
                s+=",\n"+" "*(indent-2)
            indent+=2
            if isinstance(v, type(self)):
                s+=" {}: {}".format(k,str(v))
            else:
                s+=" {}: {}".format(k, v)
                yes=False
            indent-=2
            nope=True

        # if yes:
        s+="\n "+" "*indent+"}"
        # else:
        #     s+=" }"
        indent-=2
        return s
        # return "\n" + pformat({k: repr(self[k]) for k in self}, indent=4)

    # def __repr__(self):
        # return str(self.dicts())
        # sio = StringIO()
        # return '\n'+sio.getvalue()
        # return pformat({k: str(self[k])+r'\n' for k in self})

    # def __dict__(self):
    #     """Get a standard dictionary of the items in the tree."""
    #     print([(k, v) for (k, v) in self.items()])
        # return dict([(k, (dict(v) if issubclass(type(v), dict) else v))
        #              for (k, v) in self.items()])
    #
    # def __repr__(self):
    #     return repr(self.dictify())
    #     return repr(self.)
# from collections import UserDict

class AutoDict(dict):
    """
    This dict subclass supports some extensions to allow it function as an arbitrary, non-balanced tree

    The first is making it callable like myAutoDict(key1, ..., key_last, new_key, newvalue)
    In terms of a normal dict, This is roughly equivalent to:

            myitem = mydict[key1][...][key_many]
            if not isinstance(myitem, dict):
                mydict[key1][...][key_many] = { "_values": [myitem], new_key: newvalue}
            else:
                mydict[key1][...][key_many].update({new_key: newvalue})

    Then, later on, you can get the value you just inserted with:
         myvalue = mydict[key1][...][key_many][new_key]

    If you need to access the item that was displaced, it can be accessed directly
    using the "_values" key on the given dict:
        myitem = mydict[key1][...][key_many]["_values"][0]

    or, if there is only one item in the list under the _values key, just using
        myitem = mydict[key1][...][key_many]

    would be equivalent to the previous statement. Just using item-notation on a non-leaf
    node in the tree will always return the first item in ["_values"], even if there are multiple items in the list.
    To get a different item, you can either access it directly as before, or use:

        myitem = mydict[key1][...][key_notleaf].pull(index)

    Note that the following three are all equivalent:

        myitem = mydict[key1][...][key_notleaf].pull()
        myitem = mydict[key1][...][key_notleaf].pull(0)
        myitem = mydict[key1][...][key_notleaf]

    AutoDict.pullall() will get you a copy of the entire list.

    If you need to add a non-dict value to a non-leaf node at any time, you can
    append items to the _values list in a number of ways:

        mydict[key] += item
        mydict[key] += [item1, item2, ...]
        mydict[key].push(item)

    To insert at a specific index, use:

        mydict[key].push(item, index)

    where item can be a single value or a list of values. Non-list-type sequences (tuple, set, etc.)
    will be added as a single value, so unpack them with * if you just want to add the values.

    Of course, directly accessing the list would work, too:

        mydict[key_notleaf]["_values"] += item
        mydict[key_notleaf]["_values"].insert(item, index)

    If you want to replace the entire list, just assign to the non-leaf node:

        mydict[key_notleaf] = [item1, item2, ...]
        mydict[key_notleaf] = item

    or even
        mydict[key_notleaf] = []

    Note that, in the second case, if the single value `item` is not a list instance, a list of length 1
    will implicitly be created to hold `item`.  Assigning `None` will result in an empty list, as if you
    had used the third statement (If you want an actual `None` value in the replacement list, first assign
    an empty list, then .push(None) to it).

    But that may be redundant, since, if the _values list is empty, attempting to get the first value
    from it using the item-notation shortcut will return None. However, using pull() will throw IndexError.

    You may have noticed that there is no way to assign a non-list value to _values using the above methods.
    This is by design.  You COULD replace the _values list with an arbitary value by directly accessing and
    overwriting the "_values" key, but you may as well make a new key if you're going to do that, as replacing
    "_values" would not only break some of the AutoDict functionality, but also violate some of its core assumptions.

    A main assumption of the AutoDict tree structure is that all 'real' data is stored in the
    leaves of the tree. The special treatment of the _values list is simply a shortcut to simulate having data
    nodes and child-branches accessible at the same level of the tree (contained under the same parent).

    This is much like
    the common visual representation of the directory structure on a filesystem: any directory can contain any
    number of files and sub-directories, and they all show up next to each other when you view a folder's contents
    in a file manager or list them on the command line. But in python, preserving that relationship while retaining
    the ability to access child-nodes by dictionary key requires a bit of abstraction, which is where _values comes in.
    Think of it as the "files list", while the other dictionary keys comprise the "directories list".

    Don't want to use the _values abstraction? Ok, well, here are some alternatives:

    You could of course ignore _values altogether, even use your own key (or keys) like "items" or "files" to hold
    a container of non-Autodict children you wish to be accessible at that tree level. You'd have to manage this
    container yourself, but I doubt that wouldn be difficult. If you're considering this option, you were probably
    going to filter or analyze the data as it comes in anyway, and your code will likely be better off for routing
    it in more personalized directions.

    You could determine to store every piece of data in its own individual leaf node. For the first scenario,
    it seems likely you're storing mostly or entirely complex objects, and won't have a need for 'flat' values
    (data that is just a string, bool, int, etc.). While you can certainly use the autodict for that, that wasn't
    its design purpose, and there are quite probably other data structures out there more suited to and optimized
    for your needs.

    If you have a lot of simple data like strings, you could store the 'data' in the key itself and have the key's
    value be None, empty, or the same as the key.  While that would work, it would take a little juggling of the
    items() and/or keys() methods to get your data, which is counter to a lot of the principles and utility behind
    using a dict in the first place.

    Additionally, another core premise of AutoDict is that _every_ piece of the tree
    is a meaningful part of the data: keys are labels, identifiers, and descriptors of the values or subtrees that
    lie below them; that data or subtree would have very different meaning if it were under a different key. Data
    whose meaning or purpose would not be further described by additional categorization should be stored as a
    flat value at the last meaningful level. I realize that's a bit abstract, but by adding superfluous or redundant
    aspects to the tree the data density and efficiency of the structure is reduced.  If you feel that's not going
    to be a problem for you or your program, then go right ahead!






    """
    def __init__(self, iterable, **kwargs):
        super(AutoDict, self).__init__(iterable, **kwargs)
        [].insert()
        # self.data = dict(initialData.copy()) if initialData else dict()
        # super(AutoDict, self).__init__()
        # if initialData:
        #     self.data = ViviDict(initialData.copy())
        # else: self.data = ViviDict()
        # self.retrieved_item = None

    def __call__(self, key1, key2, *key_or_val):
        """
        This will have to replace the normal attribute access
        for the setting-convenience features of this type. Ie., instead of
            autodict["key1"][key2][id(key3)][...] = value
        you will use
            autodict(key1, key2, key3, ..., value)
        Note that attribute access can still be used as desired for getting,
        and for setting if desired, but note that 'extending' a key whose value is not already
        a dict will fail.

        Here's the assumptions that will be made when calling this method:
            1) the final value to be inserted is NOT an AutoDict or subclass thereof;
               such an assignment is redundant. Use normal subscript notation if you want to create
               an empty autodict:  ottodict["a"]["b"]["c"]   # creates an empty AutoDict at the "leaf" assigned to key "c"
            2) Every key represents a nested AutoDict. If you're attempting to assign to a regular dict
               or other assignable object that you've previously stored in the structure, again, you should
               just be using regular subscript access.  Other than this specialized function, an AutoDict
               instance should function the same as a normal dict.

        As an autodict tree is a nested structure of autodicts, regular dict access could be used to
        get to the lowest existing autodict instance which can then be called to handle converting it from a
        leaf to a branch. So:  ought_o_dict[sub1][sub2][sub3](key, value)
        You can of course stop anywhere in the descent and switch to the call notation for the rest of the keys.

        :param key1: at least one key is required to accessing or creating the item in the base autodict
        :param key2: if the next paramater is omitted or a single value, then this will be the "new key"
        :param key_or_val: list of additional keys and one final value that will be assigned or inserted into the
        item referenced by the key immediately proceeding it.
        """

        arglist = list(key_or_val)
        # default new value is None
        if not key_or_val:
            val=None
        else:
            val = arglist.pop()


        arglist.reverse()
        keylist = list(key_or_val)
        # remove and save the last arg given
        value=keylist.pop()

        # put the first keys at the end
        keylist = keylist.reverse()
        d=self

        k=arglist.pop() # the first key # self[k]
        while True:
            try:
                try:
                    sub=d[k] # could throw 'not subscriptable' TypeError
                except TypeError:
                    pass


                v=arglist.pop() # the next key or the value
                # while we're not at the end of the args,
                try:
                    # assume d is a dict
                    d.__setitem__()
                except TypeError: # "<type> does not support item assignment"
                    # if d was NOT a dict, turn it into a dict containing its current value as a member
                    pass


            except IndexError:
                break


        while True:
            try:
                # get key until the list runs out
                k=keylist.pop(0)
            except IndexError:
                break
            try:
                d=d[k]
            except TypeError:
                pass

        # if last
        # either because it was already or was created by missing:
        # if isinstance(d, type(self)):
            # proceed as normal
            # d[final] = None


    def __missing__(self, key):
        value = self[key] = type(self)()
        return value


    def __getitem__(self, key):
        print ("getting item for "+key)
        # we will store the item we retrieve in an instance variable;
        # this way, we will be able to tell
        self.retrieved_item = self.data.__getitem__(key)
        return self.retrieved_item


    def __setitem__(self, key, value):
        print ("setting "+key+"="+value)
        try:
            self.data[key]=value
            # super(AutoDict, self).__setitem__(key, value)
        except TypeError as e:
            print (e)

    def __str__(self):
        return str(self.data)


from collections import defaultdict
from pprint import pprint
def tree():
    return defaultdict(tree)

def test(tt=ViviDict(), args=None):
    # tree = lambda : defaultdict(tree)

    # t=ViviDict()
    # print(t)
    # t["key1"]=4
    # print("in:  ")
    # pprint(tt.dicts(),  width=10)
    # print(tt)

    if args:
        args = args.copy()
    else:
        args=["key1", "key2", "key3", "value"]

    # args=["key1", "value"]

    val = args.pop() # save last argument (the value)
    args.reverse()

    ot = tt # save ref to initial tree

    curr_key=args.pop() # get first key
    d_curr=t # save a reference to base dict

    # we want to be careful not to autovivicate a dict for our final key
    # since the assumption is that "val" will be assigned to that key.
    # therefore, in case our first key is also our last key,
    # we only run this loop when there is at least one more
    # key remaining in the list

    # the loop will be looking two-levels ahead most of the time:
    # from the "current dict" we will be looking into the "sub dict"
    # referenced by "current key" and extracting the "next dict"
    # from that sub using the "next key". After that, we shift
    # everything by one level and do it again. Repeat until keys
    # are exhausted.

    # Confusing, I know, but what makes it worse is that
    # there is a strange situation at the beginning where the
    # "current" and "sub" (first two) levels are the same
    d_sub = d_curr
    next_key = curr_key

    while len(args)>0: #multiple args, so we will be descending
        # print()
        # print((len(args), 'key:', curr_key, 'next:', next_key))
        # print("dt: %s" % d_sub)
        # print("ot: %s" % ot)

        #
        #                                   d_next
        #                                      |
        # d_curr = { curr_key: { next_key : (value) } }
        #                      |____________________|
        #                                |
        #                             d_sub
        #

        # First Run Failure?:
        #   d_curr == d_sub == { }
        #   dnext = dsub[key] = {}  # autoviv'd
        #
        #   d_curr == d_sub == { key: {} }
        #
        #  QED first run failure not possible; empty dict means always create new dicts

        # Second run failure:
        #  Run1:
        #   key == currkey == nextkey
        #   d_curr == dsub == { key : notadict }
        #   dnext = dsub[key] = notadict
        #
        #  then:
        #   d_curr = d_sub #redundant
        #   curr_key = next_key # redundant
        #   dsub = dnext # (notadict)
        #   next_key = args.pop()
        #
        # Run2:
        #  d_curr == { currkey: notadict }
        #  d_sub == notadict
        #  dnext = dsub[nextkey] = notadict[nkey] ==> throw Error
        #
        # But at this point, the proper location is still available via d_curr[curkey], so we're good.

        # we know curr_key exists and is NOT the last key, so this is safe:
        # d_sub = d_curr[curr_key]

        try:
            # assume each key other than the last references a subdict;
            # next_key is mathematically prohibited from being the last key
            # at this point in the loop, so we get the next subdict from our
            # most recently obtained subdict
            d_next = d_sub[next_key]

            # that's really all the work that needed to be done. The rest of this is
            # just shifting everything to set up for the loop iteration.

            # after that first step, we can consider next_key our current key, so we save it as such
            curr_key = next_key

            # now, pull the upcoming key from args and assign to next_key;
            # at this point, next_key COULD be the last key, so we don't want to use it
            # until the next loop iteration when we can be sure it is once again safe.
            next_key = args.pop()

            # we're moving down to the next level of the tree, so d_sub now becomes our current dict
            d_curr = d_sub
            # and d_next becomes our current sub dict
            d_sub = d_next


            # *NOTE: if this was the first iteration of the loop, we already had d_sub===d_curr and
            # curr_key == next_key, so the previous operations were all a little redundant.
            # However, they're necessary for the rest of the loop to proceed correctly, so it's
            # a small price to pay for not requiring a separate check for the first run

            # *NOTE2: It should be impossible (according to my calculations)
            # for a failure to occur on the first run of the loop.
            # The second run is the earlist a TypeError can occur, making this whole rigamarole
            # superfluous for a 2-key vals list. Perhaps THAT is a reason to have a special case
            # for the len(args)==1 scenario...let's ponder.

        # except TypeError:

        # try:
        #     now (still assuming d_sub is a dict), get the value for next_key from d_sub
            # tsubsub = d_sub[next_key]
        except (TypeError, AssertionError):
            # print("Error! '{}' is not a dictionary!".format(d_sub))
            # however, if we were wrong in our assumption that `d_sub` is a dict,
            # trying to get the key value will throw an exception;
            # this changes our assumption to assume that `d_sub` is in fact a non-dict value
            # (a.k.a. a leaf node) that was referenced by what is now `curr_key`
            # in what is now the containing dict `d_curr`
            d_sub = make_value_list(d_sub, d_curr, curr_key)
            # in that case, we'll want to set that value aside into a list...
            ########## vlist = [d_sub]
            # and just delete that item from the dict altogether, key & value both
            ########## del d_curr[curr_key] # this won't cause the value to be garbage-
                             # collected because we still have a reference to it in vlist

            # now recreate the key's value as a dict using the autovivication
            # feature and put our saved list into it under a special key
            ########### d_curr[curr_key]["_values"]=vlist


            # set d_sub to the point to the new dict
            ########## d_sub = d_curr[curr_key]
            # we haven't pulled a new key or updated any of our variables,
            # so the next run of the loop will re-attempt the most recent
            # operation; but this time, instead of failing, it will autoviv the
            # next subdict using new_key.

            # Since we just reached the tip of this branch, we KNOW that from here on out
            # any further keys are going to autovivicate a dict for their value, meaning
            # we don't need to worry about encountering any non-dict values anymore.
            # But there would be little benefit in fastforwarding through the loop right
            # here versus letting it run itself out with the non-failing try.

    # print("dt: %s" % d_sub)
    # print("ot: %s" % ot)

    # if the final "new" key is not actually new and is already a child branch,
    # don't overwrite it with val; append val to its _values list
    # print(d_curr)
    # print(d_sub)
    if next_key in d_sub and isinstance(d_sub[next_key], ViviDict):
        d_sub[next_key]["_values"]=[val]
    else:
        # to finish off the tree after the loop runs out, we
        # use the final key value (stored in next_key) to insert the value `val`
        try:
            d_sub[next_key]=val
        except TypeError:
            d_sub = make_value_list(d_sub, d_curr, curr_key)
            d_sub[next_key] = val
        # This same statement also serves to handle the case where there was only
        # one key (while loop never ran). In that case, d_curr
        # will be the same object as the initial tree

    # print("dt: %s" % d_sub)
    # print("out: ")
    # print(ot)
    # pprint(ot, width=20)
    return ot
    # print(ot["key1"]["key2"])

def make_value_list(value, curr_dict, curr_key):
    vlist = [value]
    # and just delete that item from the dict altogether, key & value both
    del curr_dict[curr_key]  # this won't cause the value to be garbage-
    # collected because we still have a reference to it in vlist

    # now recreate the key's value as a dict using the autovivication
    # feature and put our saved list into it under a special key
    curr_dict[curr_key]["_values"] = vlist

    # set d_sub to the point to the new dict
    return curr_dict[curr_key]

from pprint import pformat
import json

if __name__ == '__main__':

    t=ViviDict()

    t["1"]["2"]=[555,32]
    t["1"]["3"]["4"]["5"]={"whoooa": "nooooope"}
    # t[1][2][3][4][5][6][7][8][9]
    # pprint(t.dicts(), width=15)
    # print(t)

    vals=["1", "3", "last", "new", "value"]

    nt = test(t, vals)
    vals = ["1", "3", 3]

    test(nt, vals)
    print(nt)
    print()
    vals=["1","2","happy","now"]
    test(nt, vals)

    print(nt)

    # j=json.loads(str(nt))
    sj = json.dumps(nt, indent=1)

    # print(sj)

    lines = sj.splitlines()
    # pprint(lines)

    inlist=-1
    toremove=[]
    for i in range(len(lines)):
        l=lines[i]
        sl = l.strip()
        if l=="":
            toremove.append(i)
            continue

        if inlist>=0:
            if sl.startswith(']'):
                lines[inlist] += sl
                lp1s = lines[i+1].strip()
                if lp1s.startswith(']'):
                    lines[inlist] += lp1s
                    toremove.append(i+1)
                    lines[i+1]=""
                inlist = -1
            else:
                lines[inlist] += " "+sl
            lines[i]=""
            toremove.append(i)

        else:
            if l.endswith('[') and not lines[i+1].lstrip().startswith('{'):
                lines[i]+=lines[i+1].strip()
                inlist=i
                lines[i+1]=""
            elif l.endswith('{') and \
                    not (lines[i+1][-1] in ['{', '[']) and \
                    (lines[i+2].endswith('}') or lines[i+2].endswith('},')) :
                lines[i]+=" "+lines[i+1].strip()+" "+lines[i+2].strip()
                lines[i+1]=lines[i+2]=""

    toremove.reverse()
    # pprint(lines)
    for r in toremove:
        del lines[r]

    newstr = "\n".join(lines)

    print(newstr)


    # ps=pformat(nt)
    # ps=str.replace(ps, ": ", ":\n ")
    # lines=ps.splitlines(True)
    # for line in lines: #type: str
    #     slines=[]
    #     s=0
    #     e=line.find(":")
    #     while e>0:
    #         seg = line[]
    #         slines.append()


    # print(ps)

    # t = ViviDict()
    # t["test"]="vest"
    # print(t)
    # t["best"]["rest"]="jest"
    # print(t)
    # t["test"].update(behest="test")
    # ="lest"
