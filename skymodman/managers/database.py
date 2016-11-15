from pathlib import PurePath
from itertools import repeat
from collections import defaultdict, namedtuple

# from skymodman import exceptions
from skymodman.managers.base import Submanager, BaseDBManager

from skymodman.types import ModEntry
from skymodman.log import withlogger
from skymodman.utils import tree



# max number of vars for sqlite query is 999
_SQLMAX=900

# DB schema definition
# note -- if 'managed' is 0/False, the mod should be in <skyrim-install>/Data/
# rather than <mods-folder>/<directory>
# XXX: 'directory' should probably be renamed, then, since it's not accurate for unmanaged mods
#             ordinal   INTEGER unique, --mod's rank in the install order
#             error     INTEGER default 0 -- Type code for errors encountered during load
# name      TEXT,           --user-editable label for mod
#             modid     INTEGER,        --nexus id, or 0 if none
#             version   TEXT,           --arbitrary, set by mod author
#             enabled   INTEGER default 1,  --effectively a boolean value (0,1)
_SCHEMA = """
        CREATE TABLE mods (
            directory TEXT    unique, --folder on disk holding mod's files
            managed   INTEGER default 1  --boolean; is this in our mods folder?
        );
        CREATE TABLE hiddenfiles (
            directory TEXT REFERENCES mods(directory) DEFERRABLE INITIALLY DEFERRED,
                                -- the mod directory under which this file resides
            filepath      TEXT,      -- path to the file that has been hidden
            CONSTRAINT no_duplicates UNIQUE (directory, filepath) ON CONFLICT IGNORE
                --make sure we don't add the same file twice
        );
        CREATE TABLE modfiles (
            directory     TEXT REFERENCES mods(directory) DEFERRABLE INITIALLY DEFERRED, -- the mod directory under which this file resides
            filepath      TEXT,      -- path to the file
            CONSTRAINT no_duplicates UNIQUE (directory, filepath) ON CONFLICT IGNORE
                --make sure we don't add the same file twice
        );
        CREATE TABLE missingfiles (
            directory     TEXT REFERENCES mods(directory) DEFERRABLE INITIALLY DEFERRED, -- the mod directory under which this file should reside
            filepath      TEXT,      -- expected path to the file
            CONSTRAINT no_duplicates UNIQUE (directory, filepath) ON CONFLICT IGNORE
                --make sure we don't add the same file twice
        );
        """
# having the foreign key deferrable should prevent the db freaking
# out when we temporarily delete entries in 'mods' to modify the
# install order.


File_Conflict_Map = namedtuple("File_Conflict_Map", "by_file by_mod")

