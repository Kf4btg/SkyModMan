import itertools

from skymodman.constants import ModError
from skymodman.managers.base import Submanager
from skymodman.log import withlogger
from skymodman.types import ModEntry, ModCollection

@withlogger
class ModCollectionManager(Submanager):
    """Creates the ModCollection instance that will be used by the rest
    of the application. Provides methods to validate the list of mods,
    query enabled and managed states, and tracks errors encountered
    during mod-loading."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.LOGGER << "Initializing ModCollectionManager"

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
        """

        :return: an iterator over all currently enabled mods in the
            collection
        """
        return filter(lambda m: m.enabled, self._collection)

    def disabled_mods(self):
        """

        :return: an iterator over all currently disabled mods in the
            collection
        """
        return itertools.filterfalse(lambda m: m.managed,
                                     self._collection)

    def managed_mods(self):
        """
        Iterate over all mods marked as "managed"
        """
        return filter(lambda m: m.managed, self._collection)

    def unmanaged_mods(self):
        """
        Iterate over all mods marked as "unmanaged"
        """
        return itertools.filterfalse(lambda m: m.managed,
                                     self._collection)

    def mods_with_error(self, error_type):
        """
        Yield all mods that currently have the given `error_type`

        :param ModError error_type:
        """
        yield from (m for m in self._collection
                    if m.key in self._errors
                    and self._errors[m.key]==error_type)

    ##=============================================
    ## validation
    ##=============================================

    def validate_mods(self, managed_mods_list):
        """
        Compare the mods held in the collection with
        `managed_mods_list`, a list of the mods actually present on disk
        in the mod-installation directory.

        Handle discrepancies by storing the type of error in the
        mapping 'errors', keyed with the unique-name of the mod.

        Error types are:

            * Mods Not Listed: for mod directories found on disk but not
              previously listed in the user's list of installed mods
            * Mods Not Found: for mods listed in the list of installed
              mods whose installation folders were not found on disk.

        :return: a 3-tuple of integers. Values are (number of errors
            cleared, number of new errors, bitwise-or combo of error-
            types encountered). Obviously an ideal result would be
            (0, 0, 0).
        """
        # :return: True ONLY if no errors were known before this method
        #     was called and no errors were found during execution. Always
        #     returns False if any errors were present before this and/or
        #     errors were found by this call. This is intended to serve
        #     as a notification that errors are either present or changed,
        #     so any interface can be updated accordingly/

        # reset error field to None
        errors_cleared = self.clear_errors()

        # list of mods marked as 'managed' in the collection
        in_coll = [m.directory for m in self.managed_mods()]

        # make a copy of the list of mods-on-disk since we may be
        # modifying its contents
        on_disk = managed_mods_list[:]

        # helps keep things shorter
        eDNF = ModError.DIR_NOT_FOUND
        eMNL = ModError.MOD_NOT_LISTED

        # errors-discovered mapping
        errmap = {eDNF: [], eMNL: []}

        #! note:: I wish there were a...lighter way to do this, but I
        #! believe only directly comparing dirnames will allow
        #! us to provide useful feedback to the user about
        #! problems with the mod installation

        # we always iterate over the smaller list, attempting
        # to remove all the files in it from the larger one. Which
        # list we're iterating over determines which error-list we
        # append to on error.
        if len(in_coll) > len(on_disk):
            l_smaller = on_disk
            l_larger = in_coll
            receive_errors = errmap[eMNL]
            leftovers = eDNF

        else:
            l_smaller = in_coll
            l_larger = on_disk
            receive_errors = errmap[eDNF]
            leftovers = eMNL

        ## perform iteration/error-determination ##
        for modname in l_smaller:
            try:
                l_larger.remove(modname)
            except ValueError:
                receive_errors.append(modname)
        # anything left in the larger list belongs
        # to the other error type;
        errmap[leftovers] = l_larger

        # value to return for types of errors encountered
        err_types = ModError.NONE

        if errmap[eMNL]:
            err_types |= eMNL
            # if any non-listed mods were discovered, add them to the
            # end of the collection
            self.LOGGER.warning("Unlisted mod(s) found in mod directory")
            for modentry in \
                    self.mainmanager.IO.create_mods_from_directories(
                        errmap[eMNL]):
                self._collection.append(modentry)

            # update errors collection;
            # self._errors is keyed with the mod-key, and each value is
            # the appropriate ModError type
            self._errors.update(dict.fromkeys(errmap[eMNL], eMNL))

        if errmap[eDNF]:
            err_types |= eDNF
            # update errors collection;
            self._errors.update(dict.fromkeys(errmap[eDNF], eDNF))


        return errors_cleared, len(self._errors), err_types

        # return True iff no errors were found or cleared
        # return not (self._errors or errors_cleared)

