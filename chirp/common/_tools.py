# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Programming tools

consumer:        a decorator for consumer generators

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

# Variables:
# End:
