# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Classes deriving from TSViewer.TSDataHandler and TSViewer.TSViewer
with specializations for plotting spectrograms.

Copyright (C) 2009 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2009-07-16
"""

from __future__ import division
import wx
from .wxcommon import *
from . import TSViewer

import numpy as nx
import libtfr
from matplotlib import cm

class SpecHandler(TSViewer.TSDataHandler):
    """
    Data handler subclass for spectrograms. The plot_data() method
    will compute the spectrogram of a signal.
    """

    # default parameters:
    nfft = 1024
    _method = 'tfr'
    _window_len = 12.0  # in ms
    _shift = 1.5  # this should really be adjusted dynamically but requires some cache mojo
    _colormap = cm.Greys
    _fpass = (0, 10)  # kHz frequency
    _dynrange = 60

    _tfr_params = dict(K=5, flock=0.002, tlock=2)

    def __init__(self, axes):
        super(SpecHandler, self).__init__(axes)
        self.signal = None
        self.image = None
        self.Fs = None

    def get_fpass(self):
        return self._fpass
    def set_fpass(self, value):
        if not len(value)==2: raise ValueError, "Frequency range must have length of 2"
        if value==self._fpass: return
        self._fpass = value
        if self.image:
            self.axes.set_ylim(value)
            self.draw()
    fpass = property(get_fpass, set_fpass)

    def get_colormap(self):
        return self._colormap
    def set_colormap(self, value):
        if value==self._colormap: return
        self._colormap = value
        if self.image:
            self.image.set_cmap(value)
            self.draw()
    colormap = property(get_colormap, set_colormap)

    def get_method(self):
        return self._method
    def set_method(self, value):
        self._method = value
        if self.signal is not None: self.plot_data(self.signal, self.Fs)
    method = property(get_method, set_method)

    def get_shift(self):
        return self._shift
    def set_shift(self, value):
        if value==self._shift: return
        self._shift = value
        if self.signal is not None: self.plot_data(self.signal, self.Fs)
    shift = property(get_shift, set_shift)

    def get_window_len(self):
        return self._window_len
    def set_window_len(self, value):
        if value==self._window_len: return
        self._window_len = value
        if self.signal is not None: self.plot_data(self.signal, self.Fs)
    window_len = property(get_window_len, set_window_len)

    def get_dynrange(self):
        return self._dynrange
    def set_dynrange(self, value):
        if value==self._dynrange: return
        self._dynrange = value
        if self.image:
            sigmax = self.image.get_array().max()
            self.image.set_clim((sigmax - value/10, sigmax))
            self.draw()
    dynrange = property(get_dynrange, set_dynrange)

    def plot_data(self, signal, Fs=20):
        """ Compute spectrogram and plot it to the current axes """
        Np = int(Fs * self.window_len)
        shift = int(self.shift * Fs)
        self.nfft = int(2**nx.ceil(nx.log2(Np)))
        self.signal = signal  # store signal for changes in parameters
        self.Fs = float(Fs)
        print "Computing %d point spectrogram: %d frames, %3.2f/ms, %d window, %d shift" % \
              (self.nfft, signal.size, self.Fs, Np, shift)
        if self._method=='hanning':
            w = nx.hanning(Np)
            S = libtfr.stft(signal, w, shift, self.nfft)
        elif self._method=='tfr':
            S = libtfr.tfr_spec(signal, self.nfft, shift, Np,
                                **self._tfr_params)
        S = nx.log10(dynamic_range(S, 96))
        extent = (0, signal.size / self.Fs, 0, self.Fs / 2)
        if self.image is None:
            self.image = self.axes.imshow(S, extent=extent, cmap=self.colormap, origin='lower')
        else:
            self.image.set_data(S)

        Smax = S.max()
        self.image.set_clim((Smax - self.dynrange / 10, Smax))
        self.axes.set_ylim(self.fpass)
        self.draw()


class SpecViewer(TSViewer.TSViewer):
    """ Combines a TSViewer panel with some spectrogram controls """
    def __init__(self, parent, id, figure=None):
        super(SpecViewer, self).__init__(parent, id, figure, handler=SpecHandler)


def dynamic_range(S, dB):
    """
    Compress a spectrogram's dynamic range by thresholding all values dB less than
    the peak of S (linear scale).
    """
    smax = S.max()
    thresh = 10**(nx.log10(smax) - dB/10.)
    return nx.where(S >= thresh, S, thresh)


# Variables:
# End:
