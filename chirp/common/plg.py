# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Read plg files, which store the output of the pitch tracker.

Copyright (C) 2011 Dan Meliza <dmeliza@gmail.com>
Created 2011-08-06
"""

import re
_el_rx = re.compile(r"\*+ Pitch for element ([0-9]+)")

def read(filename):
    """
    Parse a ptracker log file (plg) for the pitch trace.  Returns a
    recarray with the time, mean, variance, and argmax of the
    posterior pitch distribution (and any other columns output by
    ptracker) for each element defined in the plg file. Element number
    is indicated by a separate column.
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
            elif line[0] not in ('*','+'):
                values = (current_element,) + tuple(float(x) for x in line.split())
                records.append(values)

    field_types = ('i4',) + ('f8',)*len(field_names)
    field_names.insert(0,'element')
    return rec.fromrecords(records,dtype={'names':field_names,'formats':field_types})



# Variables:
# End:
