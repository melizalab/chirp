# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
basic signal processing

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-08-30
"""
from .config import _configurable

class spectrogram(_configurable):
    """ Computes spectrograms of signals. """

    options = dict(spec_method = 'tfr',
                   window_len = 12.0,  # in ms
                   window_shift = 1.5,  # also in ms
                   tfr_order = 5,
                   tfr_tm = 6.0,
                   tfr_flock = 0.01,
                   tfr_tlock = 5,
                   mtm_nw = 2.5)

    def __init__(self, configfile=None):
        self.readconfig(configfile,('spectrogram',))

    def linspect(self, signal, Fs):
        """ Calculate the spectrogram on a linear power scale.  """
        import numpy as nx
        from .libtfr import stft, tfr_spec, tgrid
        Np = int(Fs * self.options['window_len'])
        shift = int(self.options['window_shift'] * Fs)
        nfft = int(2**nx.ceil(nx.log2(Np)))
        if self.options['spec_method']=='tfr':
            S = tfr_spec(signal, nfft, shift, Np,
                         K=self.options['tfr_order'], tm=self.options['tfr_tm'],
                         flock=self.options['tfr_flock'], tlock=self.options['tfr_tlock'])
        elif self.options['spec_method']=='mtm':
            S = mtm_spec(signal, nfft, shift, self.options['mtm_nw'])
        else:
            wfun = getattr(nx,self.options['spec_method'])
            w = wfun(Np)
            S = stft(signal, w, shift, nfft)
        t = tgrid(signal.size, Fs, shift, Np)
        extent = (0, t[-1], 0, Fs / 2)
        return S,extent

    def dbspect(self, signal, Fs, dBrange=96):
        from numpy import log10
        from libtfr import dynamic_range
        S,extent = self.linspect(signal, Fs)
        return log10(dynamic_range(S, dBrange)), extent


# Variables:
# End:
