# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Storage and IO of pitch estimates and associated statistics.

pitchtrace: class for storing estimates from one or more chain.
            Can summarize across chains to plg format.

read():     read plg file into recarray. In plg format the data
            have been summarized across chains.

Copyright (C) 2011 Dan Meliza <dan // meliza.org>
Created 2011-08-06
"""

import re
_el_rx = re.compile(r"\*+ .*lement ([0-9]+)")

class Error(Exception):
    pass

_default_extension = '.plg'

class pitchtrace(object):
    """
    Stores time-varying pitch estimates, optionally from multiple chains.
    """
    def __init__(self, tgrid, pmmse, pvar, **kwargs):
        """
        Initialize the object, doing some minimal error
        checking. Required arguments:

        tgrid: the time of each analysis frame (1D array)
        pmmse: the mean of the particle distribution in each frame (1 or 2D)
        pvar:  the variance of the distribution (1 or 2D)

        For estimates, the first dimension corresponds to time, and the second
        to the estimation chain.

        Any number of additional 1D or 2D variables may be supplied as keyword arguments
        """
        self.tgrid = tgrid

        if self.nframes != pmmse.shape[0]: raise ValueError, "Dimensions of MMSE estimate don't match time grid"
        if self.nframes != pvar.shape[0]: raise ValueError, "Dimensions of variance estimate don't match time grid"
        if pmmse.shape[1] != pvar.shape[1]: raise ValueError, "Number of chains doesn't match for mean and variance"

        self.pmmse = pmmse
        self.pvar  = pvar
        self.estimates = dict()

        for k,v in kwargs.items():
            if v is None: continue
            if self.nframes != v.shape[0]: raise ValueError, "Dimensions of %s don't match time grid" % k
            if v.ndim > 1 and self.nchains != v.shape[1]:
                raise ValueError, "Wrong number of chains for %s (needs to be 1 or %d)" % (k, self.nchains)
            self.estimates[k] = v

    @property
    def nframes(self): return self.tgrid.size

    @property
    def nchains(self): return self.pmmse.shape[1]

    def offset(self, val):
        """ Adjust time grid by value """
        self.tgrid += val

    def torec(self):
        """
        Returns a recarray, averaging across chains as needed.
        """
        from numpy import sqrt, rec
        fields = ['time','p.sd','p.mmse']
        values = [self.tgrid, sqrt(_reduce(self.pvar)), _reduce(self.pmmse)]
        if self.nchains > 1:
            fields.append("p.mmse.sd")
            values.append(self.pmmse.std(1))
        for k,v in self.estimates.items():
            fields.append(k)
            values.append(_reduce(v))
            if v.ndim > 1:
                fields.append(k + ".sd")
                values.append(v.std(1))
        return rec.fromarrays(values, names=fields)

    def write(self, cout):
        """
        Print statistics of estimators, averaging across chains. This
        is the format used by read()
        """
        from numpy import savetxt
        rec = self.torec()
        print >> cout, "\t".join(rec.dtype.names)

        fmt = ["%6.2f"] + [_fmt(v) for k,v in rec.dtype.descr[1:]]
        savetxt(cout, rec, delimiter="\t", fmt=fmt)


def read(filename):
    """
    Parse a ptracker log file (plg) for the pitch trace.  Returns a
    numpy recarray, with element number is indicated by a separate
    field.  Note that this is different from the pitchtrace object
    that's used to store data on separate chains.
    """
    from numpy import rec
    current_element = -1
    field_names = None
    records = []
    with open(filename,'rt') as fp:
        for line in fp:
            m = _el_rx.match(line)
            if m:
                current_element = int(m.group(1))
            elif line.startswith("time"):
                field_names = line.split()
            elif line[0] not in ('*','+','-'):
                values = (current_element,) + tuple(float(x) for x in line.split())
                records.append(values)
            elif line.find("error") > -1:
                raise Error, "Pitch file %s has an error: %s" % (filename, line)

    field_types = ('i4',) + ('f8',)*len(field_names)
    field_names.insert(0,'element')
    return rec.fromrecords(records,dtype={'names':field_names,'formats':field_types})

def _reduce(x):
    if x.ndim==1: return x
    return x.mean(1)

def _fmt(dchar):
    if 'i' in dchar: return "%d"
    return "%6.4f"


# Variables:
# End:
