# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
script for splitting wav files into component elements

Copyright (C) 2012 Dan Meliza <dmeliza@gmail.com>
Created 2012-04-23
"""
import ewave
from chirp.common.config import _configurable
from chirp.common import geom
from chirp.split import intervalsplit

_scriptname = "csplit"
_scriptdoc = """\

Usage: csplit [-c <config.cfg>] <signal.wav> [<mask.ebl>]

Extracts each element defined in <mask.ebl> from <signal.wav>,
outputting a new wave file for each element. If <mask.ebl> is not
supplied, tries to use <signal.ebl>. See documentation for
configuration file details."""


class splitter(_configurable):
    """ Splits a recording into intervals """

    options = dict(time_ramp=2,
                   boxmask=True,
                   merge_elements=True)
    config_sections = ('csplitter',)

    def __init__(self, configfile=None, **kwargs):
        self.readconfig(configfile)
        self.options.update(kwargs)

    def splitfile(self, wavfile, lblfile, cout=None):
        """
        Split the signal in <wavfile> into the elements in <lblfile>.

        yields (extracted signal, sampling_rate)
        """
        elems = geom.elementlist.read(lblfile)
        if self.options['merge_elements']:
            if self.options['boxmask']:
                elems = [elems.range]
            else:
                raise NotImplementedError("merging polygons not implemented")

        with ewave.wavfile(wavfile, 'r') as fp:
            signal, Fs = fp.read(), fp.sampling_rate / 1000.
            for i, elem in enumerate(elems):
                if geom.elementlist.element_type(elem) == 'interval':
                    print >> cout, "** Element %d, interval bounds (%.2f, %.2f)" % (i, elem[0], elem[1])
                    fun = intervalsplit.split
                elif self.options['boxmask']:
                    print >> cout, "** Element %d, polygon interval (%.2f, %.2f)" % (i, elem.bounds[0],
                                                                                     elem.bounds[2])
                    fun = intervalsplit.split
                else:
                    raise NotImplementedError("polygon extraction not implemented")
                yield i, fun(signal, elem, Fs, **self.options), Fs

    def options_str(self):
        out = """\
* Splitter parameters:
** Time smoothing = %(time_ramp).2f ms
** Boxmask polygons = %(boxmask)s
** Merge elements = %(merge_elements)s""" % self.options
        return out


def main(argv=None, cout=None, cerr=None, **kwargs):
    import os
    import sys
    from chirp.version import version
    if argv is None:
        argv = sys.argv[1:]
    if cout is None:
        cout = sys.stdout
    if cerr is None:
        cerr = sys.stderr

    import getopt
    from chirp.common.config import configoptions
    config = configoptions()

    opts, args = getopt.getopt(argv, 'hvc:')

    for o, a in opts:
        if o == '-h':
            print _scriptdoc
            return -1
        elif o == '-v':
            print " %s version %s" % (_scriptname, version)
            return -1
        elif o == '-c':
            config.read(a)
    if len(args) < 1:
        print _scriptdoc
        return -1

    wavfile = args[0]
    basename = os.path.splitext(wavfile)[0]
    if len(args) > 1:
        maskfile = args[1]
    else:
        maskfile = basename + ".ebl"

    print >> cout, "* Program: %s" % _scriptname
    print >> cout, "** Version: %s" % version
    print >> cout, "* Sound file: %s" % wavfile
    print >> cout, "* Mask file: %s" % maskfile

    splt = splitter(config)
    print >> cout, splt.options_str()

    for i, signal, Fs in splt.splitfile(wavfile, maskfile, cout=cout):
        outfile = "%s_e%03d.wav" % (os.path.split(basename)[1], i)
        print "** Writing extracted signal to %s" % outfile
        fp = ewave.wavfile(outfile, 'w', sampling_rate=Fs * 1000)
        fp.write(signal)

# Variables:
# End:
