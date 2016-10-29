import itertools

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

        # number of mods currently having errors
        num_errors = len(self._errors)
        self._errors.clear()

        # return True if some mods had errors (but now do not)
        return num_errors

    ##=============================================
    ## Mod-trait queries
    ##=============================================

    def enabled_mods(self):
        return filter(lambda m: m.enabled, self._collection)

    def disabled_mods(self):
        return itertools.filterfalse(lambda m: m.managed,
                                     self._collection)

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

