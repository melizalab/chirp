# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
comparison method and storage plugins

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-08-30
"""
class _entrypoint(object):
    def __init__(self, name, cls):
        self.name = name
        self.cls = cls

    def load(self):
        return self.cls

class pluginset(object):

    def __init__(self, entry_point_name, defaults=None):
        self.entry_point_name = entry_point_name
        self.defaults = defaults or tuple()

    def iter_entry_points(self):
        from . import pitch_dtw, spcc, masked_spcc
        from pkg_resources import iter_entry_points as iep
        for ep in iep(self.entry_point_name):
            yield ep
        for name,cls in self.defaults:
            yield _entrypoint(name, cls)

    def names(self):
        """ Return list of available comparison methods """
        return [ep.name.lower() for ep in self.iter_entry_points()]

    def load(self, name):
        """ Load the entry point associated with a method, or ImportError if it doesn't exist """
        for ep in self.iter_entry_points():
            if ep.name.lower() == name.lower():
                return ep.load()
        raise ImportError, "No entry point for %s in group %s" % (name.lower(), entry_point_name)

    def make_scriptdoc(self):
        out = "Available storage formats:"
        for ep in self.iter_entry_points():
            cls = ep.load()
            out += "\n%15s    %s" % (cls.__name__, cls._descr)
        return out


from .pitch_dtw import pitch_dtw
from .spcc import spcc
from .masked_spcc import masked_spcc
methods = pluginset('chirp.compare.method',(('pitch_dtw',pitch_dtw),
                                            ('masked_spcc',masked_spcc),
                                            ('spcc',spcc)))

from .file_storage import file_storage
from .sqlite_storage import sqlite_storage
storage = pluginset('chirp.compare.storage',(('sqlite',sqlite_storage),
                                             ('file',file_storage)))

# Variables:
# End:
