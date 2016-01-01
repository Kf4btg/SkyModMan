import sqlite3
from _sqlite3 import Error as sqlError
import json
import json.decoder
import os
from typing import TypeVar, List, Tuple, Union
from pathlib import Path

import constants
from utils import withlogger

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

    def __init__(self, manager):
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
        return self.getModInfo()


    # db modification
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
                    self.logger.debug("Old Value for enabled: {}".format(
                            self._con.execute("select enabled from mods where iorder = ?", (row, )).fetchall()))

                    self._con.execute("UPDATE mods SET enabled = ? WHERE iorder = ?", (int(value), row))

                    self.logger.debug("New Value for enabled: {}".format(
                        self._con.execute("select enabled from mods where iorder = ?", (row,)).fetchall()))
            except sqlError as e:
                self.logger.error("SQL transaction error when updating mod enabled state: '{}'".format(e))
                success = False
        elif col == constants.COL_NAME:
            assert isinstance(value, str)

            try:
                with self._con:
                    self.logger.debug("Old Value for name: {}".format(
                            self._con.execute("select name from mods where iorder = ?", (row,)).fetchall()))

                    self._con.execute("UPDATE mods SET name = ? WHERE iorder = ?", (value, row))

                    self.logger.debug("New Value for name: {}".format(
                            self._con.execute("select name from mods where iorder = ?", (row,)).fetchall()))
            except sqlError as e:
                self.logger.error("SQL transaction error when updating mod name: '{}'".format(e))
                success = False

        else:
            self.logger.error("Column {} is not a modifiable field.".format(col))
            success = False

        return success



    # convenience methods
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

    def getModInfo(self, raw_cursor = False) -> Union[List[DBRow], sqlite3.Cursor]:
        """
        Returns all information about installed mods as a list
        of tuples.
        :param raw_cursor: If true, return the db cursor object instead of a list.
        :return:  Tuple of mod info or sqlite3.cursor
        """
        cur = self._con.execute("select * from mods")
        if raw_cursor:
            return cur
        return cur.fetchall()

    def shutdown(self):
        """
        Close the db connection
        """
        self._con.close()


    def loadModDB(self, json_source):
        """
        read the saved mod information from a json file and
        populate the in-memory database
        :param json_source: path to saved info in json format
        """

        if not isinstance(json_source, Path):
            json_source = Path(json_source)

        success = True
        with json_source.open('r') as f:
            # read from json file and convert mappings
            # to ordered tuples for sending to sqlite
            try:
                mods = json.load(f, object_pairs_hook=self.toRowTuple)

                with self._con:
                    # insert the list of row-tuples into the in-memory db
                    self._con.executemany("INSERT INTO mods(modid, version, directory, name, enabled) VALUES (?, ?, ?, ?, ?)", mods)

            except json.decoder.JSONDecodeError as e:
                self.logger.error("No mod information present in {}, or file is malformed.")
                success = False
        return success

    def saveModDB(self, json_target):
        """
        Write the data from the in-memory database to a
        json file on disk. The file will be overwritten, or
        created if it does not exist
        :param json_target:
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


    def getModDataFromModDirectory(self, mods_dir):
        """
        scan the actual mods-directory and populate the database from there instead of a cached json file.
        Will need to do this on first run and periodically to make sure cache is in sync.
        TODO: Perhaps this should be run on every startup? At least to make sure it matches the stored data.
        :return:
        """
        import configparser

        # def modListFromDirectory(self, mod_install_dir: str) -> List[Tuple[str, str, str]] :
        #     """
        #     Examine the configured mods-directory and create a list of installed mods where each folder in said directory is considered a mod. If a meta.ini file (in the format used by ModOrganizer) exists in a mod's folder, extra mod details are read from it.
        #     :param mod_install_dir:
        #     :return: A list of tuples in the form (mod-name, mod-id, mod-version)
        #     """
        #
        self.logger.info("Reading mods from mod directory")
        #
        configP = configparser.ConfigParser()


        mods_list = []
        for moddir in os.listdir(mods_dir):
            inipath = "{}/{}/{}".format(mods_dir, moddir, "meta.ini")
            if os.path.exists(inipath):
                configP.read(inipath)
                # insert tuples in form that db will expect
                mods_list.append((configP['General']['modid'], configP['General']['version'], moddir, moddir, 1))
            else:
                mods_list.append((0, "", moddir, moddir, 1))

        with self._con:
            self._con.executemany("INSERT INTO mods(modid, version, directory, name, enabled) VALUES (?, ?, ?, ?, ?)",
                                  mods_list)




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
            "directory": name,
            "name": name,
            "version": ver,
            "enabled": active
        })

    con.close()

    # dumping info as a list allows keeping the
    # correct order when reloading without having
    # to store the order index
    with open("res/modinfo.json",'w') as f:
        json.dump(modinfo, f, indent=1)



    # print(mods)
# from pprint import pprint

__fields = ["id", "version", "directory", "name", "enabled"]

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

    return tuple(d[__fields[i]] for i in range(len(__fields)))

def loadDB(jsonfile: str) -> sqlite3.Connection:
    # create db in memory
    con = sqlite3.connect(":memory:")

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
    con.execute("CREATE TABLE mods (iorder INTEGER primary key, modid INTEGER, version TEXT, directory TEXT unique, name TEXT, enabled INTEGER)")

    with open(jsonfile, 'r') as f:
        # read from json file and convert mappings
        # to ordered tuples for sending to sqlite
        mods = json.load(f, object_pairs_hook=toRowTuple)

    with con:
        # insert the list of row-tuples into the in-memory db
        con.executemany("INSERT INTO mods(modid, version, directory, name, enabled) VALUES (?, ?, ?, ?, ?)", mods)

    return con

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
    from manager import ModManager

    # test()
    testload()