import json
import json.decoder
import os
import sqlite3
from _sqlite3 import Error as sqlError
from pathlib import Path
from typing import List, Tuple, Union, Iterable

from skymodman import constants
from skymodman.utils import withlogger

_iorder = int
_modid = int
_modver = str
_moddir = str
_modname = str
_modenabled = int

DBRow = Tuple[_iorder,
              _modid,
              _modver,
              _moddir,
              _modname,
              _modenabled
             ]

@withlogger
class DBManager:

    _SCHEMA = """CREATE TABLE mods (
            iorder    INTEGER primary key,
            modid     INTEGER,
            version   TEXT,
            directory TEXT    unique,
            name      TEXT,
            enabled   INTEGER default 1
        )"""

    __fields = ["modid", "version", "directory", "name", "enabled"]

    def __init__(self, manager: 'ModManager'):
        super(DBManager, self).__init__()

        self.manager = manager

        # create db in memory
        self._con = sqlite3.connect(":memory:")

        # create the mods table
        # NOTE: `iorder` (i.e. the mod "install-order") is not
        # stored on disk with the rest of the mod info; it is
        # instead inferred from the order in which the mods
        # are listed in the config file and the number auto-
        # generated by sqlite
        # NOTE2: `directory` is the name of the folder in the
        # mods-directory where the files for this mod are saved.
        # `name` is initially equivalent, but can be changed as
        # desired by the user.
        self._con.execute(self._SCHEMA)

    @property
    def conn(self) -> sqlite3.Connection:
        """
        Directly access the database connection of this manager
        in order to perform custom queries.
        :return:
        """
        return self._con

    @property
    def mods(self) -> List[DBRow]:
        """
        Return list of all mods from the mod db
        :return:
        """
        return self.getModInfo(True).fetchall()


    def loadModDB(self, json_source):
        """
        read the saved mod information from a json file and
        populate the in-memory database
        :param json_source: path to modinfo.json file (either pathlib.Path or string)
        """

        if not isinstance(json_source, Path):
            json_source = Path(json_source)

        success = True
        with json_source.open('r') as f:
            # read from json file and convert mappings
            # to ordered tuples for sending to sqlite
            try:
                mods = json.load(f, object_pairs_hook=DBManager.toRowTuple)

                with self._con:
                    # insert the list of row-tuples into the in-memory db
                    self._con.executemany(
                        "INSERT INTO mods(modid, version, directory, name, enabled) VALUES (?, ?, ?, ?, ?)", mods)

            except json.decoder.JSONDecodeError:
                self.logger.error("No mod information present in {}, or file is malformed.")
                success = False
        return success

    def execute_(self, query:str, *args, params: Iterable=None):
        """
        Execute an arbitrary SQL-query using this object's
        database connection as a context manager
        :param query: a valid SQL string
        :param args: any non-keyword arguments after the query-string will be used in a tuple as the parameter-argument to a parameterized sql-query
        :param params: If, instead of args, the `params` keyword is provided with an Iterable object, that will be used for the query parameters. Ignored if any args are present.
        :return:
        """
        with self._con:
            if args:
                yield from self._con.execute(query, args)
            elif params:
                yield from self._con.execute(query, params)
            else:
                yield from self._con.execute(query)

    def getOne(self, query, *args, params: Iterable=None):
        """
        Like execute_, but just returns the first result
        :param query:
        :param args:
        :param params:
        :return:
        """
        with self._con:
            if args:
                cur=self._con.execute(query, args)
            elif params:
                cur=self._con.execute(query, params)
            else:
                cur=self._con.execute(query)

            return cur.fetchone()


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

        modinfo = []
        for row in self._con.execute("SELECT * FROM mods"):
            order, modid, ver, mdir, name, enabled = row

            modinfo.append({
                "modid": modid,
                "version": ver,
                "directory": mdir,
                "name": name,
                "enabled": enabled
            })

        with json_target.open('w') as f:
            json.dump(modinfo, f, indent=1)

    # db modification convenience method
    def updateField(self, row: int, col: int, value) -> bool:
        """
        Modify the value of the `enabled` or `name` attribute for the mod at place `row` in the install order
        :param row: install order (index) of mod
        :param col: which field to modify; must be either constants.COL_ENABLED or constants.COL_NAME
        :param value: if col==COL_ENABLED, must be either `True` or `False`. if COL_NAME, must be a string
        :return: True or False depending on whether transaction succeeded or not
        """
        success = True
        if col == constants.COL_ENABLED:
            assert isinstance(value, bool)

            try:
                with self._con:
                    # self.LOGGER.debug("Old Value for enabled: {}".format(
                    #         self._con.execute("select enabled from mods where iorder = ?", (row, )).fetchall()))

                    self._con.execute("UPDATE mods SET enabled = ? WHERE iorder = ?", (int(value), row))

                    # self.LOGGER.debug("New Value for enabled: {}".format(
                    #     self._con.execute("select enabled from mods where iorder = ?", (row,)).fetchall()))
            except sqlError as e:
                self.LOGGER.error("SQL transaction error when updating mod enabled state: '{}'".format(e))
                success = False

        elif col == constants.COL_NAME:
            assert isinstance(value, str)

            try:
                with self._con:
                    # self.LOGGER.debug("Old Value for name: {}".format(
                    #         self._con.execute("select name from mods where iorder = ?", (row,)).fetchall()))

                    self._con.execute("UPDATE mods SET name = ? WHERE iorder = ?", (value, row))

                    # self.LOGGER.debug("New Value for name: {}".format(
                    #         self._con.execute("select name from mods where iorder = ?", (row,)).fetchall()))
            except sqlError as e:
                self.LOGGER.error("SQL transaction error when updating mod name: '{}'".format(e))
                success = False

        else:
            self.LOGGER.error("Column {} is not a modifiable field.".format(col))
            success = False

        return success


    # db-query convenience methods
    def enabledMods(self, name_only = False):
        """
        Fetches all mods from the mod database that are
        marked as enabled.
        :param name_only: Return only the names of the mods
        :return:
        """
        if name_only:
            return [ t[0] for t in self._con.execute("select name from mods where enabled = 1")]
        return self._con.execute("select * from mods where enabled = 1").fetchall()

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
            if not moddir.is_dir(): continue
            inipath = moddir / "meta.ini"
            dirname = moddir.name
            if inipath.exists():
                configP.read(str(inipath))
                # insert tuples in form that db will expect;
                # set name = directory, default value of 1 for enabled
                mods_list.append((configP['General']['modid'], configP['General']['version'], dirname, dirname, 1))
            else:
                # set name = directory, default value of 1 for enabled,
                # 0 for modid, and empty str for version
                mods_list.append((0, "", dirname, dirname, 1))

        with self._con:
            self._con.executemany("INSERT INTO mods(modid, version, directory, name, enabled) VALUES (?, ?, ?, ?, ?)",
                                  mods_list)

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
    def toRowTuple(pairs):
        """
        Used as object_pair_hook for json.load(). Takes the mod
        information loaded from the json file and converts it
        to a tuple containing just the field values in the
        correct order for feeding to the sqlite database.
        :param pairs:
        :return:
        """

        d = dict(pairs)

        return tuple(d[DBManager.__fields[i]] for i in range(len(DBManager.__fields)))




def test():

    testdb = "res/test.db"

    if not os.path.exists(testdb):
        MM = ModManager()
        con = sqlite3.connect(testdb)
        con.execute("CREATE TABLE mods (id INTEGER primary key, modid INTEGER, version VARCHAR, name VARCHAR unique, enabled INTEGER)")

        mods = []
        for m in MM.installed_mods:
            if m[0] in MM.mod_states["Active"]:
                mods.append(m + (1, ))
            else:
                mods.append(m + (0, ))

        with con:
            con.executemany("INSERT INTO mods(name, modid, version, enabled) VALUES (?, ?, ?, ?)", mods)
    else:
        con = sqlite3.connect(testdb)


    modinfo = []
    for row in con.execute("SELECT * FROM mods"):
        order, mid, ver, name, active = row

        modinfo.append({
            "id": mid,
            "version": ver,
            "directory": name,
            "name": name,
            "enabled": active
        })

    con.close()

    # dumping info as a list allows keeping the
    # correct order when reloading without having
    # to store the order index
    with open("res/modinfo.json",'w') as f:
        json.dump(modinfo, f, indent=1)


def testload():

    # con = loadDB("res/modinfo.json")

    DB = DBManager(ModManager())

    # check
    # for row in con.execute("SELECT iorder, name FROM mods WHERE enabled = 0"):
    #     print(row)

    DB.loadModDB("res/modinfo.json")

    # [print(r) for r in DB.mods]
    # [print(r) for r in DB.enabledMods(True)]
    # [print(r) for r in DB.disabledMods(True)]

    DB.updateField(4, constants.COL_ENABLED, True)

    DB.updateField(4, constants.COL_NAME, "New name")

    # print(DB.disabledMods(True))

    # close db
    # con.close()
    DB.shutdown()

if __name__ == '__main__':
    from skymodman.managers import ModManager

    # test()
    testload()