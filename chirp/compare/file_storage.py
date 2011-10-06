# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
A basic storage system.  The files to be compared are loaded by
globbing a directory, and the output is to a text file.

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-10-05
"""

class file_storage(object):

    def __init__(self, comparator, location=None):
        """
        Initialize the storage object with the location (directory)
        where the data is stored.  Requires access to the object that
        will be doing the comparisons (comparator), to determine the
        file extension and the fields of the output.
        """
        self.location = location or '.'
        self.file_pattern = "*%s" % comparator.file_extension
        self.compare_stat_fields = comparator.compare_stat_fields
        self._load_signals()

    def _load_signals(self):
        """
        Generates a list of input signals by globbing a directory.
        Returns a list of (id, locator) tuples, where the id is an
        integer code and the locator is the path.  Note glob does not
        always return the same ordering of files.
        """
        import os.path
        from glob import iglob
        self.signals = [(i, f) for i,f in \
                            enumerate(iglob(os.path.join(self.location,self.file_pattern)))]

    @property
    def nsignals(self):
        return len(self.signals)
        
    def output_signals(self, cout=None):
        """
        Generate a table of the id/locator assignments. This may not
        be necessary if this information is stored elsewhere.
        """
        print >> cout, "id\tlocation"
        for id,loc in self.signals:
            print >> cout, "%s\t%s" % (id,loc)

    def store_results(self, gen, cout=None):
        """
        For each item in gen, output the resulting comparison.
        """
        print >> cout, "** Results:"
        print >> cout, "ref\ttgt\t" + "\t".join(self.compare_stat_fields)
        for result in gen:
            print >> cout, "\t".join(("%s" % x) for x in result)
        
    def options_str(self):
        out = """\
* Storage parameters:
** Location = %s
** File pattern = %s
** Writing to standard out (fields: %s)""" % (self.location, self.file_pattern,
                                              ",".join(self.compare_stat_fields))
        return out
            
