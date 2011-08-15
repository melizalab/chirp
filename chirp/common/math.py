# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
math functions

Copyright (C) 2011 Dan Meliza <dmeliza@gmail.com>
Created 2011-08-10
"""

from numpy import frompyfunc

def _decibels(x, mindB=0.0):
    """ Convert from linear scale to decibels safely """
    from numpy import log10, power
    thresh = power(10.0, 0.1 * mindB)
    return log10(x)*10.0 if x > thresh else mindB

decibels = frompyfunc(_decibels, 1, 1)


# Variables:
# End:
