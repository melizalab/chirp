# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Provides a wrapper around ConfigParser using a default dictionary

Copyright (C) 2011 Dan Meliza <dan // meliza.org>
Created 2011-08-02
"""
import ConfigParser

class configoptions(object):
    """
    Wraps up ConfigParser with some useful type conversion and defaulting.
    Read in a config file, then use getdict to extract the data.
    """
    _configparser = ConfigParser.SafeConfigParser

    def __init__(self, configfile=None, **kwargs):
        """
        Initialize the parser, optionally reading in a config file and specifying defaults
        """
        self.config = self._configparser(kwargs)
        self.filename = ''
        self.read(configfile)

    def read(self, fname):
        """ Parse a configuration file """
        import os
        if fname is not None and os.path.exists(fname):
            self.config.read(fname)
            self.filename = fname

    def write(self, fname):
        """ Write stored configuration to file. Note that all comments will be stripped """
        self.config.write(open(fname,'wt'))

    def getdict(self, defaults, sections=('DEFAULT')):
        """
        For each element in defaults, look up the option in the config
        file and replace it with the one defined in the config file,
        if it exists.  Uses the type of the object stored in defaults
        to ensure that the returned dictionary has objects of the same
        type.

        sections: the sections to be checked for the option. Each
                  section is checked in turn, so later sections have priority.
        """
        from ast import literal_eval
        out = dict()
        for k,v in defaults.iteritems():
            for section in sections:
                if self.config.has_option(section,k):
                    cval = self.config.get(section, k)
                    t = type(v)
                    if t in (bool,tuple,list,dict,type(None),int,float):
                        try:
                            out[k] = literal_eval(cval)
                        except ValueError:
                            raise ValueError, "Invalid value for %s" % k
                    else:
                        out[k] = cval
            if k not in out:
                out[k] = v
        return out

    def update(self, section, **kwargs):
        """
        Update the stored configparser object with new values. This is
        usually done before saving the configuration to a file.  Uses
        repr() to generate a string representation of objects.
        """
        if not self.config.has_section(section):
            self.config.add_section(section)
        for k,v in kwargs.iteritems():
            if isinstance(v,basestring):
                self.config.set(section,k,v)
            else:
                self.config.set(section,k,repr(v))

    def get(self, section, option, default):
        """ Provide direct access to the ConfigParser object """
        return self.config.get(section, option, { option : default })

    def getboolean(self, section, option, default):
        """ Provide direct access to the ConfigParser object """
        if self.config.has_option(section, option):
            return self.config.getboolean(section, option)
        else:
            return default

class _configurable(object):
    """
    This mixin provides classes with the ability to configure
    themselves using a config file. Instructions:

    1. Define a class property dictionary called 'options' and
       populate with default values

    2. Define a class property 'config_section', a tuple of strings
       that indicate which sections from the config file the class
       should read (in order)

    2. Call configmixin.readconfig(), and the options dictionary will
       be updated with values from the config file.  This can be done
       in the __init__ method of the deriving class if the options are
       needed during initialization.
    """

    options = dict()
    config_sections = ('DEFAULT',)

    def readconfig(self, cfg):
        self.options = self.options.copy()
        if cfg is None: return
        if isinstance(cfg, basestring):
            cfg = configoptions(configfile=cfg)
        if isinstance(cfg, configoptions):
            self.options.update(cfg.getdict(self.options,self.config_sections))
        else:
            raise TypeError, "%s is not a configoptions object or a filename"

# Variables:
# End:
