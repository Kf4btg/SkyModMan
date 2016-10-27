import json
import json.decoder
import os

from pathlib import Path, PurePath

from skymodman.constants import  ModError
from skymodman.managers.base import Submanager
from skymodman.log import withlogger
from skymodman.types import ModEntry, ModCollection

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
class ModCollectionManager(Submanager):
    """Intended to replace (at least some) of the database manager"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._collection = ModCollection()

        ModEntry.collection = self._collection


    @property
    def collection(self):
        return self._collection


    def reset(self):
        self._collection.clear()


    ##=============================================
    ## Mod-trait queries
    ##=============================================

    def enabled_mods(self, names_only = False):

        if names_only:
            yield from (m.name for m in self._collection if m.enabled)

        else:
            yield from (m for m in self._collection if m.enabled)

    ##=============================================
    ## Loading
    ##=============================================


    def load_saved_modlist(self, json_source):
        """
        read the saved mod information from a json file and
        populate the mod collection

        :param str|Path json_source: path to modinfo.json file
        """

        self.LOGGER << "<==Method call"

        if not isinstance(json_source, Path):
            json_source = Path(json_source)

        success = True
        with json_source.open('r') as f:
            # read from json file and convert mappings
            # to ordered tuples for sending to sqlite
            try:
                modentry_list = json.load(f, object_hook=_to_mod_entry)
                # mods = json.load(f, object_pairs_hook=_to_row_tuple)
                # self.add_to_mods_table(mods)

            except json.decoder.JSONDecodeError:
                self.LOGGER.error("No mod information present in {}, "
                                  "or file is malformed."
                                  .format(json_source))
                success = False
            else:
                self._collection.extend(modentry_list)

        # now get unmanaged mods
        if not self.load_unmanaged_mods():
            # TODO: figure out what to do in this case; does this need to be in a separate method that is called individually by the Manager?
            self.LOGGER.warning("Failed to load unmanaged data")


        return success




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