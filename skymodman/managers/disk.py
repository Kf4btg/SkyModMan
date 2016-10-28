import json
import json.decoder
import os
import itertools


from pathlib import Path
from collections import namedtuple

from skymodman import exceptions
from skymodman.constants import ModError
from skymodman.managers.base import Submanager
from skymodman.log import withlogger
from skymodman.types import ModEntry

_mod_fields = ModEntry._fields

_defaults = {
    "name": lambda v: v["directory"],
    "modid": lambda v: 0,
    "version": lambda v: "",
    "enabled": lambda v: 1,
    "managed": lambda v: 1,
    "error": lambda v: ModError.NONE
}

@withlogger
class IOManager(Submanager):
    """Contains methods dealing with the reading and writing
    of application data to/from the user's hard-disk"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # track which dlc are present
        # TODO: actually use this
        self.dlc_present = {
            'dawnguard':            False,
            'hearthfires':          False,
            'dragonborn':           False,
            'highrestexturepack01': False,
            'highrestexturepack02': False,
            'highrestexturepack03': False,
        }

        # temporary storage for info about unmanaged mods
        self._vanilla_mod_info = []


    ##=============================================
    ## Loading saved mod information
    ##=============================================

    # def load_mod_info
    def load_saved_modlist(self, json_source, container):
        """
        read the saved mod information from a json file and
        populate the mod collection

        :param str|Path json_source: path to modinfo.json file
        :param collections.abc.MutableSequence container: where to put the loaded ModEntries
        """

        self.LOGGER << "<==Method call"

        if not isinstance(json_source, Path):
            json_source = Path(json_source)

        success = True
        with json_source.open('r') as f:
            # read from json file and convert mappings
            # to ModEntry objects
            try:
                modentry_list = json.load(f,
                                          object_hook=_to_mod_entry)

            except json.decoder.JSONDecodeError:
                self.LOGGER.error(
                    "No mod information present in {}, "
                    "or file is malformed."
                    .format(json_source))
                success = False
            else:
                container.extend(modentry_list)

        # now get unmanaged mods
        if not self.load_unmanaged_mods(container):
            # TODO: figure out what to do in this case; does this need to be in a separate method that is called individually by the Manager?
            self.LOGGER.warning("Failed to load unmanaged data")

        return success

    def load_unmanaged_mods(self, container):
        """
        Check the skyrim/data folder for the vanilla game files, dlc,
        and any mods the user installed into the game folder manually.

        :param collections.abc.MutableSequence container:
        :return:
        """

        success = False
        if not self._vanilla_mod_info:
            skydir = self.mainmanager.Folders['skyrim']
            if skydir:
                self._vanilla_mod_info = vanilla_mods(skydir.path)
            else:
                self.LOGGER.warning << "Could not access Skyrim folder"
                # return False to indicate we couldn't load
                return False

        # this lets us insert the items returned by vanilla_mods()
        # in the order in which they're returned, but ignoring any
        # items that may not be present
        default_order = itertools.count()

        # noinspection PyTypeChecker
        # present_mods = [t for t in self._vanilla_mod_info if
        #                 (t[0] == 'Skyrim' or t[1]['present'])]

        # get only the mods marked as "present" (i.e. at least some
        # of their files were found in the data dir)
        present_mods = filter(lambda vmi: vmi.is_present,
                              self._vanilla_mod_info)

        # skyrim should be first item
        for m in present_mods:

            # don't bother creating entries for mods already in coll;
            # 'skyrim' should always be 1st item, and should always not
            # be in the collection at this point; thus it will always
            # be inserted at index 0
            if m.name not in container:
                container.insert(
                    next(default_order),
                    _make_mod_entry(name=m.name,
                                    managed=0,
                                    # this is not exactly accurate...
                                    # I really need to change 'directory' to something else
                                    directory=m.name
                                    ))
                # set success True if we add at least 1 item to collection
                success = True

        return success




##=============================================
## Static helper methods
##=============================================

def _make_mod_entry(**kwargs):
    return _to_mod_entry(kwargs)

def _to_mod_entry(json_object):
    """
    Take the decoded object literal (a dict) from a json.load
    operation and convert it into a ModEntry object.

    Can be used as an ``object_hook`` for json.load().

    :param dict json_object:
    :return:
    """

    return ModEntry._make(
        json_object.get(field,
                        _defaults.get(field, lambda f: "")(json_object)
        ) for field in _mod_fields)



#################################################
## NTS: these shouldn't even be in this module...


# just an object to hold info about the faux-mods we generate for the
# vanilla data/unamanged data user installed manually into Skyrim/Data
VModInfo = namedtuple("VModInfo", "name is_present files missing_files")

def vanilla_mods(skyrim_dir):
    """
    return pre-constructed ModEntries for the vanilla skyrim files

    :param Path skyrim_dir: Path of skyrim installation
    :rtype: list[tuple[str, dict[str, Any]]]
    """

    from skymodman.constants import SkyrimGameInfo as skyinfo
    _relpath = os.path.relpath
    _join = os.path.join

    # NTS: only DLC should appear in mod list (skyrim/update do not,
    # though their files will appear in archives/files lists)

    # get 'skyrim/data'
    # datadir=None
    for f in skyrim_dir.iterdir():
        if f.is_dir() and f.name.lower() == "data":
            datadir=str(f)
            break
    else:
        # datadir was not found
        raise exceptions.FileAccessError("Data", "The Skyrim '{file}' directory was not found within the Skyrim installation folder.")


    skyrim_mod = VModInfo(
        name="Skyrim",
        is_present=True, # the data directory is there, at least...
        files=[*skyinfo.masters, *skyinfo.skyrim_archives],
        missing=[]
    )

    # walk the skyrim data directory for all files
    um_files = []
    for root, dirs, files in os.walk(datadir):
        um_files.extend(
            _relpath(_join(root, f), datadir).lower() for f in files
        )

    for f in skyrim_mod.files:
        try:
            # attempt to remove an expected file from list
            um_files.remove(f.lower())
        except ValueError:
            # if it wasn't there, mark it missing
            skyrim_mod.missing_files.append(f)

    # names/default ordering of dlc mods;
    # some or all of these may not be present
    # dlc_names = ["Dawnguard", "HearthFires", "Dragonborn",
    #              "HighResTexturePack01", "HighResTexturePack02",
    #              "HighResTexturePack03"]
    dlc_mods = {}

    # skyinfo.all_dlc has names of DLC

    # dg, hf, db
    for n in skyinfo.all_dlc[:3]:
        dlc_mods[n] = VModInfo(
            name=n,
            files=[n+".esm", n+".bsa"],
            present=False, # set to True if dlc is installed
            missing_files=[] # if the dlc is Partially present,
                             # record missing files
        )

    # hi-res packs
    for n in skyinfo.all_dlc[3:]:
        dlc_mods[n] = VModInfo(
            name=n,
            files=[n + ".esp", n + ".bsa"],
            present=False,
            missing_files=[]
        )

    for dlc, info in dlc_mods.items():
        p = False # present?
        for f in info.files:
            try:
                um_files.remove(f.lower())
                p=True
            except KeyError:
                info.missing_files.append(f)
        info.is_present = p

    # any remaining files can be aggregated into 'Data'
    data_mod = VModInfo(
        name="Unmanaged Data",
        files=um_files, # anything left over,
        is_present = len(um_files) > 0,
        missing_files=[]
    )

    # return list of mod infos
    result = [skyrim_mod, *[dlc_mods[n] for n in skyinfo.all_dlc],
              data_mod]

    del skyinfo

    return result

