#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
from setuptools import setup, find_packages
from distutils.extension import Extension
from numpy.distutils.core import setup,Extension
import sys, os
import os.path as op

# try:
#     from Cython.Distutils import build_ext
#     SUFFIX = '.pyx'
# except ImportError:
#     from distutils.command.build_ext import build_ext
#     SUFFIX = '.c'

# import numpy

# COMPILER_SETTINGS = {
#     'include_dirs' : [numpy.get_include()]
#     }

# --- Distutils setup and metadata --------------------------------------------

VERSION = '1.1.0'

cls_txt = \
"""
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

long_desc = \
"""
Chirp provides a number of related tools for analyzing and comparing
bioacoustic recordings.  It can operate on recordings stored in
standard wave files, with the option of restricting analyses to
specific spectrotemporal regions of the recording.  Regions are
defined with polygons in the time-frequency domain.  The tools consist
of the following programs:

+ chirp :: inspect spectrograms of recordings and define regions
+ cpitch :: determine the pitch of recordings
+ ccompare :: compare libraries of recordings using pitch or spectrograms
+ cfilter :: extract sounds corresponding to specific spectrotemporal regions
"""

_vitterbi = Extension('chirp.pitch._vitterbi',sources=['chirp/pitch/vitterbi.pyf','chirp/pitch/vitterbi.c'])
#pyxfiles = ['chirp/pitch/vitterbi']
#extensions = [Extension(m.replace('/','.'), [m+SUFFIX], **COMPILER_SETTINGS) for m in pyxfiles]

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
  url = 'https://dmeliza.github.com/chirp',
  download_url = 'https://github.com/dmeliza/chirp',
  packages= find_packages(exclude=["*test*"]),
  package_data = {'': ['*.pyx']},
  ext_modules = [_vitterbi],
  install_requires=['distribute', 'numpy>=1.3'],   # check this
  entry_points = {'console_scripts' : ['cpitch = chirp.pitch.tracker:cpitch',
                                       'cplotpitch = chirp.misc.plotpitch:main'],
                  'gui_scripts' : ['chirp = chirp.gui.chirpgui:main']},
)


# Variables:
# End:
