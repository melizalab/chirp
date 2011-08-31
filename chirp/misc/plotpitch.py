# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Plot spectrograms of all the calls and associated pitch data in the
current directory.

Usage:
cplotpitch [-c config] <outfile>

Produces a PDF file with the spectrogram of each wav file in the
current directory, overlaid with pitch traces from each corresponding
plg file.

Copyright (C) 2010 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2010-03-15
"""

_scriptname = "cplotpitch"

import os
import numpy as nx
import matplotlib
from ..common.config import configoptions,_configurable
from ..common import postfilter

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
    if os.path.exists(basename + '.plg'):
        pitch = plg.read(basename + '.plg')
        if filterer is not None:
            ind = postfilter.ind_endpoints(filterer(pitch))
            pitch = pitch[ind[0]:ind[1]+1]
        t = pitch['time']
        if 'p.map' in pitch.dtype.names:
            p = pitch['p.map']
        else:
            p = pitch['p.mmse']
    else:
        t,p = None,None
    return signal,Fs/1000.,t,p

class plotter(_configurable):

    options = dict(colormap='Greys',
                   dynrange=60,
                   freq_range=(750.,10000.),
                   pitch_color='r')

    def __init__(self, configfile=None):
        self.readconfig(configfile, ('spectrogram','cplotpitch'))

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


def main(argv=None, cout=None):
    import sys, getopt, glob
    matplotlib.use('PDF')
    from matplotlib.backends.backend_pdf import PdfPages as multipdf
    from matplotlib.pyplot import close as close_figure
    from ..version import version
    from ..common.graphics import axgriditer
    from ..common.signal import spectrogram

    if argv is None:
        argv = sys.argv[1:]
    if cout is None:
        cout = sys.stdout

    config = configoptions()
    opts,args = getopt.getopt(sys.argv[1:], 'c:hv')
    for o,a in opts:
        if o == '-h':
            print __doc__
            return -1
        elif o == '-v':
            print "%s version %s" % (_scriptname, version)
            return -1
        elif o == '-c':
            config.read(a)
    if len(args) < 1:
        print __doc__
        sys.exit(-1)

    def gridfun(**kwargs):
        from matplotlib.pyplot import subplots
        return subplots(_nrows,_ncols,sharex=True,sharey=True, figsize=_figsize)

    def figfun(fig):
        ax = fig.axes[0]
        ax.set_xticklabels('')
        ax.set_yticklabels('')
        fig.subplots_adjust(left=0.05, right=0.95, wspace=0)
        pp.savefig(fig)
        close_figure(fig)

    # set up plotting
    pp = multipdf(args[0])
    axg = axgriditer(gridfun, figfun)
    spectrogram = spectrogram(configfile=config)
    plt = plotter(configfile=config)

    print >> cout, "* Program: cplotpitch"
    print >> cout, "** Version: %s" % version
    print >> cout, "* Plotting files in directory: %s" % os.getcwd()

    filt = postfilter.pitchfilter(configfile=config)
    print >> cout, filt.options_str()
    
    for fname in sorted(glob.iglob("*.wav")):
        basename = os.path.splitext(fname)[0]
        print "** %s" % basename
        ax = axg.next()

        signal,Fs,t,p = load_data(basename, filt)
        spec,extent = spectrogram.dbspect(signal,Fs)
        plt.plot_spectrogram(ax, spec, extent)
        if t is not None:
            plt.plot_trace(ax, t,p)

        ax.set_title(basename, ha='left', position=(0.0,1.0), fontsize=4)

    axg.close()
    pp.close()
    return 0

# Variables:
# End:
