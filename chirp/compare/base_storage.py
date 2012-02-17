# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Base class for storage systems.  The storage classes serve two
functions.  The primary purpose is to provide a mechanism for storing
comparison results.  The secondary purpose is to provide a list of
signals that will be compared.  It's convenient to link these because
RDBMS-based backends will typically use an integer ID to index signals
and the comparisons between pairs of signals.

Copyright (C) 2012 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2012-02-16
"""

class base_storage(object):

    def __init__(self, comparator):
        self.file_pattern = comparator.file_extension
        self.compare_stat_fields = comparator.compare_stat_fields
        self.symmetric = comparator.symmetric

    @property
    def nsignals(self):
        """ The number of signals stored in the object """
        return len(self.signals)

    def pairs(self):
        """ Yields the keys for the pairs of signals to be compared """
        from itertools import product
        items = [k for k,v in self.signals]
        if self.symmetric:
            for i,v1 in enumerate(items):
                for v2 in items[i:]: yield v1,v2
        else:
            for v1,v2 in product(items,items): yield v1,v2

# Variables:
# End:
