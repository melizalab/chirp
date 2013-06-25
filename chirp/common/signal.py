# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
basic signal processing

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-08-30
"""
from chirp.common.config import _configurable


class Error(Exception):
    pass


class spectrogram(_configurable):
    """ Computes spectrograms of signals. """

    options = dict(spec_method='tfr',
                   window_len=12.0,  # in ms
                   window_shift=0.7,  # also in ms
                   tfr_order=5,
                   tfr_tm=6.0,
                   tfr_flock=0.01,
                   tfr_tlock=5,
                   mtm_nw=2.5)
    config_sections = ('spectrogram',)

    def __init__(self, configfile=None, **kwargs):
        self.readconfig(configfile)
        self.options.update(kwargs)

    def linspect(self, signal, Fs, nfft=None):
        """ Calculate the spectrogram on a linear power scale.  """
        import numpy as nx
        from libtfr import stft, tfr_spec, tgrid
        shift = int(self.options['window_shift'] * Fs)
        if not nfft:
            Np = int(Fs * self.options['window_len'])
            nfft = int(2 ** nx.ceil(nx.log2(Np)))
        else:
            Np = nfft
        if self.options['spec_method'] == 'tfr':
            S = tfr_spec(signal, nfft, shift, Np,
                         K=self.options['tfr_order'], tm=self.options['tfr_tm'],
                         flock=self.options['tfr_flock'], tlock=self.options['tfr_tlock'])
        else:
            try:
                wfun = getattr(nx, self.options['spec_method'])
                w = wfun(Np)
            except Exception, e:
                raise Error("invalid window function {}: {}".format(self.options['spec_method'], e))
            S = stft(signal, w, shift, nfft)
        t = tgrid(S, Fs, shift)   # [:S.shape[1]]
        extent = (0, t[-1], 0, Fs / 2)
        return S, extent

    def dbspect(self, signal, Fs, dBrange=96, *args, **kwargs):
        from numpy import log10
        from libtfr import dynamic_range
        S, extent = self.linspect(signal, Fs, *args, **kwargs)
        return log10(dynamic_range(S, dBrange)), extent


# Variables:
# End:
