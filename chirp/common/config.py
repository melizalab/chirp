# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Provides a wrapper around ConfigParser using a default dictionary

Copyright (C) 2011 Dan Meliza <dmeliza@gmail.com>
Created 2011-08-02
"""

import ConfigParser

class configoptions(object):
    """
    Wraps up some type conversion involved in using ConfigParser.
    Instantiate with a dictionary of default values; the type of each
    is stored and used to back-convert files taken from the
    ConfigParser object.
    """
    _configparser = ConfigParser.SafeConfigParser

    def __init__(self, defaults, section):
        self.types = dict((k,type(v)) for k,v in defaults.iteritems())
        self.config = self._configparser(dict((k,str(v)) for k,v in defaults.iteritems()))
        self.section = section
        self.config.add_section(section)

    def read(self, fname):
        """ Parse a configuration file """
        self.config.read(fname)

    def items(self):
        """ Return items in the section (only the ones in the supplied defaults dict) """
        from ast import literal_eval
        out = dict()
        for k,v in self.config.items(self.section):
            t = self.types[k]
            if t in (bool,tuple,list,dict,type(None),int,float):
                try:
                    out[k] = literal_eval(v)
                except ValueError:
                    raise ValueError, "Invalid value for %s" % k
            else:
                out[k] = v
        return out

    def get(self, option, default):
        """ Provide direct access to the ConfigParser object """
        return self.config.get(self.section, option, { option : default })

    def getboolean(self, option, default):
        """ Provide direct access to the ConfigParser object """
        if self.config.has_option(self.section, option):
            return self.config.getboolean(self.section, option)
        else:
            return default



# Variables:
# End:
