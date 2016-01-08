import json
import json.decoder
import os
import sqlite3
from pathlib import Path
from typing import List, Tuple, Iterable

from skymodman import constants
from skymodman.utils import withlogger, counter

mcount = counter()

@withlogger
class DBManager:

    _SCHEMA = """CREATE TABLE mods (

            ordinal   INTEGER unique, --mod's rank in the install order
            directory TEXT    unique, --folder on disk holding mod's files
            name      TEXT,           --user-editable label for mod
            modid     INTEGER,        --nexus id, or 0 if none
            version   TEXT,           --arbitrary, set by mod author
            enabled   INTEGER default 1  --effectively a boolean value (0,1)
        );
        CREATE TABLE hiddenfiles (
            file      TEXT      -- path to the file that has been hidden
            isdir     INTEGER   -- 0 or 1 bool, all files under hidden dir are hidden
            directory TEXT REFERENCES mods(directory) DEFERRABLE INITIALLY DEFERRED
              -- the mod directory under which this file resides
        );"""

    # __fields = ["ordinal", "directory", "name", "modid", "version", "enabled"]
    __defaults = {
        "name": lambda v: v["directory"],
        "modid": lambda v: 0,
        "version": lambda v: "",
        "enabled": lambda v: 1,
    }

    def __init__(self, manager: 'ModManager'):
        super(DBManager, self).__init__()

        self.manager = manager

        # create db in memory
        self._con = sqlite3.connect(":memory:")

        # create the mods table
        # NOTE: `ordinal` (i.e. the mod's place in the "install-order") is not
        # stored on disk with the rest of the mod info; it is
        # instead inferred from the order in which the mods
        # are listed in the config file 
        # NOTE2: `directory` is the name of the folder in the
        # mods-directory where the files for this mod are saved.
        # `name` is initially equivalent, but can be changed as
        # desired by the user.
        self._con.execute(self._SCHEMA)
        self._con.row_factory = sqlite3.Row


    ################
    ## Properties ##
    ################

    @property
    def conn(self) -> sqlite3.Connection:
        """
        Directly access the database connection of this manager
        in order to perform custom queries.
        :return:
        """
        return self._con

    @property
    def mods(self) -> List[Tuple]:
        """
        Return list of all mods from the mod db
        :return:
        """
        return self.getModInfo(True).fetchall()

    ######################
    ## Table management ##
    ######################

    def reinit(self):
        """Drop the current mods table and reinitialize as empty"""

        # self.LOGGER.debug("dropping mods table")

        with self._con:
            self._con.execute("DROP TABLE hiddenfiles, mods")

            self._con.execute(self._SCHEMA)

    def loadModDB(self, json_source):
        """
        read the saved mod information from a json file and
        populate the in-memory database
        :param json_source: path to modinfo.json file (either pathlib.Path or string)
        """
        global mcount
        # reset counter so that mod-ordinal is determined by the order
        # in which the entries are read from the file
        mcount = counter()

        # self.LOGGER.debug("loading mod db from file")

        if not isinstance(json_source, Path):
            json_source = Path(json_source)

        success = True
        with json_source.open('r') as f:
            # read from json file and convert mappings
            # to ordered tuples for sending to sqlite
            try:
                mods = json.load(f, object_pairs_hook=DBManager.toRowTuple)
                self.fillTable(mods)

            except json.decoder.JSONDecodeError:
                self.logger.error("No mod information present in {}, or file is malformed.".format(json_source))
                success = False
        return success

    def loadHiddenFiles(self, json_source):
        if not isinstance(json_source, Path):
            json_source = Path(json_source)
        success = True
        with json_source.open('r') as f:
            try:
                hiddenfiles = json.load(f)
                self.populateHiddenFilesTable(hiddenfiles)
            except json.decoder.JSONDecodeError:
                self.logger.warning("No hidden files listed in {}, or file is malformed.".format(json_source))
                success = False
        return success


    def populateHiddenFilesTable(self, filelist):

        q = "insert into hiddenfiles values (?, ?, ?)"

        with self._con:
            self._con.executemany(q, filelist)

    def saveHiddenFiles(self, json_target):
        if not isinstance(json_target, Path):
            json_target = Path(json_target)

        cur = self._con.execute("Select * from hiddenfiles group by directory")

        # todo: use defaultdict for this
        filelist = {}
        for row in cur:
            mdir = row['directory']
            if not mdir in filelist:
                filelist[mdir] = []
            # each file has a path and an indicator whether it is a directory
            filelist[mdir].append({"file": row['file'], "isdir": row['isdir']})

        self.jsonWrite(json_target, filelist)

    # def fillTable(self, mod_list, doprint=False):
    def fillTable(self, mod_list):
        """
        Dynamically build the INSERT statement from the list of fields, then insert
        the values from mod_list (a list of tuples) into the database
        :param mod_list:
        :return:
        """
        query = "INSERT INTO mods(" + ", ".join(constants.db_fields) + ") VALUES ("
        query += ", ".join("?" * len(constants.db_fields)) + ")"
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

    def execute_(self, query:str, params: Iterable=None):
        """
        Execute an arbitrary SQL-query using this object's
        database connection as a context manager
        :param query: a valid SQL string
        :param params: If the `params` keyword is provided with an Iterable object, it will be used as the parameters for a parameterized query.
        :return:
        """
        with self._con:
            if params:
                yield from self._con.execute(query, params)
            else:
                yield from self._con.execute(query)

    def getOne(self, query, params: Iterable=None):
        """
        Like execute_, but just returns the first result
        :param query:
        :param params:
        :return:
        """
        with self._con:
            if params:
                cur=self._con.execute(query, params)
            else:
                cur=self._con.execute(query)

            return cur.fetchone()

    def update_(self, sql, params: Iterable=None):
        """
        As execute_, but for UPDATE, INSERT, DELETE, etc. commands. Returns the cursor object that was created to execute the statement.
        :param sql:
        :param params:
        """
        with self._con:
            if params:
                return self._con.execute(sql, params)
            else:
                return self._con.execute(sql)

    def updatemany_(self, sql, params: Iterable=None):
        """
        As update_, but for multiple transactions. Returns the cursor object that was created to execute the statement.
        :param sql:
        :param params:
        """
        with self._con:
            if params:
                return self._con.executemany(sql, params)
            else:
                return self._con.executemany(sql)

    ############
    ## Saving ##
    ############

    def saveModDB(self, json_target):
        """
        Write the data from the in-memory database to a
        json file on disk. The file will be overwritten, or
        created if it does not exist
        :param json_target: path to modinfo.json file
        :return:
        """

        if not isinstance(json_target, Path):
            json_target = Path(json_target)

        # we don't save the ordinal rank, so we need to get a list (set) of the
        # fields without "ordinal"
        # Using sets here is OK because field order doesn't matter when saving
        noord_fields = set(constants.db_fields) ^ {"ordinal"}

        # select (all fields other than ordinal)...
        query="Select " + ", ".join(noord_fields)
        # from a subquery of (all fields ordered by ordinal)
        query+=" FROM (SELECT * FROM mods ORDER BY ordinal)"
        modinfo = []

        # for each row (mod-entry)
        for row in self._con.execute(query):
            # zip fields names and values up and convert to dict to create json-able object
            modinfo.append(dict(zip(noord_fields, row)))

        with json_target.open('w') as f:
            json.dump(modinfo, f, indent=1)


    # db-query convenience methods
    def enabledMods(self, name_only = False):
        """
        Fetches all mods from the mod database that are
        marked as enabled.
        :param name_only: Return only the names of the mods
        :return:
        """
        if name_only:
            yield from (t[0] for t in self._con.execute("select name from mods where enabled = 1"))
        else:
            yield from self._con.execute("select * from mods where enabled = 1")

    def disabledMods(self, name_only = False):
        """
        Fetches all mods from the mod database that are
        marked as disabled.
        :param name_only: Return only the names of the mods
        :return:
        """
        if name_only:
            return [ t[0] for t in self._con.execute("select name from mods where enabled = 0")]
        return self._con.execute("select * from mods where enabled = 0").fetchall()

    def getModInfo(self, raw_cursor = False) :
        """-> Union[List[DBRow], sqlite3.Cursor]
        Returns all information about installed mods as a list
        of tuples.
        :param raw_cursor: If true, return the db cursor object instead of a list.
        :return:  Tuple of mod info or sqlite3.cursor
        """
        cur = self._con.execute("select * from mods")
        if raw_cursor:
            return cur
        yield from cur

    def shutdown(self):
        """
        Close the db connection
        """
        self._con.close()

    def getModDataFromModDirectory(self, mods_dir: Path):
        """
        scan the actual mods-directory and populate the database from there instead of a cached json file.
        Will need to do this on first run and periodically to make sure cache is in sync.
        :param mods_dir:
        :return:
        """
        # TODO: Perhaps this should be run on every startup? At least to make sure it matches the stored data.
        import configparser as _config

        self.logger.info("Reading mods from mod directory")
        configP = _config.ConfigParser()


        mods_list = []
        for moddir in mods_dir.iterdir():
            # skip any non-directories
            if not moddir.is_dir(): continue

            # since this is the creation of the mods list, we just derive the ordinal from
            # order in which the mod-folders are encountered (likely alphabetical)
            order = len(mods_list)+1
            dirname = moddir.name

            inipath = moddir / "meta.ini"
            if inipath.exists():
                # read info from meta.ini (ModOrganizer) file
                configP.read(str(inipath))
                mods_list.append(
                    self.makeModEntry(ordinal = order,
                                      directory = dirname,
                                      modid = configP['General']['modid'],
                                      version = configP['General']['version']
                                     )
                                )
            else:
                mods_list.append(
                    self.makeModEntry(ordinal = order, directory=dirname))

        self.fillTable(mods_list)

    def makeModEntry(self, **kwargs):
        """generates a tuple representing a mod-entry by supplementing a possibly-incomplete mapping of keywords (`kwargs`) with default values for any missing fields"""
        r = []

        for f in constants.db_fields:
            r.append(kwargs.get(f,
                                self.__defaults.get(f, lambda v: "")(kwargs)
                                )
                     )
        return tuple(r)

    def validateModsList(self, installed_mods: List[str]):
        """
        Compare the database's list of mods against a list of the folders in the installed-mods directory. Handle discrepancies accordingly.
        :param installed_mods:
        :return:
        """
        # I wish there were a...lighter way to do this, but I
        # believe only directly comparing dirnames will allow
        # us to provide useful feedback to the user about
        # problems with the mod installation

        dblist = [t[0] for t in self._con.execute("Select directory from mods")]

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

        if not_listed or not_found:
            from skymodman.exceptions import FilesystemDesyncError
            raise FilesystemDesyncError(not_found, not_listed)

        # maybe we should return a False value along with the lists
        # instead of raising an error...hmmm
        return True

    @staticmethod
    def jsonWrite(json_target: Path, pyobject):
        with json_target.open('w') as f:
            json.dump(pyobject, f, indent=1)


    @staticmethod
    def toRowTuple(pairs):
        """
        Used as object_pair_hook for json.load(). Takes the mod
        information loaded from the json file and converts it
        to a tuple of just the field values in the
        correct order for feeding to the sqlite database.
        :param pairs:
        :return:
        """

        return (mcount(), ) + tuple(s[1] for s in sorted(pairs, key=lambda p: constants.db_fields.index(p[0])))


if __name__ == '__main__':
    from skymodman.managers import ModManager

    # test()
    # testload()
    DB = DBManager(ModManager())
    DB._con.row_factory = sqlite3.Row

    DB.loadModDB(Path(os.path.expanduser("~/.config/skymodman/profiles/default/modinfo.json")))

    c= DB.conn.execute("select * from mods")

    print (c.description)

    r=c.fetchone() #type: sqlite3.Row

    print(type(r))

    print(r.keys())
    print(r['directory'])

    print(dict(zip(r.keys(), r)))





    # print(DB.getOne("Select * from mods where ordinal = 22"))
    # [ print(r) for r in DB.execute_("Select * from mods where ordinal BETWEEN 20 AND 24")]
    #
    # DB.conn.execute("DELETE FROM mods WHERE ordinal = 22")
    # [ print(r) for r in DB.execute_("Select * from mods where ordinal BETWEEN 20 AND 24")]
    #
    # DB.conn.execute("INSERT into mods (name, directory, ordinal) VALUES ('boogawooga', 'boogawoogadir', 22)")
    #
    # [ print(r) for r in DB.execute_("Select * from mods where ordinal BETWEEN 20 AND 24")]

    DB.shutdown()

