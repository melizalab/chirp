# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
compare signals using spectrographic cross-correlation.

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-08-30
"""
from ..common.config import _configurable
from .base_comparison import base_comparison

class spcc(base_comparison, _configurable):
    """
    Compute pairwise distances between motifs using spectrographic
    cross-correlation (SPCC). Configurable options:

    nfreq:       the number of frequency bands to compare
    freq_range:  the range of frequencies to compare (in Hz)
    shift:       the number of time points to shift between analysis window
    window:      the windowing function to use
    biased_norm: use a biased (but more robust) normalization
    """
    file_extension = ".wav"
    options = dict(nfreq=100,
                   shift=50,
                   freq_range=(750.0,10000.0),
                   window='hanning',
                   biased_norm=True
                   )

    def __init__(self, configfile=None, **kwargs):
        self.readconfig(configfile, ('spectrogram','spcc',))
        self.options.update(kwargs)

    def load_signal(self, locator, dtype='d'):
        """
        Loads the signal and computes the linear spectrogram.

        dtype: the data type to store the output in. Default is
               single-precision to reduce storage requirements.
        """
        from ..common.audio import wavfile
        fp = wavfile(locator)
        signal = fp.read()
        Fs = fp.sampling_rate
        spec = linspect(signal, Fs, self.options['freq_range'],
                        self.options['nfreq'], self.options['shift'])[0]
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
** Window shift = %(shift)d
** Window type = %(window)s""" % self.options
        return out

def linspect(signal, Fs, frange, N, shift):
    """ Compute STFT of signal and time/frequency grid """
    from numpy import hanning, linspace
    from libtfr import stft, fgrid, tgrid
    # have to derive NFFT from N
    df = 1. * (frange[1]-frange[0])/N
    nfft = int(1.0 * Fs / df)
    S = stft(signal, hanning(nfft), shift)
    F,ind = fgrid(Fs,nfft,frange)
    T = tgrid(signal.size, Fs, shift)
    return S[ind,:], F, T

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
    #   L2 norm (biased_norm) is simpler, but can bias CC downward if
    #   there are strong signals outside the match area This can be a
    #   good penalty for differences in duration.
    #   With running sum, it's important to use signals that have little zero-padding.
    d1 = norm(ref)
    if biased_norm:
        d2 = norm(tgt)
    else:
        d2 = sqrt(convolve((tgt**2).sum(0), ones(rframes), 'valid'))
    return num / d1 / d2


# Variables:
# End:
