import json
import json.decoder
import os
import itertools

from pathlib import Path
from collections import namedtuple

from skymodman import exceptions
# from skymodman.constants import ModError
from skymodman.managers.base import Submanager
from skymodman.log import withlogger
from skymodman.types import ModEntry

_relpath = os.path.relpath
_join = os.path.join

_mod_fields = ModEntry._fields

_defaults = {
    "name": lambda v: v["directory"],
    "modid": lambda v: 0,
    "version": lambda v: "",
    "enabled": lambda v: 1,
    "managed": lambda v: 1,
    # "error": lambda v: ModError.NONE
}

@withlogger
class IOManager(Submanager):
    """Contains methods dealing with the reading and writing
    of application data to/from the user's hard-disk"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.LOGGER << "Initializing DiskManager"


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

    def load_raw_mod_info(self, container, include_skyrim=True):
                                # save_modinfo=False):
        """
        scan the actual mods-directory and populate the database from
        there instead of a cached json file.

        Will need to do this on first run and periodically to make sure
        cache is in sync.

        :param include_skyrim:
        :param container:
        """
        # :param save_modinfo:
        # NTS: Perhaps this should be run on every startup? At least to make sure it matches the stored data.

        if include_skyrim:
            self.load_unmanaged_mods()

        # list of installed mod folders
        installed_mods = self.mainmanager.managed_mod_folders

        if not installed_mods:
            self.LOGGER << "Mods directory empty"
            return False

        mods_dir = self.mainmanager.Folders['mods']

        if not mods_dir:
            self.LOGGER.error("Mod directory unset or invalid")
            return False

        mods_dir = mods_dir.path

        # use config parser to read modinfo 'meta.ini' files, if present
        import configparser as _config
        configP = _config.ConfigParser()

        # for managed mods, mod_key is the directory name
        for mod_key in installed_mods:
            mod_dir = mods_dir / mod_key

            # support loading information read from meta.ini
            # (ModOrganizer) file
            # TODO: check case-insensitively
            meta_ini_path = mod_dir / "meta.ini"

            if meta_ini_path.exists():
                configP.read(str(meta_ini_path))
                try:
                    modid = configP['General']['modid']
                    version = configP['General']['version']
                except KeyError:
                    # if the meta.ini file was malformed or something,
                    # ignore it
                    add_me = _make_mod_entry(directory=mod_key,
                                                managed=1)
                else:
                    add_me = _make_mod_entry(directory=mod_key,
                                                managed=1,
                                                modid=modid,
                                                version=version)
            else:
                # no meta file
                add_me = _make_mod_entry(directory=mod_key,
                                                managed=1)

            container.append(add_me)

        # get rid of import
        del _config

        return True

        # finally, populate the table with the discovered mods
        # self.populate_mods_table(self._collection)

    ##=============================================
    ## Loading file lists
    ##=============================================

    def load_all_mod_files(self):
        """
        This generates tuples of the form
        (mod_key, [list of files in mod]). One can iterate over this
        generator to get all files on disk.
        """

        mods_dir = self.mainmanager.Folders['mods'].path

        # use the list of on-disk mods from manager (rather than
        # the 'theoretical' list of mods in the mod collection)
        installed = self.mainmanager.managed_mod_folders


        for mdir in installed:

            # abs-path to each directory
            mroot = str(mods_dir / mdir)

            mfiles = []
            # this gets the lowercase path to each file, starting at the
            # root of this mod folder. So:
            #   '/path/to/modstorage/CoolMod42/Meshes/WhatEver.NIF'
            # becomes:
            #   'meshes/whatever.nif'
            for root, dirs, files in os.walk(mroot):
                mfiles.extend(_relpath(
                    _join(root, f), mroot).lower() for f in files)

            yield (mdir, mfiles)

    def load_unmanaged_files(self):
        """Yield the files for the unamanged 'Vanilla' mods and any other
        files found in the Skyrim Data directory


        Yielded tuples have 3 fields:
            0) Mod name
            1) list of files found
            2) list of files that were expected but not found (missing files)


        The second and third fields may be empty lists depending on what
        was found on disk.
        """

        if not self._vanilla_mod_info:
            self._vanilla_mod_info = vanilla_mods(
                self.mainmanager.Folders['skyrim'].path)

        for m in filter(lambda vmi: vmi.is_present,
                              self._vanilla_mod_info):
            if m.files or m.missing_files:
                yield (m.name, m.files, m.missing_files)

    ##=============================================
    ## loading list of hidden files
    ##=============================================

    def load_hidden_files(self, json_source):
        """

        :param json_source:
        """
        if not isinstance(json_source, Path):
            json_source = Path(json_source)
        # success = False

        with json_source.open('r') as f:
            try:
                # due to the way we saved the hidden files, this
                # loads a nested dict structure. The top-level keys
                # are the names of mods (directories); the values for
                # these are nested (tree-like) dicts where each value
                # is either a dict
                # or a list; if the value is a dict, then the key for
                # that value is a directory name and the contents of
                # the value-dict are the contents of the directory. If value
                # is a list, then the items of that list are the regular
                # files (i.e. non-directories) within the current
                # directory
                hidden_files = json.load(f)
            except json.decoder.JSONDecodeError:
                self.LOGGER.warning("No hidden files listed in {}, "
                                   "or file is malformed."
                                   .format(json_source))
            else:
                if hidden_files:

                    # initialize variable
                    hfilelist = [] # type: list [str]

                    # recursive method to flatten the nested dictionary
                    # into a list of filepaths (strings)
                    def extract_paths(from_dict, parent_path):
                        for key, value in from_dict.items():

                            # if this is the list of files
                            if isinstance(value, list):
                                # extend hidden_file list w/ 'flattened'
                                # paths to these files
                                hfilelist.extend(
                                    _join(parent_path, file_name)
                                    for file_name in value)
                            else:
                                # it must be a dictionary representing
                                # a sub-directory; recurse!
                                extract_paths(value, _join(parent_path, key))

                    # iter over top-level items
                    for mod, contents in hidden_files.items(): # type: str, dict
                        # reset list
                        hfilelist = [] # type: list [str]
                        # start extraction with no parent path
                        extract_paths(contents, "")

                        # yield name of mod, hidden file list
                        yield mod, hfilelist


    ##=============================================
    ## Writing Data
    ##=============================================

    def save_mod_info(self, json_target, mod_container):
        """

        :param str|Path json_target:
        :param mod_container: an in-order sequence of ModEntry objects
        """

        if not isinstance(json_target, Path):
            json_target = Path(json_target)

        # create list of mods as dicts (actually Ordered dicts)
        ## note -- ignore 'Skyrim' fakemod (always first in list)
        modinfo=[me._asdict() for me in mod_container if me.directory != 'Skyrim']

        with json_target.open('w') as f:
            # NTS: maybe remove the indent when shipping (for space)
            json.dump(modinfo, f, indent=1)

    @staticmethod
    def json_write(json_target, pyobject, indent=0):
        """Dump the given object to a json file specified by the given
        Path object.

        :param Path json_target:
        :param pyobject:
        """
        with json_target.open('w') as f:
            if indent:
                json.dump(pyobject, f, indent=indent)
            else:
                json.dump(pyobject, f)








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
        files=sorted([*skyinfo.masters, *skyinfo.skyrim_archives], key=lambda p:p.lower()),
        missing_files=[]
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
            files=sorted([n+".esm", n+".bsa"], key=lambda p:p.lower()),
            is_present=False, # set to True if dlc is installed
            missing_files=[] # if the dlc is Partially present,
                             # record missing files
        )

    # hi-res packs
    for n in skyinfo.all_dlc[3:]:
        dlc_mods[n] = VModInfo(
            name=n,
            files=sorted([n + ".esp", n + ".bsa"], key=lambda p:p.lower()),
            is_present=False,
            missing_files=[]
        )

    for dlc, info in dlc_mods.items():
        isp = False # present?
        for f in info.files:
            try:
                um_files.remove(f.lower())
                isp=True
            except KeyError:
                info.missing_files.append(f)

        dlc_mods[dlc] = info._replace(is_present=isp)
        # info.is_present = p

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

