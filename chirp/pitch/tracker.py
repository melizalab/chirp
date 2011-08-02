# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
tracker    pitch-tracking from time-frequency reassignment spectrograms

Copyright (C) 2011 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2011-07-29
"""
import numpy as nx
import libtfr, template, particle

base_seed = 3653268L


class tracker(object):
    """
    This class is the front-end programming interface to the pitch
    tracker.  It will calculate pitch as a function of time from a
    variety of inputs, including spectrograms and oscillograms.
    Options are set at initialization time (see options for default
    values) but some can be altered for each analysis.

    spectrogram parameters
    =======================
    nfft    - number of frequency points in the spectrogram
    shift   - number of samples to shift for each analysis frame
    winsize - analysis window size; controls frequency resolution (< nfft)
    tfr_order - number of analysis tapers to use
    tfr_tm    - time support of tapers (leave as default, generally)
    tfr_flock - frequency locking (decreasing this reduces scatter in frequency dim)
    tfr_tlock - time locking (reduces scatter in time dim)

    pitch template parameters
    =========================
    pitch_range - range of possible pitch hypotheses (in relative freq. units)
    freq_range  - range of frequencies to analyze  (in relative freq. units)
    lobes       - number of harmonic lobes in template
    lobe_decay  - exponential decay factor for harmonic lobes
    neg_ampl    - size of negative lobes in template
    neg_width   - width of negative lobes in template

    particle filter parameters
    ==========================
    max_jump     - maximum amount pitch can change between frames
    particles    - number of particles
    pow_thresh   - exclude frames where total power is below this
    rwalk_scale  - in excluded frames, how much is pitch allowed to drift (std. dev)
    chains       - number of simulation chains to use
    btrace       - whether to use Vitterbi algorithm to backtrace best path
    """

    options = dict(nfft=512,
                   shift=30,
                   winsize=401,
                   tfr_order=5,
                   tfr_tm=6,
                   tfr_flock=0.01,
                   tfr_tlock=5,
                   pitch_range=(0.02,0.25),
                   freq_range=(0.01,0.4),
                   lobes=6,
                   lobe_decay=0.85,
                   neg_ampl=0.35,
                   neg_width=9,
                   max_jump=20,
                   particles=200,
                   pow_thresh=1e3,
                   rwalk_scale=2,
                   chains=3,
                   btrace=False,)

    def __init__(self, **kwargs):
        self.options.update(kwargs)
        self.template = template.harmonic(**self.options)

    def spec2pitch(self, spec, **kwargs):
        """
        Calculate the pitch from a spectrogram.  The spectrogram needs
        to be calculated on the same logarithmic frequency grid as the
        harmonic template.
        """
        options = self.options.copy()
        options.update(kwargs)

        like = self.template.xcorr(spec, **options)
        loglike = nx.log(nx.maximum(like, nx.exp(particle.smc.min_loglike)))
        trans = template.frame_xcorr(spec, **options)

        return loglike,trans

        # for chain in xrange(nchains):
        #     pfilt = particle.smc(loglike, proposal)
        #     pfilt.initialize(seed=base_seed + chain * 1000)
        #     pfilt.iterate_all(keep_history=True)

    def wave2pitch(self, signal, mask=None, **kwargs):
        """
        Calculate pitch from a signal waveform.  Uses the same
        frequency grid as the template.
        """
        options = self.options.copy()
        options.update(kwargs)

        spec = libtfr.tfr_spec(sig, options['nfft'], options['shift'], options['winsize'],
                               options['tfr_order'], options['tfr_tm'], options['tfr_flock'],
                               options['tfr_tlock'], fgrid=self.template.fgrid)
        # apply mask
        return self.spec2pitch(spec, **kwargs)


def pitch(spec, template, **kwargs):
    """
    Calculate the pitch from a spectrogram.  There are many options
    for this operation.

    spec:      spectrogram of signal, on a log frequency grid
    template:  harmonic template object
    """
    # initialize template
    # calculate spectrogram
    # apply mask

# Variables:
# End:
