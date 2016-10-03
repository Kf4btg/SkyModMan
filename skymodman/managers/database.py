import json
import json.decoder
import os

from pathlib import Path, PurePath
from itertools import count, repeat
from collections import defaultdict, namedtuple

from skymodman import exceptions
from skymodman.managers.base import Submanager, BaseDBManager
from skymodman.constants import (db_fields, db_fields_noerror,
                                 db_field_order, ModError, keystrings)
from skymodman.log import withlogger
from skymodman.utils import tree

_mcount = count()

# max number of vars for sqlite query is 999
_SQLMAX=900

# DB schema definition
_SCHEMA = """
        CREATE TABLE mods (
            ordinal   INTEGER unique, --mod's rank in the install order
            directory TEXT    unique, --folder on disk holding mod's files
            name      TEXT,           --user-editable label for mod
            modid     INTEGER,        --nexus id, or 0 if none
            version   TEXT,           --arbitrary, set by mod author
            enabled   INTEGER default 1,  --effectively a boolean value (0,1)
            managed   INTEGER default 1,  --boolean; is this in our mods folder?
            error     INTEGER default 0 -- Type code for errors encountered during load
        );
        CREATE TABLE hiddenfiles (
            directory TEXT REFERENCES mods(directory) DEFERRABLE INITIALLY DEFERRED,
                                -- the mod directory under which this file resides
            filepath      TEXT      -- path to the file that has been hidden
        );
        CREATE TABLE modfiles (
            directory     TEXT REFERENCES mods(directory) DEFERRABLE INITIALLY DEFERRED, -- the mod directory under which this file resides
            filepath      TEXT      -- path to the file
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

    __defaults = {
        "name": lambda v: v["directory"],
        "modid": lambda v: 0,
        "version": lambda v: "",
        "enabled": lambda v: 1,
        "managed": lambda v: 1,
    }
        # "error": lambda v: ModError.NONE

    def __init__(self, *args, **kwargs):
        super().__init__(db_path=":memory:", # create db in memory
                         schema=_SCHEMA,
                         # names of all tables
                         table_names=("mods", "modfiles", "hiddenfiles"),
                         logger=self.LOGGER,
                         *args, **kwargs)

        # indicates if fill_mods_table() has ever been called
        self._initialized = False

        # track which tables are currently empty
        self._empty = {tn:True for tn in self._tablenames}

        # self._con.set_trace_callback(print)

        # These are created from the database, so it seems like it may
        # be best just to store them in this class:

        # initialize empty file conflict map
        self._conflict_map = File_Conflict_Map({},{})

        ## {filepath:[list of mods containing that file]}
        # self._file_conflicts = defaultdict(list)
        ## {mod:[contained files that are in conflict with other mods]}
        # self.mods_with_conflicting_files = defaultdict(list)


    ################
    ## Properties ##
    ################

    @property
    def mods(self):
        """
        :return: list of all mods from the mod db
        :rtype: list[sqlite3.Row]
        """
        return self.get_mod_info(True).fetchall()

    @property
    def is_initialized(self):
        return self._initialized

    @property
    def file_conflicts(self):
        """
        Return an object containing information about conflicting files.
        Use as follows:

            * file_conflicts.by_file: dict[str, list[str]] -- a mapping
                of file paths to a list of mods containing a file with
                the same file path
            * file_conflicts.by_mod: dict[str, list[str]] -- a mapping
                of mod names to a list of files contained by that mod
                which are in conflict with some other mod.


        :return:
        """
        # return self._file_conflicts
        return self._conflict_map


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

        # self.LOGGER.debug("dropping mods table")


        with self.conn:
            # take advantage of the "truncate optimization" feature in sqlite
            # to remove all rows quicker and easier than dropping and recreating.

            # self._con.execute("DELETE FROM ?", self._tablenames)
            # Apparently you can't use ? parameters for table names??!?!?
            # for n in self._tablenames:
            #     self._con.execute("DELETE FROM {table}".format(table=n))

            # security???
            if mods and not self._empty['mods']:
                self.conn.execute("DELETE FROM mods")
                self._empty['mods'] = True

                global _mcount
                # reset counter so that mod-ordinal is determined by the order
                # in which the entries are read from the file
                _mcount = count()

            if files and not self._empty['modfiles']:
                self.conn.execute("DELETE FROM modfiles")
                self._empty['modfiles'] = True

            if hidden and not self._empty['hiddenfiles']:
                self.conn.execute("DELETE FROM hiddenfiles")
                self._empty['hiddenfiles'] = True

    def reset_errors(self):
        """
        Reset the "error" column for each mod to ModError.None
        and commit the changes

        :return: the number of rows affected
        """

        with self.conn:
            return self.conn.execute(
                "UPDATE mods SET error = 0 WHERE error != 0").rowcount

    ##################
    ## DATA LOADING ##
    ##################

    def load_mod_info(self, json_source):
        """
        read the saved mod information from a json file and
        populate the in-memory database

        :param str|Path json_source: path to modinfo.json file
        """


        if not isinstance(json_source, Path):
            json_source = Path(json_source)

        success = True
        with json_source.open('r') as f:
            # read from json file and convert mappings
            # to ordered tuples for sending to sqlite
            try:
                mods = json.load(f, object_pairs_hook=DBManager.to_row_tuple)
                self.fill_mods_table(mods)

            except json.decoder.JSONDecodeError:
                self.LOGGER.error("No mod information present in {}, "
                                  "or file is malformed."
                                  .format(json_source))
                success = False
        return success


    def load_hidden_files(self, json_source):
        """

        :param str|Path json_source:
        :return: success of operation
        """
        self.LOGGER.info("Analyzing hidden files")

        if not isinstance(json_source, Path):
            json_source = Path(json_source)
        success = False

        with json_source.open('r') as f:
            try:
                hiddenfiles = json.load(f)
                if hiddenfiles:
                    # if there were any listed, mark table non-empty
                    self._empty['hiddenfiles'] = False

                    for mod, files in hiddenfiles.items():
                        # gethiddenfiles returns a list of 1-tuples,
                        # each one with a filepath
                        hfiles = self._gethiddenfiles(files, "", [])

                        # we're committing to the db after each mod is
                        # handled; waiting until the end might speed things
                        # up, but doing it this way means that if there's a
                        # problem with one of the mods, we only rollback
                        # that one transaction instead of losing the info
                        # for EVERY mod. Savepoints may be another approach.
                        with self._con:
                            self._con.executemany(
                                "INSERT INTO hiddenfiles VALUES (?, ?)",
                                zip(repeat(mod), hfiles)
                            )

                # [print(*r, sep="\t|\t") for r in
                #  self._con.execute("select * from hiddenfiles")]
                success=True

            except json.decoder.JSONDecodeError:
                self.LOGGER.warning("No hidden files listed in {}, "
                                    "or file is malformed."
                                    .format(json_source))

        return success

    def _gethiddenfiles(self, basedict, currpath, flist, join=os.path.join):
        """
        Recursive helper for loading the list of hiddenfiles from disk

        :param basedict:
        :param currpath:
        :param flist:
        :param join: speed up execution by locally binding os.path.join
        :return: list of hidden files
        """
        for key, value in basedict.items():
            if isinstance(value, list):
                flist.extend(join(currpath, fname) for fname in value)
            else:
                flist = self._gethiddenfiles(value, join(currpath, key), flist)

        return flist
    ###################################

    def save_hidden_files(self):
        """
        Save the contents of the hiddenfiles table to the
        `hiddenfiles.json` file of the current profile

        :return:
        """
        if self.mainmanager.profile:
            self.save_hidden_files_to(self.mainmanager.profile.hidden_files)


    def save_hidden_files_to(self, json_target):
        """
        Serialize the contents of the hiddenfiles table to a file in
        json format

        :param str|Path json_target: path to hiddenfiles.json file for current profile
        """

        # Note: I notice ModOrganizer adds a '.mohidden' extension to every file it hides (or to the parent directory); hmm...I'd like to avoid changing the files on disk if possible

        if not isinstance(json_target, Path):
            json_target = Path(json_target)

        # build a tree from the database and jsonify it to disk
        htree = tree.Tree()

        for row in self.conn.execute(
            "SELECT * FROM hiddenfiles ORDER BY directory, filepath"):
            p = PurePath(row['directory'], row['filepath'])
            pathparts = p.parts[:-1]

            htree.insert(pathparts, p.name)

        with json_target.open('w') as f:
            f.write(str(htree))

        # print(tree.to_string(2))

    def remove_hidden_files(self, mod_dir, file_list):
        """
        Remove the items (filepaths) in file list from the hiddenfiles
        db table. If `file_list` contains more than 900 items, they
        will be deleted in batches of 900 (999 is parameter
        limit in sqlite)

        :param mod_dir: directory name of the mod from which to delete
        :param file_list: list of files
        """

        self.checktx()

        _q = "DELETE FROM hiddenfiles" \
             " WHERE directory = '{mdir}'" \
             " AND filepath IN ({paths})"

        c = self.conn.cursor()

        if len(file_list) <= _SQLMAX:
            # nothing special
            _q=_q.format(mdir=mod_dir,
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

        return c

    def files_hidden(self, for_mod):
        """
        Yield paths of currently hidden files for the given mod

        :param for_mod: directory name of the mod
        """

        yield from (r["filepath"]
                    for r in self.conn.execute(
            "SELECT * FROM hiddenfiles WHERE directory = ?",
            (for_mod, )
        ))

    # def fill_mods_table(self, mod_list, doprint=False):
    def fill_mods_table(self, mod_list):
        """
        Dynamically build the INSERT statement from the list of fields,
        then insert the values from mod_list (a list of tuples) into
        the database. The changes are committed after all values have
        been insterted

        :param Iterable[tuple] mod_list:
        """

        if not self._empty['mods']:
            raise exceptions.DatabaseError("Attempted to populate "
                                           "non-empty table 'mods'")

        # ignore the error field for now
        with self.conn:
            # insert the list of row-tuples into the in-memory db
            self.conn.executemany(
                "INSERT INTO mods({}) VALUES ({})".format(
                    ", ".join(db_fields_noerror),
                    ", ".join("?" * len(db_fields_noerror))
                ),
                mod_list)

            # mark db as initialized (if it wasn't already)
            self._empty['mods'] = False

    ############
    ## Saving ##
    ############

    def save_mod_info(self, json_target):
        """
        Write the data from the in-memory database to a
        json file on disk. The file will be overwritten, or
        created if it does not exist

        :param str|Path json_target: path to modinfo.json file
        """

        if not isinstance(json_target, Path):
            json_target = Path(json_target)

        # we don't save the ordinal rank, so we need to get a list (set)
        # of the fields without "ordinal" Using sets here is OK because
        # field order doesn't matter when saving
        noord_fields = set(db_fields) - {db_fields.FLD_ORD, db_fields.FLD_ERR}

        modinfo = []

        # select (all fields other than ordinal & error)
        # from a subquery of (all fields ordered by ordinal).
        for row in self.conn.execute(
                "SELECT {} FROM (SELECT * FROM mods ORDER BY ordinal)"
                        .format(", ".join(noord_fields))):

            # then, for each row (mod entry),
            # zip fields names and values up and convert to dict
            # to create json-able object
            modinfo.append(dict(zip(noord_fields, row)))

        with json_target.open('w') as f:
            json.dump(modinfo, f, indent=1)


    # db-query convenience methods
    def enabled_mods(self, name_only = False):
        """
        Fetches all mods from the mod database that are marked as enabled.

        :param name_only: Return only the names of the mods
        :return:
        :rtype: typing.Generator[str|tuple, Any, None]
        """
        if name_only:
            yield from (t[0] for t in
                        self.conn.execute(
                            "SELECT name FROM mods WHERE enabled = 1"))
        else:
            yield from self.conn.execute(
                "SELECT * FROM mods WHERE enabled = 1")

    def disabled_mods(self, name_only = False):
        """
        Fetches all mods from the mod database that are marked as disabled.

        :param name_only: Return only the names of the mods
        :return:
        :rtype: typing.Generator[str|tuple, Any, None]
        """
        if name_only:
            yield from (t[0] for t in
                        self.conn.execute(
                            "SELECT name FROM mods WHERE enabled = 0"))
        else:
            yield from self.conn.execute(
                                "SELECT * FROM mods WHERE enabled = 0")

    def mods_with_error(self, error_type):
        """
        Fetches all mods from the db with the given ModError type

        :param error_type:
        :return:
        """

        yield from self.conn.execute(
            "SELECT * FROM mods WHERE error = ?", (error_type, ))

    def get_mod_info(self, raw_cursor = False) :
        """
        Yields Row objects containing all information about installed mods

        :param raw_cursor: If true, return the db cursor object instead of yielding Rows
        :return:   Tuple of mod info or sqlite3.cursor
        :rtype: __generator[sqlite3.Row, Any, None]|sqlite3.Cursor
        """
        cur = self.conn.execute("SELECT * FROM mods")
        if raw_cursor:
            return cur
        yield from cur


    def get_mod_data_from_directory(self, mods_dir):
        """
        scan the actual mods-directory and populate the database from
        there instead of a cached json file.

        Will need to do this on first run and periodically to make sure
        cache is in sync.

        """
        # TODO: Perhaps this should be run on every startup? At least to make sure it matches the stored data.

        # mods_dir = self.mainmanager.get_directory(keystrings.Dirs.MODS,
        #                                           aspath=True)

        # list of installed mod folders
        installed_mods = self.mainmanager.installed_mods

        import configparser as _config

        self.logger.info("Reading mods from mod directory")
        configP = _config.ConfigParser()


        mods_list = []
        for dirname in installed_mods:
            moddir = mods_dir / dirname

            # since this is the creation of the mods list, we just
            # derive the ordinal from order in which the mod-folders
            # are encountered (likely alphabetical)
            order = len(mods_list)+1

            # support loading information
            # read from meta.ini (ModOrganizer) file, if present
            inipath = moddir / "meta.ini"
            if inipath.exists():
                configP.read(str(inipath))
                try:
                    mods_list.append(
                        self.make_mod_entry(
                            ordinal = order,
                            directory=dirname,
                            modid=configP['General']['modid'],
                            version=configP['General']['version']
                        ))
                except KeyError:
                    # if the meta.ini file was malformed or something,
                    # ignore it
                    mods_list.append(
                        self.make_mod_entry(ordinal=order,
                                            directory=dirname))
            else:
                mods_list.append(
                    self.make_mod_entry(ordinal = order,
                                        directory=dirname))

        # so long as the mod directory wasn't empty, populate the table
        if mods_list:
            self.fill_mods_table(mods_list)
        else:
            self.LOGGER << "Mods directory empty"

        del _config

    def load_all_mod_files(self, mods_dir=None):
        """
        Here's an experiment to load ALL files from disk when the
        program starts up...let's see how long it takes

        Update: about 12 seconds to load info for 223 mods from an
        ntfs-3g partition on a 7200rpm WD-Black...
        not the horriblest, but still likely needs to be shunted to
        another thread.  Especially since that was pretty much just
        reading file names; no operations such as checking for conflicts
        was done Also, dumping the db to disk (in txt form) made a
        2.7 MB file.

        Update to update: 2nd time around, didn't even take 2 seconds. I
        did make some tweaks to the code, but still...I'm guessing the
        files were still in the system RAM?

        """

        if mods_dir:
            if isinstance(mods_dir, str):
                mods_dir = Path(mods_dir)
        else:
            # mods_dir = self.mainmanager.get_directory(keystrings.Dirs.MODS, aspath=True)
            mods_dir = self.mainmanager.Folders[keystrings.Dirs.MODS].path
            # verify that mods dir is set
            # if not mods_dir:
            #     raise exceptions.InvalidAppDirectoryError(keystrings.Dirs.MODS, mods_dir)



        installed_mods = self.mainmanager.installed_mods

        # go through each folder indivually
        with self.conn:
            for mdir in installed_mods:
                self.add_files_from_dir(mdir, str(mods_dir / mdir))

        self._empty['modfiles'] = self.count("modfiles") < 1



                # self.LOGGER << "dumping db contents to disk"
        # with open('res/test2.dump.sql', 'w') as f:
        #     for l in self._con.iterdump():
        #         f.write(l+'\n')

    def load_skyfiles(self, skyrim_dir):
        """
        Like 'load_all_mod_files', this examines the disk for
        individual files and adds them to the modfiles table. However,
        this only examines the "Data" directory within the given
        Skyrim installation folder and addsd the files under the mod
        name "Skyrim"

        :param skyrim_dir:
        """

        # check if we have any "Skyrim"-rows already

        # c=self.count("modfiles", directory='Skyrim')
        # self.LOGGER << "Skyfile count: {}".format(c)

        # if self.count("modfiles", directory='Skyrim')

        self.LOGGER << "adding files from Skyrim Data directory"
        if self.count("modfiles", directory='Skyrim'):
            # if so, clear them out
            self.remove_files('Skyrim')

        # with self.conn:
        for f in skyrim_dir.iterdir():
            if f.is_dir() and f.name.lower() == "data":
                # add files to db under mod-name "Skyrim"
                # TODO: make sure all parts of the application treat these items as a special case (since the files listed here obviously won't be under the 'normal' mods directory)
                # self.add_files_from_dir('Skyrim', str(f))
                self._add_files_from_skyrim_data(f)
                break

        self._empty['modfiles'] = self.count("modfiles") < 1

    def _add_files_from_skyrim_data(self, path, *,
                           relpath = os.path.relpath,
                           join = os.path.join):
        """Special case: adding vanilla/manually-installed mods from Skyrim/Data

        :param Path path:
        """
        mfiles = []


        files_by_ext = defaultdict(list)

        for f in path.iterdir():
            if f.is_file():
                # get extension (without leading period, in lowercase)
                ext = f.suffix.lstrip('.').lower()
                if ext:
                    # create mapping of file names by extension; this
                    # will let us easily determine if, e.g., we have
                    # matching esm's/esp's and bsa's
                    files_by_ext[ext].append(f.stem.lower())


        s_mods = []
        for ext, flist in files_by_ext.items():
            # add faux-mods for found es[mp]'s and corresponding bsa's
            if ext in ['esm', 'esp']:
                for file in flist:
                    # the 'mod' name will be the stem of the file
                    m_name=file
                    # first item of file list is the es[mp]
                    to_add=[file+'.'+ext]

                    # go through all OTHER extensions for matching files
                    for e2, fl2 in files_by_ext.items():
                        if e2!=ext and m_name in fl2:
                            to_add.append(m_name+'.'+e2)

                    # TODO: store enabled status, custom-name for these; also see if version info can be pulled from files
                    # create the fake mod; set up in format that can be
                    # passed to to_row_tuple()
                    m_info = self.make_mod_entry(ordinal=next(_mcount),
                                                 name=m_name,
                                                 directory=m_name,
                                                 managed=0
                                                 )
                    # m_info=[("name", m_name),
                    #         ("directory", m_name),
                    #         ("modid", 0),
                    #         ("version", ""),
                    #         ("enabled", 1)]

                    # s_mods.append(self.to_row_tuple(m_info))

                    with self.conn:
                        # add the "mod"
                        self.conn.execute(
                            "INSERT INTO mods({}) VALUES ({})".format(
                                ", ".join(db_fields_noerror),
                                ", ".join("?" * len(db_fields_noerror))
                            ),
                            m_info
                            # self.to_row_tuple(m_info)
                        )
                        # and now the mod files
                        self.conn.executemany(
                            "INSERT INTO modfiles VALUES (?, ?)",
                            zip(repeat(m_name), to_add))




        # for root, dirs, files in os.walk(path):
        #     mfiles.extend(
        #         relpath(join(root, f), path).lower() for f in files)


    # noinspection PyIncorrectDocstring
    def add_files_from_dir(self, mod_name, mod_root, *,
                           relpath = os.path.relpath,
                           join = os.path.join):
        """
        Given a directory `mod_root` containing files for a mod named `mod_name`, add those files to the modfiles table.
        :param mod_name:
        :param str mod_root:
        :return:
        """

        mfiles = []
        for root, dirs, files in os.walk(mod_root):
            # this gets the lowercase path to each file, starting at the
            # root of this mod folder. So:
            #   '/path/to/modstorage/CoolMod42/Meshes/WhatEver.NIF'
            # becomes:
            #   'meshes/whatever.nif'
            mfiles.extend(
                relpath(join(root, f), mod_root).lower() for f in files)

        # put the mod's files in the db, with the mod name as the first
        # field (e.g. 'CoolMod42'), and the filepath as the second (e.g.
        # 'meshes/whatever.nif')
        if mfiles:
            self._con.executemany(
                "INSERT INTO modfiles VALUES (?, ?)",
                zip(repeat(mod_name), mfiles))

            # mark modfiles table non-empty
            # self._empty['modfiles'] = False


        # try: mfiles.remove('meta.ini') #don't care about these
        # except ValueError: pass

    def remove_files(self, for_mod):
        """
        Remove all data rows from the modfiles table that belong to the
        specified mod

        :param for_mod: Name of mod's directory on disk (i.e. the ID
            under which they are keyed in the db)
        """
        if not self._empty['modfiles']:
            self.LOGGER << "Removing files for mod '{}' from database".format(for_mod)

            with self.conn:
                self.conn.execute("DELETE FROM modfiles WHERE directory = ?", (for_mod, ))

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
        file=''
        conflicts = defaultdict(list)
        mods_with_conflicts = defaultdict(list)

        # only run if there are actually any files to check
        if not self._empty['modfiles']:
            self.LOGGER.info("Detecting file conflicts")

            # if we're reloading the status of conflicted mods,
            # delete the view if it exists

            # create the view
            with self.conn:
                self.conn.execute("DROP VIEW IF EXISTS filesbymodorder")

                # self._con.execute(q)
                self.conn.execute("""
                    CREATE VIEW filesbymodorder AS
                        SELECT ordinal, f.directory, filepath
                        FROM modfiles f, mods m
                        WHERE f.directory=m.directory
                        ORDER BY ordinal
                    """)

            # [print(*r) for r in self._con.execute(detect_dupes_query)]
            # for r in self._con.execute(detect_dupes_query):

            # query view to detect duplicates
            for r in self.conn.execute("""
                SELECT f.filepath, f.ordinal, f.directory
                    FROM filesbymodorder f
                    INNER JOIN (
                        SELECT filepath, COUNT(*) AS C
                        FROM filesbymodorder
                        GROUP BY filepath
                        HAVING C > 1
                    ) dups ON f.filepath=dups.filepath
                    ORDER BY f.filepath, f.ordinal
                    """):
                if r['filepath'] != file:
                    file=r['filepath']
                mod=r['directory']

                # a dictionary of file conflicts to an ordered
                #  list of mods which contain them
                conflicts[file].append(mod)
                # also, a dictionary of mods to a list of conflicting files
                mods_with_conflicts[mod].append(file)
        else:
            self.LOGGER << "No files present in modfiles table"

        # convert to normal dicts when adding to conflict map
        self._conflict_map = File_Conflict_Map(by_file=dict(conflicts),
                                               by_mod=dict(mods_with_conflicts))

        # self._file_conflicts = conflicts
        # self.mods_with_conflicting_files = mods_with_conflicts

        # for c in mods_with_conflicts['Bethesda Hi-Res DLC Optimized']:
        #     print("other mods containing file '%s'" % c)
        #     for m in conflicts[c]:
        #         if m!='Bethesda Hi-Res DLC Optimized':
        #             print('\t', m)

    def make_mod_entry(self, **kwargs):
        """
        generates a tuple representing a mod-entry by supplementing a
        possibly-incomplete mapping of keywords (`kwargs`) with default
        values for any missing fields
        """
        row = []

        for field in db_fields_noerror:
            row.append(kwargs.get(field,
                                  self.__defaults.get(
                                      field, lambda v: "")(kwargs)))
        return tuple(row)

    def validate_mods_list(self, installed_mods):
        """
        Compare the database's list of mods against a list of the
        folders in the installed-mods directory. Handle discrepancies by
        raising an Exception object containing two separate lists:

            * Mods Not Listed: for mod directories found on disk but not
              previously listed in the user's list of installed mods
            * Mods Not Found: for mods listed in the list of installed
              mods whose installation folders were not found on disk.

        :param list[str] installed_mods: list of all installed mods
        :return: True if no errors and table unchanged. False if errors
            encountered and/or removed from table
        """
        # I wish there were a...lighter way to do this, but I
        # believe only directly comparing dirnames will allow
        # us to provide useful feedback to the user about
        # problems with the mod installation

        # reset the errors collection (set 'error' field to 0 for
        # every row where it is currently non-zero)
        num_removed = self.reset_errors()

        self.logger.debug("Resetting mod errors: {} entries affected"
                          .format(num_removed))

        dblist = [r["directory"] for r in
                  self.conn.execute("SELECT directory FROM mods")]

        # make a copy of the mods list since we may be
        # modifying its contents
        im_list = installed_mods[:]

        not_found = []
        not_listed = []

        if len(dblist) > len(im_list):
            for modname in im_list:
                try:
                    dblist.remove(modname)
                except ValueError:
                    # if it's not listed in the db, note that
                    not_listed.append(modname)
            # anything left over is missing from the disk
            not_found = dblist

        else: # len(dblist) <= len(installed_mods):
            for modname in dblist:
                try:
                    im_list.remove(modname)
                except ValueError:
                    not_found.append(modname)
            # if everything matched, this should be empty
            not_listed = im_list


        # i think inserting into the database is faster when done in
        # large chunks, so we accumulated the errors above and will
        # insert them all at once
        if not_listed:
            self._update_errors(ModError.MOD_NOT_LISTED, not_listed)

        if not_found:
            self._update_errors(ModError.DIR_NOT_FOUND, not_found)

        # return true only if all 3 are empty/0;
        # we return false on num_removed so that the GUI will
        # still update its contents
        return not (not_listed or not_found or num_removed)

    def _update_errors(self, error_type, dir_list):
        """helper method for validate_mods_list"""

        with self.conn:
            ## for each mod-directory name in `dir_list`, update the
            ## 'error' field for that mod's db-entry to be `error_type`
            query = "UPDATE mods SET error = {} " \
                    "WHERE directory IN (".format(
                    # use int() for a bit of added security
                    int(error_type))

            # get the appropriate number of '?'.
            # i don't think we need to worry about this going over
            # 999...do we?
            query += ", ".join("?" * len(dir_list)) + ")"

            # make it so.
            self.conn.execute(query, dir_list)

    @staticmethod
    def json_write(json_target, pyobject):
        """Dump the given object to a json file specified by the given Path object.

        :param Path json_target:
        :param pyobject:
        """
        with json_target.open('w') as f:
            json.dump(pyobject, f, indent=1)


    @staticmethod
    def to_row_tuple(pairs):
        """
        Used as object_pair_hook for json.load(). Takes the mod
        information loaded from the json file and converts it
        to a tuple of just the field values in the
        correct order for feeding to the sqlite database.

        :param typing.Sequence[tuple[str, Any]] pairs:
        :return: Tuple containing just the values of the fields
        """

        # value for ordinal is taken from global incrementer as it is not
        # stored in the modinfo file and is instead dependent on the
        # order in which items are read from said file
        return (next(_mcount),) + tuple(
            s[1] for s in sorted(pairs,
                                 key=lambda p: db_field_order[p[0]]))

