import sqlite3



# TODO: remove this; this issue is apparently fixed in python 3.6
# this Connection subclass courtesy of Ryan Kelly:
# http://code.activestate.com/lists/python-list/189197/
# during a discussion of the problems with savepoints
# and the mystery of python's isolation-levels
class HappyConn(sqlite3.Connection):
    def __enter__(self):
        self.execute("BEGIN")
        return self
    def __exit__(self, exc_type, exc_info, traceback):
        if exc_type is None:
            self.execute("COMMIT")
        else:
            self.execute("ROLLBACK")

def getconn(path):
    """
    return a modified Connection with its isolation level set to
    ``None`` and sensible commit/rollback policies when used as a
    context manager.
    """
    conn = sqlite3.connect(path, factory=HappyConn)
    # "isolation_level = None" seems like a simple-enough thing
    # to understand, but in truth it replaces the dark magic
    # of pysqlite's auto-transactions with a new kind of dark
    # magic that, at the least, allows us to avoid spurious
    # auto-commits and enables savepoints (which are totally
    # broken under the default isolation level). It requires
    # paying a bit of extra attention and making sure to issue
    # the appropriate BEGIN, ROLLBACK, and COMMIT commands.
    conn.isolation_level = None
    return conn

class BaseDBManager:

    def __init__(self, db_path, schema, table_names,
                 logger=None,
                 row_factory=sqlite3.Row, *args, **kwargs):

        # noinspection PyArgumentList
        super().__init__(*args, **kwargs)

        # create our connection
        self._con = getconn(db_path)

        # execute the schema
        self._con.executescript(schema)

        # set the default row factory
        self._con.row_factory = row_factory

        self._tablenames = tuple(table_names)

        # use subclass' logger
        self._log = logger


    ##=============================================
    ## Properties
    ##=============================================

    @property
    def conn(self) -> sqlite3.Connection:
        """
        Directly access the database connection of this manager
        in order to perform custom queries.
        """
        return self._con

    @property
    def in_transaction(self):
        return self._con.in_transaction

    ##=============================================
    ## Transaction Management
    ##=============================================

    def checktx(self):
        """Check if the connection is in a transaction. If not, begin one"""
        if not self._con.in_transaction:
            self._con.execute("BEGIN")

    def savepoint(self, name="last"):
        """
        Create a savepoint in the database with name `name`. If, later,
        ``rollback()`` is called with the same name as a parameter, the
        database will revert to the state it was in when the savepoint
        was created, rather than all the way to the beginning of the
        transaction.

        :param name: name of the savepoint; does not need to be unique.
            If not provided, the name 'last' will be used.
            ``rollback("last")`` will then return to the most recent
            time savepoint() was called.
        :return:
        """

        self.checktx()

        self._con.execute("SAVEPOINT {}".format(
            # don't allow whitespace;
            # take the first element of name split on ws
            # to enforce this
            name.split()[0])
        )

    ##############
    ## wrappers ##
    ##############

    def commit(self):
        """
        Commit the current transaction. Logs a warning if there is no
        active transaction to commit
        """
        if not self._con.in_transaction and self._log:
            self._log.warning(
                "Database not currently in transaction."
                " Committing anyway.")

        self._con.execute("COMMIT")

    def rollback(self, savepoint=None):
        """Rollback the current transaction. If a savepoint name is
        provided, rollback to that savepoint"""

        if self._con.in_transaction:
            if savepoint:
                self._con.execute("ROLLBACK TO {}".format(
                    savepoint.split()[0]))
            else:
                self._con.execute("ROLLBACK")
                # self._con.rollback()
        elif self._log:
            # i'm aware that a rollback without transaction isn't
            # an error or anything; but if there's nothing to rollback
            # and rollback() is called, then I likely did something
            # wrong and I want to know that
            self._log.warning("nothing to rollback")

    def shutdown(self):
        """
        Close the db connection
        """
        self._con.close()

    def select(self, *fields, FROM, WHERE="", params=()):
        """
        Execute a SELECT statement for the specified fields from
        the named table, optionally using a WHERE constraint and
        parameters sequences. This method returns the cursor object
        used to execute the statment (which can then be used in a
        "yield from" statement or e.g. turned into a sequence
        with fetchall() )

        :param fields: columns/fields to choose from each matching row.
            If none are provided, then "*" will be used to select all
            columns
        :param FROM: name of the database table to select from
        :param WHERE: a SQL 'WHERE' constraint, minus the "WHERE"
        :param params: parameter sequence to match any "?" in the query

        :rtype: sqlite3.Cursor

        """


        if FROM not in self._tablenames:
            raise KeyError(FROM)
            # raise exceptions.DatabaseError(
            #     "'{}' is not a valid from_table name".format(
            #         from_table))

        _q = "SELECT {flds} FROM {tbl}{whr}".format(
            flds=", ".join(fields) if fields else "*",
            tbl=FROM,
            whr=" WHERE {}".format(WHERE) if WHERE else ""
        )

        return self._con.execute(_q, params)

    def selectone(self, *fields, FROM, WHERE="", params=()):
        """
        Like ``select()``, but just returns the first row from the result
        of the query
        """
        return self.select(*fields,
                           FROM=FROM,
                           WHERE=WHERE,
                           params=params).fetchone()

    def update(self, sql, params=(), many=False):
        """
        Like select(), but for UPDATE, INSERT, DELETE, etc. commands.
        Returns the cursor object that was created to execute the
        statement. The changes made are NOT committed before this
        method returns; call commit() (or call this method while
        using the connection as a context manager) to make sure they're
        saved.

        :param str sql: a valid sql query
        :param many: is this an ``executemany`` scenario?
        :param typing.Iterable params:
        """
        self.checktx()

        cmd = self._con.executemany if many else self._con.execute
        # return self._con.execute(sql, params)
        return cmd(sql, params)

    def delete(self, FROM, WHERE="", params=(), many=False):
        """
        Delete entries from a database table.

        :param FROM:
        :param WHERE: if omitted, ALL rows in the table will be reomved
        :param params:
        :param many: is this an ``executemany`` situation?
        :return: cursor object
        """
        self.checktx()

        cmd = self._con.executemany if many else self._con.execute

        return cmd("DELETE FROM {tbl}{whr}".format(
            tbl=FROM,
            whr=(" WHERE %s" % WHERE) if WHERE else ""
        ), params)

    def insert(self, values_count, table, *fields, params=(),
               many=True):
        """
        e.g.:

            >>> insert(2, "datatable", "firstname", "address", params=ftuple_list)
            executemany('INSERT INTO datatable(firstname, address) VALUES (?, ?)', ftuple_list)

        :param int values_count: number of ? to use for the values
        :param str table: name of table
        :param fields: optional field names for table (if any are
            provided, the total number provided must equal `values_count`)
        :param params:
        :param many: if True (the default) use an executemany() command
            rather than an execute() command
        :return: cursor created by execution
        """
        self.checktx()

        cmd = self._con.executemany if many else self._con.execute

        return cmd("INSERT INTO {tbl}{flds} VALUES {vals}".format(
            tbl=table,
            flds=('(%s)' % ", ".join(fields)) if fields else "",
            vals='?' if values_count == 1
            else '({})'.format(", ".join('?' * values_count))
        ), params)

    def count(self, table, **kwargs):
        """
        Get a count of items in the given table. If no keyword arguments
        are provide, get total count of all rows in the table. If
        keyword args are given that correspond to (field_name=value)
        pairs, return count of rows matching those condition(s).
        """

        if table not in self._tablenames:
            raise KeyError(table)

        if not kwargs:
            return int(self._con.execute(
                f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        else:
            q = f"SELECT COUNT(*) FROM {table} WHERE "
            keys = []
            vals = []
            ## do this to make sure the keys and their associated
            ## values are properly matched (same index)
            for k, v in kwargs.items():
                keys.append(k)
                vals.append(v)

            q += ", ".join(["{} = ?".format(k) for k in keys])
            return int(self._con.execute(q, vals).fetchone()[0])