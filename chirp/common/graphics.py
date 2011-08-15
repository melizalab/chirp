# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Plotting utilities, including spectrograms.

Copyright (C) 2011 Dan Meliza <dmeliza@gmail.com>
Created 2011-08-10
"""

from .config import _configurable

def axgriditer(gridfun=None, figfun=None, **figparams):
    """
    Generates axes for multiple gridded plots.  Initial call
    to generator specifies plot grid (default 1x1).  Yields axes
    on the grid; when the grid is full, opens a new figure and starts
    filling that.

    Arguments:
    gridfun - function to open figure and specify subplots. Needs to to return
              fig, axes. Default function creates one subplot in a figure.

    figfun - called when the figure is full or the generator is
             closed.  Can be used for final figure cleanup or to save
             the figure.  Can be callable, in which case the
             signature is figfun(fig); or it can be a generator, in
             which case its send() method is called.

    additional arguments are passed to the figure() function
    """
    if gridfun is None:
        from matplotlib.pyplot import subplots
        gridfun = lambda : subplots(1,1)

    fig,axg = gridfun(**figparams)
    try:
        while 1:
            for ax in axg.flat:
                yield ax
            if callable(figfun): figfun(fig)
            elif hasattr(figfun,'send'): figfun.send(fig)
            fig, axg = gridfun(**figparams)
    except:
        # cleanup and re-throw exception
        if callable(figfun): figfun(fig)
        elif hasattr(figfun,'send'): figfun.send(fig)
        raise

class spectrogram(_configurable):
    """ Computes spectrograms of signals. """

    options = dict(spec_method = 'tfr',
                   window_len = 12.0,  # in ms
                   window_shift = 1.5,  # also in ms
                   tfr_order = 5,
                   tfr_tm = 6.0,
                   tfr_flock = 0.01,
                   tfr_tlock = 5,)

    def __init__(self, configfile=None):
        self.readconfig(configfile,('spectrogram',))

    def linspect(self, signal, Fs):
        """ Calculate the spectrogram on a linear power scale """
        import numpy as nx
        from libtfr import stft, tfr_spec
        Np = int(Fs * self.options['window_len'])
        shift = int(self.options['window_shift'] * Fs)
        nfft = int(2**nx.ceil(nx.log2(Np)))
        if self.options['spec_method']=='hanning':
            w = nx.hanning(Np)
            S = stft(signal, w, shift, nfft)
        elif self.options['spec_method']=='tfr':
            S = tfr_spec(signal, nfft, shift, Np,
                         K=self.options['tfr_order'], tm=self.options['tfr_tm'],
                         flock=self.options['tfr_flock'], tlock=self.options['tfr_tlock'])
        extent = (0, signal.size / Fs, 0, Fs / 2)
        return S,extent

    def dbspect(self, signal, Fs, dBrange=96):
        from numpy import log10
        from libtfr import dynamic_range
        S,extent = self.linspect(signal, Fs)
        return log10(dynamic_range(S, dBrange)), extent


# Variables:
# End:
