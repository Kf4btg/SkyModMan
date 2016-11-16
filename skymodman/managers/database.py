from pathlib import PurePath
from itertools import repeat
from collections import defaultdict, namedtuple

from skymodman.managers.base import Submanager, BaseDBManager

from skymodman.log import withlogger
from skymodman.utils import tree


# max number of vars for sqlite query is 999
_SQLMAX=900

# DB schema definition
# note -- if 'managed' is 0/False, the mod should be in <skyrim-install>/Data/
# rather than <mods-folder>/<directory>
# TODO: 'directory' should probably be renamed, then, since it's not accurate for unmanaged mods
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
        Does not check for an empty mods table.

        :param mod_list: list of mod entries
        """
        self.LOGGER << "<==Method call"

        with self.conn as con:
            c=con.executemany(
                "INSERT INTO mods VALUES (?, ?)",
                ((m.directory, m.managed)
                 for m in mod_list)
            )

            if c.rowcount:
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

        _q = """DELETE FROM hiddenfiles
                WHERE directory = '{mdir}'
                AND filepath IN ({paths})"""

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


    def hidden_files(self, for_mod):
        """
        Obtain paths of currently hidden files for the given mod

        :param for_mod: directory name of the mod
        :return: the cursor of the executed command. can be used
            as an iterator.
        """

        return self.conn.execute(
            "SELECT filepath FROM hiddenfiles "
            "WHERE directory = ? ORDER BY filepath", (for_mod, )
        )

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
