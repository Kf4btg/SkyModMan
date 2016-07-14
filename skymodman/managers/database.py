import json
import json.decoder
import os
import sqlite3
from pathlib import Path, PurePath
from itertools import count, repeat
from collections import defaultdict

from skymodman.constants import db_fields, ModError
from skymodman.utils import withlogger, tree
# from skymodman.managers import modmanager as Manager

_mcount = count()

# from skymodman.utils import humanizer
# @humanizer.humanize
@withlogger
class DBManager:

    _SCHEMA = """
        CREATE TABLE mods (
            ordinal   INTEGER unique, --mod's rank in the install order
            directory TEXT    unique, --folder on disk holding mod's files
            name      TEXT,           --user-editable label for mod
            modid     INTEGER,        --nexus id, or 0 if none
            version   TEXT,           --arbitrary, set by mod author
            enabled   INTEGER default 1,  --effectively a boolean value (0,1)
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

    # having the foreign key deferrable should prevent the db freaking out when we temporarily delete entries in 'mods' to modify the install order.

    _tablenames = ("modfiles", "hiddenfiles", "mods")
    _profile_reset_tables = ("hiddenfiles", "mods") # which tables need to be reset when profile changes

    __defaults = {
        "name": lambda v: v["directory"],
        "modid": lambda v: 0,
        "version": lambda v: "",
        "enabled": lambda v: 1,
    }
        # "error": lambda v: ModError.NONE

    def __init__(self):
        """

        """
        super().__init__()

        # create db in memory
        self._con = sqlite3.connect(":memory:")

        # create the mods table
        # NOTE: `ordinal` (i.e. the mod's place in the "install-order") is not stored on disk with the rest of the mod info; it is instead inferred from the order in which the mods are listed in the config file
        # NOTE2: `directory` is the name of the folder in the
        # mods-directory where the files for this mod are saved.
        # `name` is initially equivalent, but can be changed as
        # desired by the user.
        self._con.executescript(self._SCHEMA)
        self._con.row_factory = sqlite3.Row

        # These are created from the database, so it seems like it may
        # be best just to store them in this class:
        # actuall no that was confusing. there;d store on the manager now
        # nope not anymore. i don't know what's happening

        ## {filepath:[list of mods containing that file]}
        # self.conflicts = defaultdict(list)

        ## {mod:[contained files that are in conflict with other mods]}
        # self.mods_with_conflicts = defaultdict(list)

        self.file_conflicts = None
        self.mods_with_conflicting_files = None


    ################
    ## Properties ##
    ################

    @property
    def conn(self) -> sqlite3.Connection:
        """
        Directly access the database connection of this manager
        in order to perform custom queries.
        """
        return self._con

    @property
    def mods(self):
        """
        :return: list of all mods from the mod db
        :rtype: list[sqlite3.Row]
        """
        return self.get_mod_info(True).fetchall()

    ######################
    ## Table management ##
    ######################

    def reinit(self):
        """Drop the current mods table and reinitialize as empty"""

        # self.LOGGER.debug("dropping mods table")

        with self._con:
            # take advantage of the "truncate optimization" feature in sqlite
            # to remove all rows quicker and easier than dropping and recreating.

            # self._con.execute("DELETE FROM ?", self._tablenames)
            # Apparently you can't use ? parameters for table names??!?!?
            for n in self._tablenames:
                self._con.execute("DELETE FROM {table}".format(table=n))


            # self._con.execute("DROP TABLE hiddenfiles, mods")

            # self._con.executescript(self._SCHEMA)

    def reset_table(self, table_name):
        """
        Remove all rows from specified table

        :param table_name: Jim.
        :return: Number of rows removed
        """

        # not that I'm worried too much about security with this
        # program... but let's see if we can't avoid some SQL-injection
        # attacks, just out of principle

        if table_name not in self._tablenames:
            # should probably raise an error
            return 0

        q="DELETE FROM {table}".format(table=table_name)
        with self._con:
            return self._con.execute(q).rowcount


    def reset_errors(self):
        """
        Reset the "error" column for each mod to ModError.None

        :return: the number of rows affected
        """

        with self._con:
            return self._con.execute(
                "UPDATE mods SET error = 0 WHERE error != 0").rowcount

    def commit(self):
        """
        Commit the current transaction. Logs a warning if there is no
        active transaction to commit
        """
        if not self._con.in_transaction:
            self.LOGGER.warning("Database not currently in transaction."
                                " Committing anyway.")

        self._con.commit()

    def rollback(self):
        if self._con.in_transaction:
            self._con.rollback()
        else:
            # i'm aware that a rollback without transaction isn't
            # an error or anything; but if there's nothing to rollback
            # and rollback() is called, then I likely did something
            # wrong and I want to know that
            self.LOGGER.warning("nothing to rollback")


    ##################
    ## DATA LOADING ##
    ##################

    def load_mod_info(self, json_source) -> bool:
        """
        read the saved mod information from a json file and
        populate the in-memory database

        :param str|Path json_source: path to modinfo.json file
        """
        global _mcount
        # reset counter so that mod-ordinal is determined by the order
        # in which the entries are read from the file
        _mcount = count()

        # self.LOGGER.debug("loading mod db from file")

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

    def load_hidden_files(self, json_source) -> bool:
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
                for mod, files in hiddenfiles.items():
                    # gethiddenfiles returns a list of 1-tuples,
                    # each one with a filepath
                    hfiles = self._get_hidden_files(files, "", [])

                    with self._con:
                        self._con.executemany(
                            'INSERT INTO hiddenfiles VALUES ("'
                            + mod + '", ?)', hfiles)

                # [print(*r, sep="\t|\t") for r in
                #  self._con.execute("select * from hiddenfiles")]
                success=True

            except json.decoder.JSONDecodeError:
                self.LOGGER.warning("No hidden files listed in {}, "
                                    "or file is malformed."
                                    .format(json_source))
        return success

    def _get_hidden_files(self, basedict, currpath, flist, join=os.path.join):
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
                # have to add each filepath as 1-tuple to keep sqlite happy
                flist.extend((join(currpath, fname), ) for fname in value)
            else:
                flist = self._get_hidden_files(value, join(currpath, key), flist)

        return flist
    ###################################

    def populate_hidden_files_table(self, filelist):
        """
        :param Iterable[(str, str)] filelist: List of 2-tuples; each
            tuple is of form (directory:str, filepath:str)

            Here, `directory` is the name of the folder in the
            configured mods directory that contains the files for the
            mod in question.  This would be something like
            'Big Trees HD_v2', or whatever arbitrary name the mod
            author gave the folder.

            `filepath` is the relative path from the containing mod
            directory to the hidden file (something along the lines of
            "meshes/trees/bigtree.nif").
        """
        with self._con:
            self._con.executemany("INSERT INTO hiddenfiles VALUES (?, ?)", filelist)

    def save_hidden_files(self, json_target):
        """

        Note: I notice ModOrganizer adds a '.mohidden' extension to every file it hides (or to the parent directory);
        hmm...I'd like to avoid changing the files on disk if possible

        :param str|Path json_target: path to hiddenfiles.json file for current profile
        """

        if not isinstance(json_target, Path):
            json_target = Path(json_target)

        # build a tree from the database and jsonify it to disk
        htree = tree.Tree()

        for row in self._con.execute(
            "SELECT * FROM hiddenfiles ORDER BY directory, filepath"):
            # print(*row)
            p = PurePath(row['directory'], row['filepath'])
            pathparts = p.parts[:-1]

            htree.insert(pathparts, p.name)

        with json_target.open('w') as f:
            f.write(str(htree))


        # print(tree.to_string(2))


    # def fill_mods_table(self, mod_list, doprint=False):
    def fill_mods_table(self, mod_list):
        """
        Dynamically build the INSERT statement from the list of fields, then insert
        the values from mod_list (a list of tuples) into the database

        :param Iterable[tuple] mod_list:
        """

        # db_fields[:-1] to ignore the error field for now (leave it at
        # its default of 0)
        query = "INSERT INTO mods(" + \
                ", ".join(db_fields[:-1]) + \
                ") VALUES ("
        query += ", ".join("?" * len(db_fields[:-1])) + ")"
        #
        # if doprint:
        #     print(query)
        #     # print(list(mod_list))
        #     for m in mod_list:
        #         print(m)

        # self.LOGGER.debug(query)
        with self._con:
            # insert the list of row-tuples into the in-memory db
            self._con.executemany(query, mod_list)


    ##############
    ## wrappers ##
    ##############

    def execute_(self, query, params=None):
        """
        Execute an arbitrary SQL-query using this object's
        database connection as a context manager

        :param str query: a valid SQL query
        :param typing.Iterable params: If the `params` keyword is
            provided with an Iterable object, it will be used as the
            parameters for a parameterized query.
        :rtype: typing.Generator[sqlite3.Row, Any, None]
        """
        with self._con:
            if params:
                yield from self._con.execute(query, params)
            else:
                yield from self._con.execute(query)

    def getone(self, query, params=None):
        """
        Like execute_, but just returns the first result

        :param str query:
        :param typing.Iterable params:
        :return: The first row obtained
        :rtype: sqlite3.Row
        """
        with self._con:
            if params:
                cur=self._con.execute(query, params)
            else:
                cur=self._con.execute(query)

            return cur.fetchone()

    def update_(self, sql, params=None):
        """
        As execute_, but for UPDATE, INSERT, DELETE, etc. commands.
        Returns the cursor object that was created to execute the
        statement.

        :param str sql:
        :param typing.Iterable params:
        """
        with self._con:
            if params:
                return self._con.execute(sql, params)
            else:
                return self._con.execute(sql)

    def updatemany_(self, sql, params=None):
        """
        As update_, but for multiple transactions. Returns the cursor
        object that was created to execute the statement.

        :param str sql:
        :param typing.Iterable params:
        :return: the cursor object that executed the query
        """
        with self._con:
            if params:
                return self._con.executemany(sql, params)
            else:
                return self._con.executemany(sql)

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
        noord_fields = set(db_fields) ^ {"ordinal", "error"}

        # select (all fields other than ordinal)...
        query="SELECT " + ", ".join(noord_fields)
        # from a subquery of (all fields ordered by ordinal)
        query+=" FROM (SELECT * FROM mods ORDER BY ordinal)"
        modinfo = []

        # for each row (mod-entry)
        for row in self._con.execute(query):
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
                        self._con.execute(
                            "SELECT name FROM mods WHERE enabled = 1"))
        else:
            yield from self._con.execute(
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
                        self._con.execute(
                            "SELECT name FROM mods WHERE enabled = 0"))
        else:
            yield from self._con.execute(
                                "SELECT * FROM mods WHERE enabled = 0")

    def mods_with_error(self, error_type):
        """
        Fetches all mods from the db with the given ModError type

        :param error_type:
        :return:
        """

        yield from self._con.execute(
            "SELECT * FROM mods WHERE error = ?", (error_type, ))


    def get_mod_info(self, raw_cursor = False) :
        """
        Yields Row objects containing all information about installed mods

        :param raw_cursor: If true, return the db cursor object instead of yielding Rows
        :return:   Tuple of mod info or sqlite3.cursor
        :rtype: __generator[sqlite3.Row, Any, None]|sqlite3.Cursor
        """
        cur = self._con.execute("SELECT * FROM mods")
        if raw_cursor:
            return cur
        yield from cur

    def shutdown(self):
        """
        Close the db connection
        """
        self._con.close()

    def get_mod_data_from_directory(self, mods_dir):
        """
        scan the actual mods-directory and populate the database from
        there instead of a cached json file.

        Will need to do this on first run and periodically to make sure
        cache is in sync.

        :param str mods_dir:
        """
        # TODO: Perhaps this should be run on every startup? At least to make sure it matches the stored data.
        import configparser as _config

        self.logger.info("Reading mods from mod directory")
        configP = _config.ConfigParser()


        mods_list = []
        for moddir in Path(mods_dir).iterdir():
            # skip any non-directories
            if not moddir.is_dir(): continue

            # since this is the creation of the mods list, we just
            # derive the ordinal from order in which the mod-folders
            # are encountered (likely alphabetical)
            order = len(mods_list)+1
            dirname = moddir.name

            # self.load_all_mod_files(moddir, order)

            inipath = moddir / "meta.ini"
            if inipath.exists():
                # read info from meta.ini (ModOrganizer) file
                configP.read(str(inipath))
                mods_list.append(
                    self.make_mod_entry(ordinal = order,
                                        directory = dirname,
                                        modid = configP['General']['modid'],
                                        version = configP['General']['version']
                                        )
                                )
            else:
                mods_list.append(
                    self.make_mod_entry(ordinal = order, directory=dirname))

        self.fill_mods_table(mods_list)

        del _config

    def load_all_mod_files(self, directory):
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

        :param str directory: path to the configured mod-storage dir
        :return:
        """

        # go through each folder indivually
        for modfolder in Path(directory).iterdir():
            if not modfolder.is_dir(): continue
            self.add_files_from_dir(modfolder.name, str(modfolder))

        # self.LOGGER << "dumping db contents to disk"
        # with open('res/test2.dump.sql', 'w') as f:
        #     for l in self._con.iterdump():
        #         f.write(l+'\n')

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
        # modroot = str(directory)  # the abs path for this mod's folder

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
                "INSERT INTO modfiles VALUES (?, ?)", zip(repeat(mod_name), mfiles))

        # try: mfiles.remove('meta.ini') #don't care about these
        # except ValueError: pass

    def detect_file_conflicts(self):
        """
        Using the data in the 'modfiles' table, detect any file
        conflicts among the installed mods
        """

        self.LOGGER.info("Detecting file conflicts")


        # if we're reloading the status of conflicted mods,
        # delete the view if it exists
        self._con.execute("DROP VIEW IF EXISTS filesbymodorder")

        q="""
        CREATE VIEW filesbymodorder AS
            SELECT ordinal, f.directory, filepath
            FROM modfiles f, mods m
            WHERE f.directory=m.directory
            ORDER BY ordinal
        """

        with self._con:
            self._con.execute(q)

        detect_dupes_query = """
            SELECT f.filepath, f.ordinal, f.directory
                FROM filesbymodorder f
                INNER JOIN (
                    SELECT filepath, COUNT(*) AS C
                    FROM filesbymodorder
                    GROUP BY filepath
                    HAVING C > 1
                ) dups ON f.filepath=dups.filepath
                ORDER BY f.filepath, f.ordinal
                """

        file=''
        conflicts = defaultdict(list)
        mods_with_conflicts = defaultdict(list)

        # [print(*r) for r in self._con.execute(detect_dupes_query)]
        for r in self._con.execute(detect_dupes_query):
            if r['filepath'] != file:
                file=r['filepath']
            mod=r['directory']
            # a dictionary of file conflicts to an ordered list of mods which contain them
            conflicts[file].append(mod)
            # also, a dictionary of mods to a list of conflicting files
            mods_with_conflicts[mod].append(file)

        self.file_conflicts = conflicts
        self.mods_with_conflicting_files = mods_with_conflicts

        # for c in mods_with_conflicts['Bethesda Hi-Res DLC Optimized']:
        #     print("other mods containing file '%s'" % c)
        #     for m in conflicts[c]:
        #         if m!='Bethesda Hi-Res DLC Optimized':
        #             print('\t', m)

    def make_mod_entry(self, **kwargs):
        """generates a tuple representing a mod-entry by supplementing a possibly-incomplete mapping of keywords (`kwargs`) with default values for any missing fields"""
        row = []

        for field in db_fields[:-1]:
            row.append(kwargs.get(field, self.__defaults
                                  .get(field, lambda v: "")(kwargs)
                                )
                     )
        return tuple(row)

    def validate_mods_list(self, moddir):
        """
        Compare the database's list of mods against a list of the
        folders in the installed-mods directory. Handle discrepancies by
        raising an Exception object containing two separate lists:

            * Mods Not Listed: for mod directories found on disk but not
              previously listed in the user's list of installed mods
            * Mods Not Found: for mods listed in the list of installed
              mods whose installation folders were not found on disk.

        :param str moddir: the path to the mod storage directory

        :return: True if no errors and table unchanged. False if errors
            encountered and/or removed from table
        """
        # I wish there were a...lighter way to do this, but I
        # believe only directly comparing dirnames will allow
        # us to provide useful feedback to the user about
        # problems with the mod installation

        # list of all the installed mods
        installed_mods = os.listdir(moddir)

        # first, reset the errors column

        num_removed = self.reset_errors()

        self.logger.debug("Resetting mod errors: {} entries affected".format(num_removed))

        dblist = [t["directory"] for t in self._con.execute("SELECT directory FROM mods")]
        not_found = []
        not_listed = []

        if len(dblist) > len(installed_mods):
            for modname in installed_mods:
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
                    installed_mods.remove(modname)
                except ValueError:
                    not_found.append(modname)
            # if everything matched, this should be empty
            not_listed = installed_mods


        # i think inserting into the database is faster when done in
        # large chunks, so we accumulated the errors above and will
        # insert them all at once
        if not_listed:
            with self._con:
                ## for each mod-directory name in not_listed, update
                ## the 'error' field for that mod's db-entry to be
                ## ModError.MOD_NOT_LISTED
                query = "UPDATE mods SET error = {} " \
                        "WHERE directory IN (".format(
                    # use int() for a bit of added security
                    int(ModError.MOD_NOT_LISTED))

                # get the appropriate number of ?
                query += ", ".join("?" * len(not_listed)) + ")"

                # make it so.
                self._con.execute(query, not_listed)

        if not_found:
            ## same as above, but for DIR_NOT_FOUND

            with self._con:
                query = "UPDATE mods SET error = {} " \
                        "WHERE directory IN (".format(
                    int(ModError.DIR_NOT_FOUND))

                query += ", ".join("?" * len(not_found)) + ")"

                self._con.execute(query, not_found)

        # return true only if all 3 are empty/0;
        # we return false on num_removed so that the GUI will
        # still update its contents
        return not (not_listed or not_found or num_removed)

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

        return (next(_mcount),) + tuple(s[1] for s in sorted(pairs, key=lambda p: db_fields.index(p[0])))


# if __name__ == '__main__':
#     # from skymodman.managers import ModManager
#
#     DB = DBManager()
#     DB._con.row_factory = sqlite3.Row
#
#     DB.load_mod_info(Path(os.path.expanduser("~/.config/skymodman/profiles/default/modinfo.json")))
#
#     c= DB.conn.execute("select * from mods")
#
#     print (c.description)
#
#     r=c.fetchone() #type: sqlite3.Row
#
#     print(type(r))
#
#     print(r.keys())
#     print(r['directory'])
#
#     print(dict(zip(r.keys(), r)))
#
#
#
#
#
#     # print(DB.getone("Select * from mods where ordinal = 22"))
#     # [ print(r) for r in DB.execute_("Select * from mods where ordinal BETWEEN 20 AND 24")]
#     #
#     # DB.conn.execute("DELETE FROM mods WHERE ordinal = 22")
#     # [ print(r) for r in DB.execute_("Select * from mods where ordinal BETWEEN 20 AND 24")]
#     #
#     # DB.conn.execute("INSERT into mods (name, directory, ordinal) VALUES ('boogawooga', 'boogawoogadir', 22)")
#     #
#     # [ print(r) for r in DB.execute_("Select * from mods where ordinal BETWEEN 20 AND 24")]
#
#     DB.shutdown()

