# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
Programming tools

consumer:       a decorator for consumer generators
alnumkey:       yield the alphabetical and numeric components of a string

Copyright (C) 2012 Dan Meliza <dmeliza@gmail.com>
Created 2012-01-31
"""

def consumer(func):
    def wrapper(*args,**kw):
        gen = func(*args, **kw)
        gen.next()
        return gen
    wrapper.__name__ = func.__name__
    wrapper.__dict__ = func.__dict__
    wrapper.__doc__  = func.__doc__
    return wrapper

def alnumkey(s):
    """
    Turn a string into component string and number chunks.
    "z23a" -> ("z", 23, "a")

    Use as a key in sorting filenames naturally
    """
    import re
    convert = lambda text: int(text) if text.isdigit() else text 
    return [convert(c) for c in re.split('([0-9]+)', s)]


# Variables:
# End:
