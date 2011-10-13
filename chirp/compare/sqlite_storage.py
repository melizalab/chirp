# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
A database storage system.  The files to be compared are loaded from a
database, and the output is to a table in the database.  Uses sqlite
as a backend.

Copyright (C) 2011 Daniel Meliza <dan // meliza.org> Created
2011-10-05
"""
import os,sqlite3

sql_create_target = """\
CREATE TABLE %s (
`id` INTEGER NOT NULL,
`ref` INTEGER NOT NULL REFERENCES %s(id),
`tgt` INTEGER NOT NULL REFERENCES %s(id),
%s,
PRIMARY KEY (`id` ASC AUTOINCREMENT))
"""

class sqlite_storage(object):

    def __init__(self, comparator, location):
        """
        Initialize the storage object with the location where the data
        is stored.  This has the form <path>:<table>, where path is
        the location of a sqlite database, and table is a table with
        at least the following fields (id, location). Requires access
        to the object that will be doing the comparisons (comparator),
        to determine the file extension and the fields of the output.
        """
        self.location = location
        self.file_pattern = "%s" % comparator.file_extension
        self.compare_stat_fields = comparator.compare_stat_fields
        self.table_name = "superb_" + type(comparator).__name__
        self.symmetric = comparator.symmetric
        self.signals = []
        self._load_signals()


    def _load_signals(self):
        """
        Generates a list of input signals by globbing a directory.
        Returns a list of (id, locator) tuples, where the id is an
        integer code and the locator is the path.  Note glob does not
        always return the same ordering of files.
        """
        path,table = self.location_parts
        self.connection = sqlite3.connect(path)
        cursor = self.connection.cursor()
        cursor.execute("SELECT id,filename FROM %s ORDER BY id" % table)
        self.signals = [(i,f+self.file_pattern) for i,f in cursor.fetchall()]

    def _create_target_table(self, values):
        signal_table = self.location_parts[1]
        sql_columns = ",\n".join("`%s` %s" % (name,sqlite_type(val)) for \
                                   name,val in zip(self.compare_stat_fields, values[2:]))
        sql = sql_create_target % (self.table_name, signal_table, signal_table, sql_columns)
        self.connection.execute("DROP TABLE IF EXISTS %s" % self.table_name)
        self.connection.execute(sql)

    @property
    def location_parts(self):
        """ A tuple of the database path and the source table """
        try:
            path,table = self.location.split(":")
        except (AttributeError, ValueError):
            raise ValueError, "Invalid database location (path:table)"
        if not os.path.exists(path):
            raise ValueError, "Invalid database location (path does not exist)"
        return path,table

    @property
    def nsignals(self):
        return len(self.signals)


    def output_signals(self, cout=None):
        """
        Generate a table of the id/locator assignments. This may not
        be necessary if this information is stored elsewhere.
        """
        pass

    def store_results(self, gen, cout=None):
        """
        For each item in gen, store the resulting comparison.  The
        target table is dropped and reinitialized.
        """
        # create table using types of first yielded result
        cols = ("ref","tgt") + tuple(self.compare_stat_fields)
        sql1 =  "INSERT INTO %s (%s) VALUES (%s)" % (self.table_name,
                                                    ",".join(cols),
                                                    ",".join("?" for x in cols))
        cols = ("tgt","ref") + tuple(self.compare_stat_fields)
        sql2 =  "INSERT INTO %s (%s) VALUES (%s)" % (self.table_name,
                                                    ",".join(cols),
                                                    ",".join("?" for x in cols))

        result = gen.next()
        with self.connection:
            self._create_target_table(result)
            self.connection.execute(sql1,result)
            if self.symmetric: self.connection.execute(sql2,result)
            for result in gen:
                self.connection.execute(sql1,result)
                if self.symmetric: self.connection.execute(sql2,result)

    def options_str(self):
        out = """\
* Storage parameters:
** Location = %s
** File pattern = %s
** Writing to table %s:%s (fields: %s)""" % (self.location, self.file_pattern,
                                          self.location_parts[0], self.table_name,
                                          ",".join(self.compare_stat_fields))
        return out

# register some sqlite converters
import numpy
def adapt_numpy(val):
    return val.tolist()
sqlite3.register_adapter(numpy.int32,adapt_numpy)
sqlite3.register_adapter(numpy.float32,adapt_numpy)
sqlite3.register_adapter(numpy.float64,adapt_numpy)

def sqlite_type(value):
    if isinstance(value,basestring):
        return 'TEXT'
    elif isinstance(value,float):
        return 'REAL'
    elif isinstance(value,(long,int)):
        return 'INTEGER'
    else:
        raise TypeError, "Can't match type (%s) with sqlite type" % type(value)