# from skymodman.utils import humanizer
# @humanizer.humanize
@withlogger
class DBManager(BaseDBManager, Submanager):

    def __init__(self, *args, **kwargs):
        super().__init__(db_path=":memory:", # create db in memory
                         schema=_SCHEMA,
                         # names of all tables
                         table_names=("mods", "modfiles", "hiddenfiles", "missingfiles"),
                         logger=self.LOGGER,
                         *args, **kwargs)

        # TODO: once we're testing this at scale (with real mods), we really should check the memory usage of the modfiles table...I wouldn't be suprised if it got enormous. Might want to consider using a disk-based db, in that case.

        self.LOGGER << "Initializing DBManager"

        # track which tables are currently empty
        self._empty = {tn:True for tn in self._tablenames}

        # self._con.set_trace_callback(print)

    ##=============================================
    ## Properties
    ##=============================================

    # @property
    # def mods(self):
    #     """
    #     :return: list of all mods from the mod db
    #     :rtype: list[sqlite3.Row]
    #     """
    #     return self.get_mod_info(True).fetchall()


    ######################
    ## Table management ##
    ######################

    def reinit(self, mods=True, files=True, hidden=True):
        """
        Drop the current tables and reinitialize as empty

        :param mods: If True, drop the mods table
        :param files: If True, drop the modfiles table
        :param hidden: If True, drop the hiddenfiles table
        """

        with self.conn:
            # take advantage of the "truncate optimization" feature in
            # sqlite to remove all rows quicker and easier than
            # dropping and recreating.

            # Apparently you can't use ? parameters for table names??!?

            # security???
            if mods and not self._empty['mods']:
                self.conn.execute("DELETE FROM mods")
                self._empty['mods'] = True

                # global _mcount
                # reset counter so that mod-ordinal is determined by the
                # order in which the entries are read from the file
                # _mcount = count()

            if files and not self._empty['modfiles']:
                self.conn.execute("DELETE FROM modfiles")
                self._empty['modfiles'] = True

            if files and not self._empty['missingfiles']:
                self.conn.execute("DELETE FROM missingfiles")
                self._empty['missingfiles'] = True

            if hidden and not self._empty['hiddenfiles']:
                self.conn.execute("DELETE FROM hiddenfiles")
                self._empty['hiddenfiles'] = True


            # if sky:
            #     # clear vanilla info if skyrim dir has changed
            #     self._vanilla_mod_info = []

    ##=============================================
    ## Table population
    ##=============================================

    def add_to_mods_table(self, mod_list):
        """
        Dynamically build the INSERT statement from the list of fields,
        then insert the values from mod_list (a sequence of tuples) into
        the database. The changes are committed after all values have
        been inserted.

        Does not check for an empty mods table.

        :param mod_list:
        """
        self.LOGGER << "<==Method call"

        # ignore the error field for now
        with self.conn:
            # insert the list of row-tuples into the in-memory db
            self.conn.executemany(
                "INSERT INTO mods({}) VALUES ({})".format(
                    ", ".join(ModEntry._fields),
                    ", ".join("?" * len(ModEntry._fields))
                ),
                mod_list)

            # mark db as initialized (if it wasn't already)
            self._empty['mods'] = False

    def populate_mods_table(self, mod_list):
        """Similar to add_to_mods_table, but this first checks to see if
        the mods table is empty before attempting to add any data to it.
        The method will fail if table already contains data."""

        if self._empty['mods']:
            self.add_to_mods_table(mod_list)
        else:
            self.LOGGER.error(
                "Attempted to populate non-empty table 'mods'.")

    # noinspection PyShadowingBuiltins
    def add_files(self, type, for_mod, files):
        """
        Record the list of filepaths in the database keyed by the mod
        with which they are associated. `type` indicates the context
        for the file list.

        :param type: a string that is either 'mod', 'missing', or 'hidden'
        :param for_mod:
        :param files: list of filepaths (as strings)
        """
        if files:
            table = type + "files"
            if table in self._tablenames:
                with self.conn:
                    self.conn.executemany(
                        "INSERT INTO " + table + " VALUES (?, ?)",
                        zip(repeat(for_mod), files))

                    self._empty[table] = False

    def remove_files(self, for_mod):
        """
        Remove all data rows from the modfiles table that belong to the
        specified mod

        :param for_mod: Name of mod's directory on disk (i.e. the ID
            under which they are keyed in the db)
        """
        if not self._empty['modfiles']:
            self.LOGGER << "Removing files for mod '{}' from database".format(
                for_mod)

            with self.conn:
                self.conn.execute(
                    "DELETE FROM modfiles WHERE directory = ?",
                    (for_mod,))

        if not self._empty['missingfiles']:
            with self.conn:
                self.conn.execute(
                    "DELETE FROM missingfiles WHERE directory = ?",
                    (for_mod,))

        if not self._empty['hiddenfiles']:
            with self.conn:
                self.conn.execute(
                    "DELETE FROM hiddenfiles WHERE directory = ?",
                    (for_mod,))

    ##=============================================
    ## DB Querying/analysis
    ## ---------------------
    ## Mostly convenenience methods
    ##=============================================

    def detect_file_conflicts(self):
        """
        Using the data in the 'modfiles' table, detect any file
        conflicts among the installed mods

        Note: this method causes an implicit COMMIT in the database.
        This is unlikely to be an issue, though, since we only call
        this before the user has actually had a chance to make any
        changes (or immediately after they've saved them)
        """

        # setup variables
        file = ''
        conflicts = defaultdict(list)
        mods_with_conflicts = defaultdict(list)

        # only run if there are actually any files to check
        if not self._empty['modfiles']:
            self.LOGGER.info("Detecting file conflicts")

            ## Ordinal is no longer stored in database;
            # the 'winning' mod will be determined elsewhere based
            # on dynamic ordering of mod collection

            # query for duplicates that doesn't use a custom view:
            for r in self.conn.execute("""
                SELECT f.filepath, f.directory
                    FROM modfiles f
                    INNER JOIN (
                        SELECT filepath, COUNT(*) AS C
                        FROM modfiles
                        GROUP BY filepath
                        HAVING C > 1
                    ) dups on f.filepath=dups.filepath
                    ORDER BY f.filepath, f.directory
                """):

                # detects when we 'switch' files
                if r['filepath'] != file:
                    file = r['filepath']

                # identity of mod containing this occurrence of 'file'
                mod = r['directory']

                # a dictionary of file conflicts to an ordered
                #  list of mods which contain them
                conflicts[file].append(mod)
                # also, a dictionary of mods to a list of conflicting files
                mods_with_conflicts[mod].append(file)
        else:
            self.LOGGER << "No entries present in modfiles table"

        # convert to normal dicts when adding to conflict map
        return File_Conflict_Map(
            by_file=dict(conflicts),
            by_mod=dict(mods_with_conflicts))

        # for c in mods_with_conflicts['Bethesda Hi-Res DLC Optimized']:
        #     print("other mods containing file '%s'" % c)
        #     for m in conflicts[c]:
        #         if m!='Bethesda Hi-Res DLC Optimized':
        #             print('\t', m)

    def find_matching_files(self, mod_key, pattern):
        """
        Yield files contained by the mod w/ directory `mod_key` that
        match the given SQL-wildcard `pattern` (for the "LIKE" operator)


        :return: list of matching files
        """

        # yield the first (and only) item of the 1-tuple returned
        # for each matching row in table--i.e. the path for each
        # matching file
        yield from (r[0] for r in self.conn.execute(
            "SELECT filepath FROM modfiles WHERE directory=? "
            "AND filepath LIKE ?", (mod_key, pattern)))

    ##=============================================
    ## Dealing with hidden files
    ## -----------------------------------
    ## conglomerate methods that deal w/ hidden files here
    ##=============================================

    def remove_hidden_files(self, mod_dir, file_list):
        """
        Remove the items (filepaths) in file list from the hiddenfiles
        db table. If `file_list` contains more than 900 items, they
        will be deleted in batches of 900 (999 is parameter
        limit in sqlite)

        :param mod_dir: directory name of the mod from which to delete
        :param file_list: list of files
        """

        _q = "DELETE FROM hiddenfiles" \
             " WHERE directory = '{mdir}'" \
             " AND filepath IN ({paths})"

        with self.conn as c:

            if len(file_list) <= _SQLMAX:
                # nothing special
                _q = _q.format(mdir=mod_dir,
                               paths=", ".join("?" * len(file_list)))
                c.execute(_q, file_list)
            else:
                # something special
                sections, remainder = divmod(len(file_list), _SQLMAX)
                for i in range(sections):
                    s = _SQLMAX * i
                    query = _q.format(mdir=mod_dir,
                                      paths=", ".join('?' * _SQLMAX))
                    c.execute(query, file_list[s:s + _SQLMAX])
                if remainder:
                    query = _q.format(mdir=mod_dir,
                                      paths=", ".join('?' * remainder))
                    c.execute(query, file_list[sections * _SQLMAX:])

        # return c

    def hidden_files(self, for_mod):
        """
        Obtain paths of currently hidden files for the given mod

        :param for_mod: directory name of the mod
        :return: the cursor of the executed command. can be used
            as an iterator.
        """

        return self.conn.execute(
            "SELECT filepath FROM hiddenfiles WHERE directory = ? ORDER BY filepath", (for_mod, )
        )

        # yield from (r["filepath"]
        #             for r in self.conn.execute(
        #     "SELECT filepath FROM hiddenfiles WHERE directory = ? ORDER BY filepath",
        #     (for_mod,)
        # ))

    def get_hidden_file_tree(self):
        """
        Return all hidden files for all mods as a tree structure
        (from utils.tree). The tree is non-flattened and convenient
        for serializing to disk w/ json.
        """

        # build a tree from the database
        htree = tree.Tree()

        for row in self.conn.execute(
                "SELECT * FROM hiddenfiles ORDER BY directory, filepath"):
            p = PurePath(row['directory'], row['filepath'])
            pathparts = p.parts[:-1]

            htree.insert(pathparts, p.name)

        return htree

    # def mods_with_error(self, error_type):
    #     """
    #     Fetches all mods from the db with the given ModError type
    #
    #     :param error_type:
    #     :return:
    #     """
    #
    #     yield from self.conn.execute(
    #         "SELECT * FROM mods WHERE error = ?", (error_type, ))


    # def validate_mods_list(self, managed_mods):
    #     """
    #     Compare the database's list of mods against a list of the
    #     folders in the installed-mods directory. Handle discrepancies by
    #     raising an Exception object containing two separate lists:
    #
    #         * Mods Not Listed: for mod directories found on disk but not
    #           previously listed in the user's list of installed mods
    #         * Mods Not Found: for mods listed in the list of installed
    #           mods whose installation folders were not found on disk.
    #
    #     :param list[str] managed_mods: list of all installed mods
    #     :return: True if no errors and table unchanged. False if errors
    #         encountered and/or removed from table
    #     """
    #
    #
    #     # I wish there were a...lighter way to do this, but I
    #     # believe only directly comparing dirnames will allow
    #     # us to provide useful feedback to the user about
    #     # problems with the mod installation
    #
    #     # reset the errors collection (set 'error' field to 0 for
    #     # every row where it is currently non-zero)
    #     num_removed = self.reset_errors()
    #
    #     self.logger.debug("Resetting mod errors: {} entries affected"
    #                       .format(num_removed))
    #
    #     dblist = [r["directory"] for r in
    #               self.conn.execute(
    #                   "SELECT directory FROM mods WHERE managed = 1")]
    #
    #     # make a copy of the mods list since we may be
    #     # modifying its contents
    #     im_list = managed_mods[:]
    #
    #     not_found = []
    #     not_listed = []
    #
    #     if len(dblist) > len(im_list):
    #         for modname in im_list:
    #             try:
    #                 dblist.remove(modname)
    #             except ValueError:
    #                 # if it's not listed in the db, note that
    #                 not_listed.append(modname)
    #         # anything left over is missing from the disk
    #         not_found = dblist
    #
    #     else: # len(dblist) <= len(managed_mod_folders):
    #         for modname in dblist:
    #             try:
    #                 im_list.remove(modname)
    #             except ValueError:
    #                 not_found.append(modname)
    #         # if everything matched, this should be empty
    #         not_listed = im_list
    #
    #     # i think inserting into the database is faster when done in
    #     # large chunks, so we accumulated the errors above and will
    #     # insert them all at once
    #     if not_listed:
    #         self._update_errors(ModError.MOD_NOT_LISTED, not_listed)
    #
    #     if not_found:
    #         self._update_errors(ModError.DIR_NOT_FOUND, not_found)
    #
    #     # return true only if all 3 are empty/0;
    #     # we return false on num_removed so that the GUI will
    #     # still update its contents
    #     return not (not_listed or not_found or num_removed)


    ##=============================================
    ## Data loading
    ##=============================================

    # def load_mod_info(self, json_source):
    #     """
    #     read the saved mod information from a json file and
    #     populate the in-memory database
    #
    #     :param str|Path json_source: path to modinfo.json file
    #     """
    #
    #     self.LOGGER << "<==Method call"
    #
    #     if not isinstance(json_source, Path):
    #         json_source = Path(json_source)
    #
    #     success = True
    #     with json_source.open('r') as f:
    #         # read from json file and convert mappings
    #         # to ordered tuples for sending to sqlite
    #         try:
    #             modentry_list = json.load(f, object_hook=_to_mod_entry)
    #             # mods = json.load(f, object_pairs_hook=_to_row_tuple)
    #             # self.add_to_mods_table(mods)
    #
    #         except json.decoder.JSONDecodeError:
    #             self.LOGGER.error("No mod information present in {}, "
    #                               "or file is malformed."
    #                               .format(json_source))
    #             success = False
    #         else:
    #             self._collection.extend(modentry_list)
    #
    #     # now get unmanaged mods
    #     if not self.load_unmanaged_mods():
    #         self.LOGGER.warning("Failed to load unmanaged data")
    #
    #     if success:
    #         # assuming the ModCollection and ModEntry classes are
    #         # written correctly... this should work just fine!
    #         self.populate_mods_table(self._collection)
    #         # self.add_to_mods_table(self._collection)
    #
    #     return success

    # def load_mod_info_from_disk(self, include_skyrim=True):
    #                             # save_modinfo=False):
    #     """
    #     scan the actual mods-directory and populate the database from
    #     there instead of a cached json file.
    #
    #     Will need to do this on first run and periodically to make sure
    #     cache is in sync.
    #
    #     :param include_skyrim:
    #     """
    #     # :param save_modinfo:
    #     # NTS: Perhaps this should be run on every startup? At least to make sure it matches the stored data.
    #
    #     if include_skyrim:
    #         self.load_unmanaged_mods()
    #
    #     # list of installed mod folders
    #     installed_mods = self.mainmanager.managed_mod_folders
    #
    #     if not installed_mods:
    #         self.LOGGER << "Mods directory empty"
    #     else:
    #
    #         mods_dir = self.mainmanager.Folders['mods']
    #
    #         if not mods_dir:
    #             self.LOGGER.error("Mod directory unset or invalid")
    #             return
    #
    #         mods_dir = mods_dir.path
    #
    #         # use config parser to read modinfo 'meta.ini' files, if present
    #         import configparser as _config
    #         configP = _config.ConfigParser()
    #
    #         # for managed mods, mod_key is the directory name
    #         for mod_key in installed_mods:
    #             mod_dir = mods_dir / mod_key
    #
    #             # support loading information read from meta.ini
    #             # (ModOrganizer) file
    #             meta_ini_path = mod_dir / "meta.ini"
    #
    #             if meta_ini_path.exists():
    #                 configP.read(str(meta_ini_path))
    #                 try:
    #                     modid = configP['General']['modid']
    #                     version = configP['General']['version']
    #                 except KeyError:
    #                     # if the meta.ini file was malformed or something,
    #                     # ignore it
    #                     add_me = _make_mod_entry(directory=mod_key,
    #                                                 managed=1)
    #                 else:
    #                     add_me = _make_mod_entry(directory=mod_key,
    #                                                 managed=1,
    #                                                 modid=modid,
    #                                                 version=version)
    #             else:
    #                 # no meta file
    #                 add_me = _make_mod_entry(directory=mod_key,
    #                                                 managed=1)
    #
    #             self._collection.append(add_me)
    #
    #         # get rid of import
    #         del _config
    #
    #         # finally, populate the table with the discovered mods
    #         self.populate_mods_table(self._collection)

            # if mods_list:
            #     self.add_to_mods_table(mods_list)
            # else:
                # self.LOGGER << "Mods directory empty"

    # def load_unmanaged_mods(self):
    #     """Check the skyrim/data folder for the vanilla game files, dlc,
    #     and any mods the user installed into the game folder manually."""
    #
    #     # um_mods = []
    #
    #     success = False
    #     if not self._vanilla_mod_info:
    #         skydir = self.mainmanager.Folders['skyrim']
    #         if skydir:
    #             self._vanilla_mod_info = vanilla_mods(skydir.path)
    #         else:
    #             self.LOGGER.warning << "Could not access Skyrim folder"
    #             # return False to indicate we couldn't load
    #             return False
    #
    #     # this lets us insert the items returned by vanilla_mods()
    #     # in the order in which they're returned, but ignoring any
    #     # items that may not be present
    #     default_order = count()
    #
    #     # noinspection PyTypeChecker
    #     present_mods = [t for t in self._vanilla_mod_info if
    #                     (t[0] == 'Skyrim' or t[1]['present'])]
    #
    #     # skyrim should be first item
    #     for m_name, m_info in present_mods:
    #
    #         # don't bother creating entries for mods already in coll;
    #         # 'skyrim' should always be 1st item, and should always not
    #         # be in the collection at this point; thus it will always
    #         # be inserted at index 0
    #         if m_name not in self._collection:
    #             self._collection.insert(
    #                 next(default_order),
    #                 _make_mod_entry(name=m_name,
    #                                 managed=0,
    #                                 # this is not exactly accurate...
    #                                 # I really need to change 'directory' to something else
    #                                 directory=m_name
    #                                 ))
    #             # set success True if we add at least 1 item to collection
    #             success=True
    #
    #     return success

    # def load_all_mod_files(self, mods_dir=None):
    #     """
    #     Here's an experiment to load ALL files from disk when the
    #     program starts up...let's see how long it takes
    #
    #     Update: about 12 seconds to load info for 223 mods from an
    #     ntfs-3g partition on a 7200rpm WD-Black...
    #     not the horriblest, but still likely needs to be shunted to
    #     another thread.  Especially since that was pretty much just
    #     reading file names; no operations such as checking for conflicts
    #     was done Also, dumping the db to disk (in txt form) made a
    #     2.7 MB file.
    #
    #     Update to update: 2nd time around, didn't even take 2 seconds. I
    #     did make some tweaks to the code, but still...I'm guessing the
    #     files were still in the system RAM?
    #
    #     """
    #
    #     if mods_dir:
    #         if isinstance(mods_dir, str):
    #             mods_dir = Path(mods_dir)
    #     else:
    #         mods_dir = self.mainmanager.Folders['mods'].path
    #         # verify that mods dir is set
    #         # if not mods_dir:
    #         #     raise exceptions.InvalidAppDirectoryError(
    #         #       keystrings.Dirs.MODS, mods_dir)
    #
    #     installed_mods = self.mainmanager.managed_mod_folders
    #
    #     # go through each folder individually
    #     with self.conn:
    #         for mdir in installed_mods:
    #             self.add_files_from_dir(mdir, str(mods_dir / mdir))
    #
    #     self._empty['modfiles'] = self.count("modfiles") < 1
    #
    #
    # def load_unmanaged_mod_files(self, skyrim_dir):
    #     """Record the files for the unmanaged 'Vanilla' files"""
    #
    #     if not self._vanilla_mod_info:
    #         self._vanilla_mod_info = vanilla_mods(skyrim_dir)
    #
    #     # noinspection PyTypeChecker
    #     present_mods = [t for t in self._vanilla_mod_info if
    #                     (t[0] == 'Skyrim' or t[1]['present'])]
    #
    #     # now add the files
    #     for m_name, m_info in present_mods:
    #         if m_info['files']:
    #             self.add_to_modfiles_table(m_name, m_info['files'])
    #
    #         # if we know that some files are missing, record that
    #         if m_info['missing']:
    #             self.add_to_missing_files_table(m_name,
    #                                             m_info['missing'])
    #
    #     self._empty['modfiles'] = self.count("modfiles") < 1
    #     self._empty['missingfiles'] = self.count("missingfiles") < 1

    # def add_files_from_dir(self, mod_name, mod_root):
    #     """
    #     Given a directory `mod_root` containing files for a mod named `mod_name`, add those files to the modfiles table.
    #     :param mod_name:
    #     :param str mod_root:
    #     :return:
    #     """
    #
    #     mfiles = []
    #     for root, dirs, files in os.walk(mod_root):
    #         # this gets the lowercase path to each file, starting at the
    #         # root of this mod folder. So:
    #         #   '/path/to/modstorage/CoolMod42/Meshes/WhatEver.NIF'
    #         # becomes:
    #         #   'meshes/whatever.nif'
    #         mfiles.extend(_relpath(
    #             _join(root, f), mod_root).lower() for f in files)
    #
    #     # put the mod's files in the db, with the mod name as the first
    #     # field (e.g. 'CoolMod42'), and the filepath as the second (e.g.
    #     # 'meshes/whatever.nif')
    #     if mfiles:
    #         with self.conn:
    #             self.conn.executemany(
    #                 "INSERT INTO modfiles VALUES (?, ?)",
    #                 zip(repeat(mod_name), mfiles))
    #             self._empty['modfiles'] = False

    ##=============================================
    ## Saving Data
    ##=============================================

    # def save_mod_info(self, json_target):
    #     """
    #     Write the data from the in-memory database to a
    #     json file on disk. The file will be overwritten, or
    #     created if it does not exist
    #
    #     :param str|Path json_target: path to modinfo.json file
    #     """
    #
    #     if not isinstance(json_target, Path):
    #         json_target = Path(json_target)
    #
    #     # we don't save the ordinal rank, so we need to get a list (set)
    #     # of the fields without "ordinal" Using sets here is OK because
    #     # field order doesn't matter when saving
    #     # noord_fields = set(_db_fields) - {db_fields.FLD_ORD,
    #     #                                  db_fields.FLD_ERR}
    #
    #     dbfields_noerr_noord=ModEntry._fields[:-1]
    #
    #     modinfo = []
    #
    #     # select (all fields other than ordinal & error)
    #     # from a subquery of (all fields ordered by ordinal).
    #     # ignore 'skyrim' mod
    #     for row in self.conn.execute(
    #             "SELECT {} FROM (SELECT * FROM mods WHERE directory != 'Skyrim' ORDER BY ordinal)"
    #                     .format(", ".join(dbfields_noerr_noord))):
    #         # then, for each row (mod entry),
    #         # zip fields names and values up and convert to dict
    #         # to create json-able object
    #         modinfo.append(dict(zip(dbfields_noerr_noord, row)))
    #
    #     with json_target.open('w') as f:
    #         json.dump(modinfo, f, indent=1)
    #

    # def load_hidden_files(self, json_source):
    #     """
    #
    #     :param str|Path json_source:
    #     :return: success of operation
    #     """
    #     self.LOGGER.info("Analyzing hidden files")
    #
    #     if not isinstance(json_source, Path):
    #         json_source = Path(json_source)
    #     success = False
    #
    #     with json_source.open('r') as f:
    #         try:
    #             hiddenfiles = json.load(f)
    #             if hiddenfiles:
    #                 # if there were any listed, mark table non-empty
    #                 self._empty['hiddenfiles'] = False
    #
    #                 for mod, files in hiddenfiles.items():
    #                     # gethiddenfiles returns a list of 1-tuples,
    #                     # each one with a filepath
    #                     hfiles = self._gethiddenfiles(files, "", [])
    #
    #                     # we're committing to the db after each mod is
    #                     # handled; waiting until the end might speed
    #                     # things up, but doing it this way means that
    #                     # if there's a problem with one of the mods, we
    #                     # only rollback that one transaction instead of
    #                     # losing the info for EVERY mod. Savepoints may
    #                     # be another approach.
    #                     with self._con:
    #                         self._con.executemany(
    #                             "INSERT INTO hiddenfiles VALUES (?, ?)",
    #                             zip(repeat(mod), hfiles))
    #
    #             # [print(*r, sep="\t|\t") for r in
    #             #  self._con.execute("select * from hiddenfiles")]
    #             success = True
    #
    #         except json.decoder.JSONDecodeError:
    #             self.LOGGER.warning("No hidden files listed in {}, "
    #                                 "or file is malformed."
    #                                 .format(json_source))
    #
    #     return success
    #
    # def _gethiddenfiles(self, basedict, currpath, flist,
    #                     join=os.path.join):
    #     """
    #     Recursive helper for loading the list of hiddenfiles from disk
    #
    #     :param basedict:
    #     :param currpath:
    #     :param flist:
    #     :param join: speed up execution by locally binding os.path.join
    #     :return: list of hidden files
    #     """
    #     for key, value in basedict.items():
    #         if isinstance(value, list):
    #             flist.extend(join(currpath, fname) for fname in value)
    #         else:
    #             flist = self._gethiddenfiles(value, join(currpath, key),
    #                                          flist)
    #
    #     return flist

    # def save_hidden_files(self):
    #     """
    #     Save the contents of the hiddenfiles table to the
    #     `hiddenfiles.json` file of the current profile
    #
    #     :return:
    #     """
    #     if self.mainmanager.profile:
    #         self.save_hidden_files_to(
    #             self.mainmanager.profile.hidden_files)
    #
    # def save_hidden_files_to(self, json_target):
    #     """
    #     Serialize the contents of the hiddenfiles table to a file in
    #     json format
    #
    #     :param str|Path json_target: path to hiddenfiles.json file
    #         for current profile
    #     """
    #
    #     # NTS: I notice ModOrganizer adds a '.mohidden' extension to every file it hides (or to the parent directory); hmm...I'd like to avoid changing the files on disk if possible
    #
    #     if not isinstance(json_target, Path):
    #         json_target = Path(json_target)
    #
    #     # build a tree from the database and jsonify it to disk
    #     htree = tree.Tree()
    #
    #     for row in self.conn.execute(
    #             "SELECT * FROM hiddenfiles ORDER BY directory, filepath"):
    #         p = PurePath(row['directory'], row['filepath'])
    #         pathparts = p.parts[:-1]
    #
    #         htree.insert(pathparts, p.name)
    #
    #     with json_target.open('w') as f:
    #         f.write(str(htree))
    #
    #         # print(tree.to_string(2))

##=============================================
## Module-level methods (should maybe be static?)
##=============================================

# def _to_row_tuple(pairs):
#     """
#     Used as object_pair_hook for json.load(). Takes the mod
#     information loaded from the json file and converts it
#     to a tuple of just the field values in the
#     correct order for feeding to the sqlite database.
#
#     :param typing.Sequence[tuple[str, Any]] pairs:
#     :return: Tuple containing just the values of the fields
#     # """
#     # print(dict(pairs))
#     # value for ordinal is taken from global incrementer as it is not
#     # stored in the modinfo file and is instead dependent on the
#     # order in which items are read from said file
#     return _row_tuple(ordinal=next(_mcount), **dict(pairs))


        # return (next(_mcount),) + tuple(
        #     s[1] for s in sorted(pairs,
        #                          key=lambda p: db_field_order[p[0]]))

# def _row_tuple(**kwargs):
#     """Pulls value from supplied keyword arguments (generated from the
#     on-disk json file), supplementing any missing fields with default
#     values."""
#     return tuple(kwargs.get(field, _defaults.get(
#                              field, lambda v: "")(kwargs))
#                              for field in db_fields_noerror)

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
#         ) for field in _db_fields)
#
#
#
