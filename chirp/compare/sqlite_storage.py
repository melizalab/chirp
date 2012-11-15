# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
A database storage system.  The files to be compared are loaded from a
database, and the output is to a table in the database.  Uses sqlite
as a backend.

Copyright (C) 2011 Daniel Meliza <dan // meliza.org> Created
2011-10-05
"""
import os,sqlite3,glob
from .base_storage import base_storage as _base_storage
from ..common import _tools

sql_create_filelist = """\
CREATE TABLE IF NOT EXISTS %s (
`id` INTEGER NOT NULL,
`filename` VARCHAR(512) UNIQUE NOT NULL,
PRIMARY KEY (`id` ASC AUTOINCREMENT))
"""

sql_create_target = """\
CREATE TABLE IF NOT EXISTS %s (
`id` INTEGER NOT NULL,
`ref` INTEGER NOT NULL REFERENCES %s(id),
`tgt` INTEGER NOT NULL REFERENCES %s(id),
%s,
PRIMARY KEY (`id` ASC AUTOINCREMENT))
"""

class sqlite_storage(_base_storage):
    _descr = "sqlite database (LOCATION: database file)"
    _preferred_extension = ".db"
    signal_table = "signals"

    def __init__(self, comparator, location, signals=None, restrict=False, skip=False, **kwargs):
        """
        Initialize the storage object with the location where the data
        is stored.

        @param location  the path of a sqlite database (created as needed)
        @param signals   the directory where the signals are located
        @param restrict  if True, only include signals already stored in the database;
                         if False, signals will be added to the database
        @param skip      if True, pairs() will only return uncompleted calculations
        """
        _base_storage.__init__(self, comparator)
        self.location = location
        self.table_name = type(comparator).__name__
        self.restrict = restrict
        self.skip = skip
        self._load_signals(signals or '.')

    def _load_signals(self, signal_dir):
        """
        Generates a list of input signals by globbing a directory.
        Returns a list of (id, locator) tuples, where the id is an
        integer code and the locator is the path.  Note glob does not
        always return the same ordering of files.
        """
        con = sqlite3.connect(self.location)
        with con:
            con.execute(sql_create_filelist % self.signal_table)
            files = glob.glob(os.path.join(signal_dir, "*" + self.file_pattern))
            if not self.restrict:
                con.executemany("INSERT OR IGNORE INTO %s (filename) VALUES (?)" % self.signal_table,
                                ((os.path.splitext(os.path.split(x)[1])[0],) for x in files))
            cursor = con.execute("SELECT id,filename FROM %s ORDER BY id" % self.signal_table)
            self.signals = [(i,os.path.join(signal_dir,f+self.file_pattern)) for i,f in cursor.fetchall() \
                                if os.path.join(signal_dir, f+self.file_pattern) in files]


    def _create_target_table(self, con, values):
        sql_columns = ",\n".join("`%s` %s" % (name,sqlite_type(val)) for \
                                   name,val in zip(self.compare_stat_fields, values[2:]))
        sql = sql_create_target % (self.table_name, self.signal_table, self.signal_table, sql_columns)
        if not self.skip:
            con.execute("DROP TABLE IF EXISTS %s" % self.table_name)
        con.execute(sql)

    def pairs(self):
        if self.skip:
            try:
                con = sqlite3.connect(self.location)
                cur = con.execute("SELECT ref,tgt FROM %s" % self.table_name)
                done = [(r,t) for r,t in cur.fetchall()]
                for k1,k2 in _base_storage.pairs(self):
                    if (k1,k2) not in done: yield k1,k2
                return
            except sqlite3.OperationalError:
                # table probably doesn't exist; go to fallback
                pass
        for k1,k2 in _base_storage.pairs(self): yield k1,k2

    def output_signals(self):
        """
        Generate a table of the id/locator assignments. This may not
        be necessary if this information is stored elsewhere.
        """
        pass

    @_tools.consumer
    def store_results(self):
        """
        Store comparisons. This function returns a generator; use
        send() to store each comparison as it's available.  If not
        skipping completed comparisons, the target table is dropped
        and recreated.
        """
        # create table using types of first yielded result
        cols = ("ref","tgt") + tuple(self.compare_stat_fields)
        sql1 =  "INSERT OR IGNORE INTO %s (%s) VALUES (%s)" % (self.table_name,
                                                    ",".join(cols),
                                                    ",".join("?" for x in cols))
        cols = ("tgt","ref") + tuple(self.compare_stat_fields)
        sql2 =  "INSERT OR IGNORE INTO %s (%s) VALUES (%s)" % (self.table_name,
                                                    ",".join(cols),
                                                    ",".join("?" for x in cols))
        con = sqlite3.connect(self.location)
        with con:
            try:
                result = yield
                self._create_target_table(con, result)
                con.execute(sql1,result)
                if self.symmetric and result[0]!=result[1]: con.execute(sql2,result)
                while 1:
                    result = yield
                    con.execute(sql1,result)
                    if self.symmetric and result[0]!=result[1]: con.execute(sql2,result)
            except GeneratorExit:
                pass

    def options_str(self):
        out = """\
* Storage parameters:
** Location = %s
** File pattern = %s
** Add files to database = %s
** Skip pairs already in database = %s
** Writing to table %s:%s (fields: %s)""" % (self.location, self.file_pattern,
                                             not self.restrict, self.skip,
                                             self.location, self.table_name,
                                             ",".join(self.compare_stat_fields))
        return out

    def write_metadata(self, data):
        """ Provide metadata about the analysis. With sqlite this just gets dumped to stdout """
        print data

# register some sqlite converters
import numpy
def adapt_numpy(val):
    return val.tolist()
sqlite3.register_adapter(numpy.int32,adapt_numpy)
sqlite3.register_adapter(numpy.int64,adapt_numpy)
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
