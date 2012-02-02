# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Classes deriving from TSViewer.TSDataHandler and TSViewer.TSViewer
with specializations for plotting spectrograms.

Copyright (C) 2009 Daniel Meliza <dan // meliza.org>
Created 2009-07-16
"""
from __future__ import division
import wx
from . import TSViewer

import numpy as nx
from ..common.signal import spectrogram
from ..common.config import _configurable
from matplotlib import cm

class SpecHandler(TSViewer.TSDataHandler, _configurable):
    """
    Data handler subclass for spectrograms. The plot_data() method
    will compute the spectrogram of a signal.
    """
    options = dict(colormap = 'Greys',
                   freq_range = (0.0, 10000.0),  # Hz frequency, gets displayed in kHz
                   dynrange = 60)

    def __init__(self, configfile=None):
        self.spectrogram = spectrogram(configfile=configfile)
        self.readconfig(configfile,('spectrogram',))
        self.signal = None
        self.image = None
        self.Fs = None

    def set_axes(self, axes):
        """ After getting axes, set the default ylim """
        super(SpecHandler, self).set_axes(axes)
        f1,f2 = (f/1000. for f in self.options['freq_range'])
        self.axes.set_ylim((f1,f2))

    def get_colormap(self, obj=False):
        if obj:
            return getattr(cm,self.options['colormap'],"Greys")
        else:
            return self.options['colormap']
    def set_colormap(self, value):
        if value==self.options['colormap']: return
        self.options['colormap'] = value
        if self.image:
            self.image.set_cmap(self.get_colormap(obj=True))
            self.draw()
    colormap = property(get_colormap, set_colormap)

    def get_method(self):
        return self.spectrogram.options['spec_method']
    def set_method(self, value):
        self.spectrogram.options['spec_method'] = value
        if self.signal is not None: self.plot_data(self.signal, self.Fs)
    method = property(get_method, set_method)

    def get_shift(self):
        return self.spectrogram.options['window_shift']
    def set_shift(self, value):
        if value==self.spectrogram.options['window_shift']: return
        self.spectrogram.options['window_shift'] = value
        if self.signal is not None: self.plot_data(self.signal, self.Fs)
    shift = property(get_shift, set_shift)

    def get_window_len(self):
        return self.spectrogram.options['window_len']
    def set_window_len(self, value):
        if value==self.spectrogram.options['window_len']: return
        self.spectrogram.options['window_len'] = value
        if self.signal is not None: self.plot_data(self.signal, self.Fs)
    window_len = property(get_window_len, set_window_len)

    def get_dynrange(self):
        return self.options['dynrange']
    def set_dynrange(self, value):
        if value==self.options['dynrange']: return
        self.options['dynrange'] = value
        if self.image:
            sigmax = self.image.get_array().max()
            self.image.set_clim((sigmax - value/10, sigmax))
            self.draw()
    dynrange = property(get_dynrange, set_dynrange)

    def plot_data(self, signal, Fs=20):
        """ Compute spectrogram and plot it to the current axes """
        self.signal = signal  # store signal for changes in parameters
        self.Fs = float(Fs)
        S,extent = self.spectrogram.dbspect(signal, Fs)
        if self.image is None:
            # store current ylim
            y1,y2 = self.ylim
            self.image = self.axes.imshow(S, extent=extent, cmap=self.get_colormap(obj=True), origin='lower')
            self.ylim = y1,y2
        else:
            self.image.set_data(S)

        Smax = S.max()
        self.image.set_clim((Smax - self.dynrange / 10, Smax))
        self.draw()


class SpecViewer(TSViewer.TSViewer):
    """ Combines a TSViewer panel with some spectrogram controls """
    def __init__(self, parent, id, figure=None, configfile=None):
        handler = SpecHandler(configfile=configfile)
        super(SpecViewer, self).__init__(parent, id, figure, handler=handler, configfile=configfile)

def test(soundfile):

    from ..common.audio import wavfile
    fp = wavfile(soundfile)
    signal,Fs = fp.read(), fp.sampling_rate

    class SpecViewFrame(wx.Frame):
        def __init__(self, parent=None):
            super(SpecViewFrame, self).__init__(parent, title="TSViewer Test App", size=(1000,300),
                style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)
            self.figpanel = SpecViewer(self, -1)
            self.figpanel.plot_data(signal, Fs)

    app = wx.PySimpleApp()
    app.frame = SpecViewFrame()
    app.frame.Show()
    app.MainLoop()


# Variables:
# End:
