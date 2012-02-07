# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-

version = "1.1.1"

def lib_versions():
    import sys
    from libtfr import __version__ as tfrver
    from shapely.geos import geos_capi_version
    from numpy import __version__ as npyver
    return dict(chirp = version,
                python = sys.version.split()[0],
                numpy = npyver,
                libtfr = tfrver,
                geos = "%d.%d.%d" % geos_capi_version)

__doc__ = """\
This is chirp, a program for bioacoustic analysis.

Library versions:
chirp:        %(chirp)s
python:       %(python)s
numpy:        %(numpy)s
libtfr:       %(libtfr)s
geos/shapely: %(geos)s

Copyright (C) 2011-2012 Dan Meliza <dan // meliza.org>
Project site: http://github.com/dmeliza/chirp
""" % lib_versions()


# Variables:
# End:
