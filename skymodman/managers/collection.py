import itertools
from operator import attrgetter

from skymodman.constants import ModError
from skymodman.managers.base import Submanager
from skymodman.log import withlogger
from skymodman.types import ModEntry, ModCollection

@withlogger
class ModCollectionManager(Submanager):
    """Intended to replace (at least some) of the database manager"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # temporary storage for info about unmanaged mods
        self._vanilla_mod_info = []

        # mod collection instance
        self._collection = ModCollection()
        # set as collection for all ModEntry objects
        ModEntry.collection = self._collection

        self._errors = {} # store mod errors here


    @property
    def collection(self):
        return self._collection

    @property
    def errors(self):
        return self._errors


    def reset(self):
        self._collection.clear()

    def clear_errors(self):
        """Reset the 'error' field on each mod to ModError.None"""

        # need to know if any mods currently have errors
        # had_errors = any(m.error for m in self._collection)

        # number of mods currently having errors
        num_errors = len(self._errors)
        self._errors.clear()

        # execute by feeding into 0-length deque
        # XXX: this is pretty hacky...
        # deque(map(lambda m: setattr(m, "error", ModError.NONE),
            # we could filter this down to just the entries
            # that have a non-NONE error field...but just setting
            # it on all of them is likely much quicker
            # self._collection), maxlen=0)

        # return True if some mods had errors (but now do not)
        return num_errors

    ##=============================================
    ## Mod-trait queries
    ##=============================================

    def enabled_mods(self, names_only = False):

        if names_only:
            return map(attrgetter("name"), filter(lambda m: m.enabled, self._collection))


            # yield from (m.name for m in self._collection if m.enabled)

        else:
            return filter(lambda m: m.enabled, self._collection)

            # yield from (m for m in self._collection if m.enabled)

    def managed_mods(self):
        """
        Iterate over all mods marked as "managed"
        """
        return filter(lambda m: m.managed, self._collection)

    def unmanaged_mods(self):
        return itertools.filterfalse(lambda m: m.managed,
                                     self._collection)


    ##=============================================
    ## validation
    ##=============================================

    def validate_mods(self, managed_mods_list):
        """Compare the mods held in the collection with
        `managed_mods_list`, a list of the mods actually present on disk
        in the mod-installation directory.

        Handle discrepancies by storing the type of error in the
        mapping 'errors', keyed with the unique-name of the mod.

        Error types are:

            * Mods Not Listed: for mod directories found on disk but not
              previously listed in the user's list of installed mods
            * Mods Not Found: for mods listed in the list of installed
              mods whose installation folders were not found on disk.
        """

        # FIXME: I think errors are another thing that should be stored externally of the ModEntry object

        # reset error field to None
        errors_cleared = self.clear_errors()

        # list of mods marked as 'managed' in the collection
        in_coll = list(m.directory for m in self.managed_mods())

        # make a copy of the list of mods-on-disk since we may be
        # modifying its contents
        on_disk = managed_mods_list[:]

        # errors discovered
        errmap = {
            ModError.DIR_NOT_FOUND: [],
            ModError.MOD_NOT_LISTED: []
        }

        # selector = len(in_coll) > len(on_disk)
        #
        # objs = (
        #     (in_coll, on_disk)[selector],
        #     (on_disk, in_coll)[selector],
        #     errmap[(ModError.DIR_NOT_FOUND, ModError.MOD_NOT_LISTED)[selector]],
        #     (ModError.MOD_NOT_LISTED, ModError.DIR_NOT_FOUND)[selector]
        # )
        #
        # for modname in objs[0]:
        #     try:
        #         objs[1].remove(modname)
        #     except ValueError:
        #         objs[2].append(modname)
        #     errmap[objs[3]]=objs[1]

        if len(in_coll) > len(on_disk):
            l_smaller = on_disk
            l_larger = in_coll
            receive_errors = errmap[ModError.MOD_NOT_LISTED]
            leftovers = ModError.DIR_NOT_FOUND

        else:
            l_smaller = in_coll
            l_larger = on_disk
            receive_errors = errmap[ModError.DIR_NOT_FOUND]
            leftovers = ModError.MOD_NOT_LISTED

        for modname in l_smaller:
            try:
                l_larger.remove(modname)
            except ValueError:
                receive_errors.append(modname)
            errmap[leftovers]=l_larger


        self._errors.update(itertools.chain(
            dict.fromkeys(errmap[ModError.MOD_NOT_LISTED],
                          ModError.MOD_NOT_LISTED),
            dict.fromkeys(errmap[ModError.DIR_NOT_FOUND],
                          ModError.DIR_NOT_FOUND)
        ))

        # for key in errmap[ModError.MOD_NOT_LISTED]:
        #     self._errors[key] = ModError.MOD_NOT_LISTED
        #     # self._collection[key].error = ModError.MOD_NOT_LISTED
        # # for key in not_found:
        # for key in errmap[ModError.DIR_NOT_FOUND]:
        #     self._errors[key] = ModError.DIR_NOT_FOUND
        #     # self._collection[key].error = ModError.DIR_NOT_FOUND

        return not (self._errors or errors_cleared)


    ##=============================================
    ## Loading
    ##=============================================


    # def load_mod_info
#     def load_saved_modlist(self, json_source):
#         """
#         read the saved mod information from a json file and
#         populate the mod collection
#
#         :param str|Path json_source: path to modinfo.json file
#         """
#
#         self.LOGGER << "<==Method call"
#
#         if not isinstance(json_source, Path):
#             json_source = Path(json_source)
#
#         success = True
#         with json_source.open('r') as f:
#             # read from json file and convert mappings
#             # to ModEntry objects
#             try:
#                 modentry_list = json.load(f, object_hook=_to_mod_entry)
#
#             except json.decoder.JSONDecodeError:
#                 self.LOGGER.error("No mod information present in {}, "
#                                   "or file is malformed."
#                                   .format(json_source))
#                 success = False
#             else:
#                 self._collection.extend(modentry_list)
#
#         # now get unmanaged mods
#         if not self.load_unmanaged_mods():
#             # TODO: figure out what to do in this case; does this need to be in a separate method that is called individually by the Manager?
#             self.LOGGER.warning("Failed to load unmanaged data")
#
#
#         return success
#
#
#     def load_unmanaged_mods(self):
#         """Check the skyrim/data folder for the vanilla game files, dlc,
#         and any mods the user installed into the game folder manually."""
#
#         success = False
#         if not self._vanilla_mod_info:
#             skydir = self.mainmanager.Folders['skyrim']
#             if skydir:
#                 self._vanilla_mod_info = vanilla_mods(skydir.path)
#             else:
#                 self.LOGGER.warning << "Could not access Skyrim folder"
#                 # return False to indicate we couldn't load
#                 return False
#
#         # this lets us insert the items returned by vanilla_mods()
#         # in the order in which they're returned, but ignoring any
#         # items that may not be present
#         default_order = itertools.count()
#
#         # noinspection PyTypeChecker
#         # present_mods = [t for t in self._vanilla_mod_info if
#         #                 (t[0] == 'Skyrim' or t[1]['present'])]
#
#         # get only the mods marked as "present" (i.e. at least some
#         # of their files were found in the data dir)
#         present_mods = filter(lambda vmi: vmi.is_present, self._vanilla_mod_info)
#
#         # skyrim should be first item
#         for m in present_mods:
#
#             # don't bother creating entries for mods already in coll;
#             # 'skyrim' should always be 1st item, and should always not
#             # be in the collection at this point; thus it will always
#             # be inserted at index 0
#             if m.name not in self._collection:
#                 self._collection.insert(
#                     next(default_order),
#                     _make_mod_entry(name=m.name,
#                                     managed=0,
#                                     # this is not exactly accurate...
#                                     # I really need to change 'directory' to something else
#                                     directory=m.name
#                                     ))
#                 # set success True if we add at least 1 item to collection
#                 success=True
#
#         return success
#
#
#
#
# ##=============================================
# ## Static helper methods
# ##=============================================
#
# def _make_mod_entry(**kwargs):
#     return _to_mod_entry(kwargs)
#
# def _to_mod_entry(json_object):
#     """
#     Take the decoded object literal (a dict) from a json.load
#     operation and convert it into a ModEntry object.
#
#     Can be used as an ``object_hook`` for json.load().
#
#     :param dict json_object:
#     :return:
#     """
#
#     return ModEntry._make(
#         json_object.get(field,
#                         _defaults.get(field, lambda f: "")(json_object)
#         ) for field in _mod_fields)
#
#
#
# #################################################
# ## NTS: these shouldn't even be in this module...
#
#
# # just an object to hold info about the faux-mods we generate for the
# # vanilla data/unamanged data user installed manually into Skyrim/Data
# VModInfo = namedtuple("VModInfo", "name is_present files missing_files")
#
# def vanilla_mods(skyrim_dir):
#     """
#     return pre-constructed ModEntries for the vanilla skyrim files
#
#     :param Path skyrim_dir: Path of skyrim installation
#     :rtype: list[tuple[str, dict[str, Any]]]
#     """
#
#     from skymodman.constants import SkyrimGameInfo as skyinfo
#     _relpath = os.path.relpath
#     _join = os.path.join
#
#     # NTS: only DLC should appear in mod list (skyrim/update do not,
#     # though their files will appear in archives/files lists)
#
#     # get 'skyrim/data'
#     datadir=None
#     for f in skyrim_dir.iterdir():
#         if f.is_dir() and f.name.lower() == "data":
#             datadir=str(f)
#             break
#
#     skyrim_mod = VModInfo(
#         name="Skyrim",
#         is_present=True, # the data directory is there, at least...
#         files=[*skyinfo.masters, *skyinfo.skyrim_archives],
#         missing=[]
#     )
#
#     # skyrim_mod = {
#     #     'name': "Skyrim",
#     #     'directory': 'Skyrim', # should be 'data'?
#     #     'ordinal': -1, # is this a good idea? Just to designate this is always first
#     #     'files': [*skyinfo.masters, *skyinfo.skyrim_archives],
#     #     'missing': [] # any missing files
#     # }
#
#     # walk the skyrim data directory for all files
#     um_files = []
#     for root, dirs, files in os.walk(datadir):
#         um_files.extend(
#             _relpath(_join(root, f), datadir).lower() for f in files
#         )
#
#     # for f in skyrim_mod['files']:
#     for f in skyrim_mod.files:
#         try:
#             # attempt to remove an expected file from list
#             um_files.remove(f.lower())
#         except ValueError:
#             # if it wasn't there, mark it missing
#             skyrim_mod.missing_files.append(f)
#         # if f.lower() not in um_files:
#         #     skyrim_mod['missing'].append(f)
#
#
#     # names/default ordering of dlc mods;
#     # some or all of these may not be present
#     # dlc_names = ["Dawnguard", "HearthFires", "Dragonborn",
#     #              "HighResTexturePack01", "HighResTexturePack02",
#     #              "HighResTexturePack03"]
#     dlc_mods = {}
#
#     # skyinfo.all_dlc has names of DLC
#
#     # dg, hf, db
#     for n in skyinfo.all_dlc[:3]:
#         dlc_mods[n] = VModInfo(
#             name=n,
#             files=[n+".esm", n+".bsa"],
#             present=False, # set to True if dlc is installed
#             missing_files=[] # if the dlc is Partially present,
#                              # record missing files
#         )
#
#         # dlc_mods[n] = {
#         #     "name": n,
#         #     "files": [n+".esm", n+".bsa"],
#         #     "present": False, # set to True if dlc is installed
#         #     "missing": [] # if the dlc is Partially present, record missing files
#         # }
#
#     # hi-res packs
#     for n in skyinfo.all_dlc[3:]:
#         dlc_mods[n] = VModInfo(
#             name=n,
#             files=[n + ".esp", n + ".bsa"],
#             present=False,
#             missing_files=[]
#         )
#         # dlc_mods[n] = {
#         #     "name": n,
#         #     "files": [n+".esp", n+".bsa"],
#         #     "present": False,
#         #     "missing": []
#         # }
#
#     for dlc, info in dlc_mods.items():
#         p = False # present?
#         # for f in info['files']:
#         for f in info.files:
#             try:
#                 um_files.remove(f.lower())
#                 p=True
#             except KeyError:
#                 # if f.lower() not in um_files:
#                 # p|=False
#                 info.missing_files.append(f)
#                 # info['missing'].append(f)
#         info.is_present = p
#         # info['present'] = p
#
#     # any remaining files can be aggregated into 'Data'
#
#     data_mod = VModInfo(
#         name="Unmanaged Data",
#         files=um_files, # anything left over,
#         is_present = len(um_files) > 0,
#         missing_files=[]
#     )
#
#     # data_mod = {
#     #     'name': "Unmanaged Data",
#     #     'directory': 'data',
#     #     'files': um_files,
#     #     'present': len(um_files) > 0,
#     #     'missing': []
#     # }
#
#     # return list of mod infos
#     result = [skyrim_mod, *[dlc_mods[n] for n in skyinfo.all_dlc],
#               data_mod]
#
#     # return tuples of (name: modinfo)
#     # result = [("Skyrim", skyrim_mod), *[(n, dlc_mods[n]) for n in skyinfo.all_dlc], (data_mod.name, data_mod)]
#
#     del skyinfo
#
#     return result


