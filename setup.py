#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- mode: python -*-
from setuptools import setup, find_packages
from distutils.extension import Extension
try:
    from numpy.distutils.core import setup,Extension
except:
    pass
import sys

ext_libs = ['fftw3', 'lapack']
ext_incl = []

# --- Distutils setup and metadata --------------------------------------------

VERSION = '1.2.2'

cls_txt = """
Development Status :: 5 - Production/Stable
Intended Audience :: Science/Research
License :: OSI Approved :: GNU General Public License (GPL)
Programming Language :: Python
Topic :: Scientific/Engineering
Operating System :: Unix
Operating System :: POSIX :: Linux
Operating System :: MacOS :: MacOS X
Natural Language :: English
"""

short_desc = "Analyze and compare bioacoustic recordings"

long_desc = """Chirp provides a number of related tools for analyzing and comparing
bioacoustic recordings.  It can operate on recordings stored in
standard wave files, with the option of restricting analyses to
specific spectrotemporal regions of the recording.  Regions are
defined with polygons in the time-frequency domain.  The tools consist
of the following programs:

+ chirp :: inspect spectrograms of recordings and define regions
+ cpitch :: determine the pitch of recordings
+ ccompare :: compare libraries of recordings using pitch or spectrograms
"""

# --- customization for different platforms

if sys.platform=='darwin':
    ext_incl.append('/opt/local/include')
    app_options=dict(app=['chirp.py'],
                     options=dict(py2app=dict(plist=dict(
                                                CFBundleName = "chirp",
                                                CFBundleShortVersionString = VERSION,
                                                CFBundleGetInfoString = "Chirp %s" % VERSION,
                                                CFBundleExecutable = "chirp",
                                                CFBundleIdentifier = "org.meliza.chirp",
                                                CFBundleDocumentTypes=[dict(CFBundleTypeExtensions=["wav"],
                                                                            CFBundleTypeName="Wave Soundfile",
                                                                            CFBundleTypeRole="Viewer"),
                                                                       dict(CFBundleTypeExtensions=["ebl"],
                                                                            CFBundleTypeName="Extended Label File",
                                                                            CFBundleTypeRole="Editor"),
                                                                       dict(CFBundleTypeExtensions=["plg"],
                                                                            CFBundleTypeName="Pitch Logfile",
                                                                            CFBundleTypeRole="Viewer"),]
                                                ),
                                              frameworks=['/opt/local/lib/libgeos_c.dylib']
                                              )
                                  )

                )
elif sys.platform=='win32':
    app_options=dict(app=['chirp.py'])
else:
    app_options=dict()

_vitterbi = Extension('chirp.pitch._vitterbi', sources=['chirp/pitch/vitterbi.pyf', 'chirp/pitch/vitterbi.c'])
_dtw = Extension('chirp.compare._dtw', sources=['chirp/compare/dtw.pyf', 'chirp/compare/dtw.c'])

setup(
    name = 'chirp',
    version = VERSION,
    description = short_desc,
    long_description = long_desc,
    classifiers = [x for x in cls_txt.split("\n") if x],
    author = 'C Daniel Meliza',
    author_email = '"dan" at the domain "meliza.org"',
    maintainer = 'C Daniel Meliza',
    maintainer_email = '"dan" at the domain "meliza.org"',
    url = 'https://dmeliza.github.io/chirp',
    download_url = 'https://github.com/dmeliza/chirp',
    packages = find_packages(exclude=["*test*"]),
    ext_modules = [_vitterbi,_dtw],
    entry_points = {'console_scripts' : ['cpitch = chirp.pitch.tracker:cpitch',
                                         'cplotpitch = chirp.misc.plotpitch:main',
                                         'ccompare = chirp.compare.ccompare:main',
                                         'csplit = chirp.split.csplit:main',
                                         'cpitchstats = chirp.misc.pitchstats:main',],
                    'gui_scripts': ['chirp = chirp.gui.chirpgui:main'],},
    **app_options
)


# Variables:
# End:
