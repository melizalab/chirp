# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
mixin class for plotting an overlay of pitch estimates in an axes

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-08-29
"""
from matplotlib.lines import Line2D
from ..common import plg, geom, postfilter
from ..pitch import tracker as ptracker

class PitchOverlayMixin(object):
    """
    Provides functions for overplotting pitch traces in an axes.  Use
    as a mixin class; the deriving class needs to have an 'axes'
    property that references a matplotlib Axes object and a draw()
    method that causes the axes to update.
    """
    def __init__(self, configfile=None):
        self.configfile = configfile
        self.filter = postfilter.pitchfilter(configfile=configfile)
        self.masker = geom.masker(configfile=configfile)
        self.trace_h = []

    def add_trace(self, t, f, **kwargs):
        """ Add a trace (typically pitch) to the plot. Removes previous plot if clear is True """
        plotargs = dict(color='w', linestyle='none', marker='o', alpha=0.2)
        plotargs.update(kwargs)
        h = Line2D(t, f, **plotargs)
        self.axes.add_line(h)
        self.trace_h.append(h)
        self.draw()

    def remove_trace(self):
        for h in self.trace_h: h.remove()
        self.trace_h = []
        self.draw()

    def plot_plg(self, plgfile):
        """
        Read data from a plg file and plot it.  This is a single trace
        because estimates are collapsed across chains.
        """
        pest = plg.read(plgfile)
        t = pest['time']
        if 'p.map' in pest.dtype.names:
            f = pest['p.map']
        else:
            f = pest['p.mmse']
        ind = self.filter(pest)
        self.remove_trace()
        self.add_trace(t[ind],f[ind])
        self.add_trace(t[~ind],f[~ind], color='k')

    def plot_calcd_pitch(self, signal, Fs, masks=None):
        """
        Calculate the pitch and plot it. Plots a separate trace for
        each chain.
        """
        from numpy import sqrt, maximum
        self.remove_trace()
        pt = ptracker.tracker(configfile=self.configfile, samplerate=Fs*1000)
        spec,tgrid,fgrid = pt.matched_spectrogram(signal,Fs)

        def _plot(t,var,est):
            ind = self.filter({'p.sd' : sqrt(maximum(0,var)) * Fs})
            for i in xrange(est.shape[1]):
                self.add_trace(t[ind[:,i]], est[ind[:,i],i])
                self.add_trace(t[~ind[:,i]], est[~ind[:,i],i], color='k')
        if masks is not None:
            for startcol, mspec, imask in self.masker.split(spec, masks, tgrid, fgrid):
                startframe, pitch_mmse, pitch_var, pitch_map, stats= pt.track(mspec, mask=imask)
                startframe += startcol
                t = tgrid[startframe:startframe+pitch_mmse.shape[0]]
                if pitch_map is not None:
                    _plot(t, pitch_var, pitch_map * Fs)
                else:
                    _plot(t, pitch_var, pitch_mmse * Fs)
        else:
            startframe, pitch_mmse, pitch_var, pitch_map, stats= pt.track(spec)
            t = tgrid[startframe:startframe+pitch_mmse.shape[0]]
            if pitch_map is not None:
                _plot(t, pitch_var, pitch_map * Fs)
            else:
                _plot(t, pitch_var, pitch_mmse * Fs)

# Variables:
# End:
