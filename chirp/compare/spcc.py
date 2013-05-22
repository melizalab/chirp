# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
compare signals using spectrographic cross-correlation.

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-08-30
"""
import os
from ..common.config import _configurable
from .base_comparison import base_comparison

class spcc(base_comparison, _configurable):
    """
    Compute pairwise distances between motifs using spectrographic
    cross-correlation (SPCC). Configurable options:

    nfreq:         the number of frequency bands to compare
    freq_range:    the range of frequencies to compare (in Hz)
    shift:         the number of time points to shift between analysis window
    window:        the windowing function to use
    subtract_mean: subtract mean of log spectrograms before doing CC
    biased_norm:   use a biased (but more robust) normalization
    """
    _descr = "spectrographic crosscorrelation (requires wav; ebl optional)"
    file_extension = ".wav"
    options = dict(spec_method='hanning',
                   nfreq=100,
                   window_shift=1.5, # this is in ms
                   freq_range=(750.0,10000.0),
                   powscale='linear',
                   mask='box',
                   subtract_mean=True,
                   biased_norm=True
                   )
    config_sections = ('spectrogram','spcc',)

    def __init__(self, configfile=None, **kwargs):
        self.readconfig(configfile)
        self.options.update(kwargs)

    def load_signal(self, locator, dtype='d'):
        """
        Loads the signal and computes the spectrogram.

        dtype: the data type to store the output in. Use
               single-precision floats if needed to reduce storage
               requirements.
        """
        from ..common.audio import wavfile
        from ..common.signal import spectrogram
        from ..common.libtfr import fgrid, dynamic_range
        from ..common.geom import elementlist, masker
        from numpy import linspace, log10

        fp = wavfile(locator)
        signal = fp.read()
        Fs = fp.sampling_rate

        speccr = spectrogram(**self.options)
        # adjust window size to get correct number of frequency bands
        df = 1. * (self.options['freq_range'][1]-self.options['freq_range'][0])/self.options['nfreq']
        nfft = int(Fs / df)

        spec,extent = speccr.linspect(signal, Fs / 1000, nfft=nfft)
        F,ind = fgrid(Fs,nfft,self.options['freq_range']) # in Hz
        spec = spec[ind,:]
        T = linspace(extent[0],extent[1],spec.shape[1]) # in ms

        # first convert the spectrogram to its final scale
        if self.options['powscale'].startswith('log'):
            # TODO calculate dynamic range of the signal for non 16 bit PCM?
            spec = log10(dynamic_range(spec, 96))
            # recenter spectrogram
            if self.options['subtract_mean']:
                spec -= spec.mean()

        if self.options['mask'] != 'none':
            eblfile = os.path.splitext(locator)[0] + elementlist.default_extension
            if os.path.exists(eblfile):
                mask = elementlist.read(eblfile)
                spec = masker(boxmask=self.options['mask']=='box').cut(spec,mask,T,F / 1000.)

        return spec.astype(dtype)

    def compare(self, ref, tgt):
        cc = spectcc(ref, tgt, self.options['biased_norm'])
        return (cc.sum(0).max(),)

    @property
    def compare_stat_fields(self):
        """ Return a tuple of the names for the statistics returned by compare() """
        return ("spcc",)

    def options_str(self):
        out = """\
* SPCC parameters:
** Frequency bands = %(nfreq)d
** Frequency range %(freq_range)s
** Window shift = %(window_shift).2f
** Spectrogram method = %(spec_method)s
** Spectrogram power scale = %(powscale)s
** Use biased norm = %(biased_norm)s
** Spectrogram masking = %(mask)s""" % self.options
        return out

def spectcc(ref, tgt, biased_norm=True):
    """
    Compute cross-correlation between two spectrograms.  This is
    essentially the mean of the cross-correlations for each of the
    frequency bands in the spectrograms.

    ref, tgt:  spectrograms of signals, nfreq x nframe

    returns the 2D cross-correlation, calculate sum of columns to get CC for each lag
    """
    from numpy import conj,sqrt,convolve,ones
    from numpy.fft import fft,ifft
    from numpy.linalg import norm

    assert ref.ndim == tgt.ndim
    if ref.ndim == 1:
        ref.shape = (1,ref.size)
        tgt.shape = (1,tgt.size)

    rfreq,rframes = ref.shape
    tfreq,tframes = tgt.shape
    assert tfreq==rfreq, "Spectrograms must have same number of frequency bands"
    # switch ref and tgt so that ref is always shorter
    if tframes < rframes:
        tframes,rframes = rframes,tframes
        tgt,ref = ref,tgt

    sz = rframes+tframes-1

    # numerator
    X   = conj(fft(ref,sz,axis=1))
    X  *= fft(tgt,sz,axis=1)
    num = ifft(X).real
    # restrict to valid frames (complete overlap)
    ind = abs(rframes-tframes)+1
    num = num[:,:ind]

    # denominator
    # * for the shorter signal, it's just the L2 norm
    # * for the longer signal, can use L2 norm, or a moving sum
    d1 = norm(ref)
    if biased_norm:
        d2 = norm(tgt)
    else:
        d2 = sqrt(convolve((tgt**2).sum(0), ones(rframes), 'valid'))
    return num / d1 / d2


# Variables:
# End:
