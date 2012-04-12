# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
# Copyright (C) 2010 Daniel Meliza <dan // meliza.org>
# Created 2010-03-15
"""
Plot spectrograms and overlaid pitch traces of a collection of signals.

Usage:
cplotpitch [-c config] [-@] <files> <outfile>

Optional arguments:

-c       specify a chirp.cfg file with configurable options
-@       plot files from standard in (separated by newlines)
         instead of command line (useful for pipes from find, etc)
"""

_scriptname = "cplotpitch"

import os
import numpy as nx
import matplotlib
from ..common.config import configoptions,_configurable
from ..common import postfilter, _tools

figparams = { 'dpi' : 300 }
matplotlib.rc('font', size=10)
matplotlib.rc('xtick', labelsize=8)
matplotlib.rc('ytick', labelsize=8)
matplotlib.rc('axes',labelsize=10,titlesize=10)
matplotlib.rc('ytick.major', size=2)
matplotlib.rc('xtick.major', size=2)
matplotlib.rc('figure.subplot', top=0.95, hspace=0.35)

_figsize = (11,6)
_nrows = 6
_ncols = 3

def load_data(basename, filterer=None):
    """
    Load data from wav and plg files. If filterer is not None, filters
    pitch trace.
    """
    from ..common.audio import wavfile
    from ..common import plg
    fp = wavfile(basename + ".wav")
    signal,Fs = fp.read(), fp.sampling_rate
    if not os.path.exists(basename + '.plg'):
        return signal,Fs/1000.,None,None

    pitch = plg.read(basename + '.plg')
    if filterer is not None:
        ind = postfilter.ind_endpoints(filterer(pitch))
        if ind is None:
            return signal,Fs/1000.,None,None
        pitch = pitch[ind[0]:ind[1]+1]
        t = pitch['time']
    if 'p.map' in pitch.dtype.names:
        p = pitch['p.map']
    else:
        p = pitch['p.mmse']
    return signal,Fs/1000.,t,p

class plotter(_configurable):

    options = dict(colormap='Greys',
                   dynrange=60,
                   freq_range=(750.,10000.),
                   pitch_color='r')
    config_sections = ('spectrogram','cplotpitch')

    def __init__(self, configfile=None):
        self.readconfig(configfile)

    def plot_spectrogram(self, ax, spec, extent):
        from matplotlib import cm
        cmap = getattr(cm, self.options['colormap'])
        img = ax.imshow(spec, extent=extent, cmap=cmap, origin='lower')
        Smax = spec.max()
        img.set_clim((Smax - self.options['dynrange'] / 10, Smax))
        ax.set_ylim(tuple(f/1000. for f in self.options['freq_range']))
        return img

    def plot_trace(self, ax, t, p):
        ax.hold(True)
        p = ax.plot(t,p,self.options['pitch_color'])
        ax.hold(False)
        return p

@_tools.consumer
def multiplotter(outfile, config, cout=None, show_pitch=True):
    """
    A coroutine for plotting a bunch of motifs on the same page. A
    useful entry point for scripts that want to do something similar
    to cplotpitch, but with control over which motifs get plotted.
    """
    matplotlib.use('PDF')
    from matplotlib.backends.backend_pdf import PdfPages as multipdf
    from matplotlib.pyplot import close as close_figure
    from ..version import version
    from ..common.graphics import axgriditer
    from ..common.signal import spectrogram

    def gridfun(**kwargs):
        from matplotlib.pyplot import subplots
        return subplots(_nrows,_ncols,sharex=True,sharey=True, figsize=_figsize)

    def figfun(fig):
        maxx = max(ax.dataLim.x1 for ax in fig.axes)
        ax = fig.axes[0]
        ax.set_xticklabels('')
        ax.set_yticklabels('')
        ax.set_xlim(0,maxx)
        for ax in fig.axes:
            ax.yaxis.set_ticks_position('left')
            ax.xaxis.set_ticks_position('bottom')
        fig.subplots_adjust(left=0.05, right=0.95, wspace=0)
        pp.savefig(fig)
        close_figure(fig)

    # set up plotting
    pp = multipdf(outfile)
    axg = axgriditer(gridfun, figfun)
    spectrogram = spectrogram(configfile=config)
    plt = plotter(configfile=config)

    filt = postfilter.pitchfilter(configfile=config)
    print >> cout, filt.options_str()

    print >> cout, "* Plotting signals:"
    try:
        # first call to yield won't return anything
        ax = None
        while 1:
            # receives filename from caller and returns last axes
            basename = yield ax
            ax = axg.next()

            try:
                signal,Fs,t,p = load_data(basename, filt)
                print >> cout, "** %s" % basename
            except Exception, e:
                print >> cout, "** %s: error loading data (%s)" % (basename, e)
                continue
            spec,extent = spectrogram.dbspect(signal,Fs)
            plt.plot_spectrogram(ax, spec, extent)
            if show_pitch and t is not None:
                plt.plot_trace(ax, t,p)

        # loop will break when caller sends stop()
    finally:
        axg.close()
        pp.close()


def main(argv=None, cout=None):
    import sys, getopt, glob
    from ..version import version

    if argv is None:
        argv = sys.argv[1:]
    if cout is None:
        cout = sys.stdout

    signals = None
    config = configoptions()
    opts,args = getopt.getopt(sys.argv[1:], 'c:hv@')
    for o,a in opts:
        if o == '-h':
            print __doc__
            return -1
        elif o == '-v':
            print "%s version %s" % (_scriptname, version)
            return -1
        elif o == '-c':
            config.read(a)
        elif o == '-@':
            signals = (f.strip() for f in sys.stdin.readlines())

    if len(args) < 1:
        print __doc__
        sys.exit(-1)
    if not signals:
        if len(args) < 2:
            print __doc__
            sys.exit(-1)
        signals = args[:-1]

    print >> cout, "* Program: cplotpitch"
    print >> cout, "** Version: %s" % version
    print >> cout, "** Output file: %s" % args[-1]

    plotter = multiplotter(args[-1], config, cout)
    for fname in signals:
        basename = os.path.splitext(fname)[0]
        ax = plotter.send(basename)
        ax.set_title(basename, ha='left', position=(0.0,1.0), fontsize=4)

    return 0

# Variables:
# End:
