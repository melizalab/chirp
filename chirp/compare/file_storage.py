# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
A basic storage system.  The files to be compared are loaded by
globbing a directory, and the output is to a text file.

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-10-05
"""

from .base_storage import base_storage as _base_storage
from ..common import _tools


class file_storage(_base_storage):
    _descr = "file stream (LOCATION: [file]; skip/restrict unsupported)"
    _preferred_extension = ".clg"

    def __init__(self, comparator, location, signals=None, **kwargs):
        """
        Initialize the storage object with the location (stream
        object) where the data will be stored.  Requires access to the
        object that will be doing the comparisons (comparator), to
        determine the file extension and the fields of the output.
        """
        import sys
        _base_storage.__init__(self, comparator)
        if isinstance(location, basestring):
            self.cout = open(location, 'wt')
        elif location is None:
            self.cout = sys.stdout
        else:
            self.cout = location
        self._load_signals(signals or '.')

    def _load_signals(self, signal_dir):
        """
        Generates a list of input signals by globbing a directory.
        Returns a list of (id, locator) tuples, where the id is an
        integer code and the locator is the path.  Note glob does not
        always return the same ordering of files.
        """
        import os.path
        from glob import iglob
        self.signals = [(i, f) for i, f in
                        enumerate(iglob(os.path.join(signal_dir, '*' + self.file_pattern)))]

    def output_signals(self):
        """
        Generate a table of the id/locator assignments. This may not
        be necessary if this information is stored elsewhere.
        """
        print >> self.cout, "id\tlocation"
        for id, loc in self.signals:
            print >> self.cout, "%s\t%s" % (id, loc)

    @_tools.consumer
    def store_results(self):
        print >> self.cout, "** Results:"
        print >> self.cout, "ref\ttgt\t" + "\t".join(self.compare_stat_fields)
        try:
            while 1:
                result = yield
                print >> self.cout, "\t".join(("%s" % x) for x in result)
        except GeneratorExit:
            pass

    def options_str(self):
        out = """\
* Storage parameters:
** Location = %s
** File pattern = %s
** Fields: %s""" % (self.cout.name, self.file_pattern,
                    ",".join(self.compare_stat_fields))
        return out

    def write_metadata(self, data):
        """ Provide metadata about the analysis. """
        print data
