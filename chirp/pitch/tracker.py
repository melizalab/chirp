# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
tracker    pitch-tracking from time-frequency reassignment spectrograms

Copyright (C) 2011 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2011-07-29
"""
import numpy as nx
import libtfr, template, particle, vitterbi

base_seed = 3653268


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
    min_loglike  - floor for log likelihood (not a very important parameter)
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
                   btrace=False,
                   min_loglike=-100)

    def __init__(self, **kwargs):
        self.options = self.options.copy()
        self.options.update(kwargs)
        self.template = template.harmonic(**self.options)

    def spec2pitch(self, spec, **kwargs):
        """
        Calculate the pitch from a spectrogram.  The spectrogram needs
        to be calculated on the same logarithmic frequency grid as the
        harmonic template.

        Options:
        chains       number of simulation chains
        rwalk_scale  random walk in frames where power is low
        btrace       do backwards filter to find MAP estimate?
        """
        options = self.options.copy()
        options.update(kwargs)
        btrace = options.get('btrace',False)
        chains = options.get('chains',1)

        spec,starttime = specprocess(spec, **kwargs)
        like = self.template.xcorr(spec, **options)
        proposal = template.frame_xcorr(spec, **options)

        pitch_mmse = nx.zeros((spec.shape[1],chains))
        if btrace:
            pitch_map = nx.zeros((spec.shape[1],chains))
        else:
            pitch_map = None
        for chain in xrange(chains):
            # may be some use in multithreading here
            pfilt = particle.smc(like, proposal, **options)
            pfilt.initialize(nparticles=options['particles'], seed=base_seed + chain * 1000)
            pitch_mmse[0,chain] = pfilt.integrate(func=lambda x : self.template.pgrid[x])
            pitch_dist[:,0] = pfilt.density()

            for f,p,w in pfilt.iterate(rwalk_scale=options['rwalk_scale'], keep_history=btrace):
                pitch_mmse[f,chain] = pfilt.integrate(func=lambda x: self.template.pgrid[x])

            if btrace:
                particles = nx.column_stack(pfilt.particle_history)
                pitch_map = vitterbi.filter(particles, pfilt.loglike, proposal, **kwargs)

        return starttime, pitch_mmse, pitch_map

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


def specprocess(spec, pow_thresh=1e3, **kwargs):
    """
    Preprocess a spectrogram before running it through the pitch
    detector.  Currently this consists of eliminating frames at the
    beginning and end where the total power is less than pow_thresh.
    Although inputs should be segmented carefully, this helps to deal
    with cases where the mask may be so small at the beginning or end
    that the spectrogram is essentially masked out.

    Returns reduced spectrogram, index of first column kept
    """
    specpow = nx.sqrt((spec**2).sum(0))
    ind = nx.nonzero(specpow > pow_thresh)[0]
    if ind.size<2:
        raise ValueError, "Spectrogram is entirely below power threshold"
    return spec[:,ind[0]:ind[-1]], ind[0]


# Variables:
# End:
