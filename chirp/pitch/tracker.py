# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
pitch-tracking from time-frequency reassignment spectrograms

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
    variety of inputs, including spectrograms and signal waveforms.
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
                   tfr_tm=6.0,
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

    def track(self, signal, cout=None, **kwargs):
        """
        Calculate the pitch from a spectrogram or signal waveform.  If
        the input is a spectrogram, it needs to be calculated on the
        same logarithmic frequency grid as the harmonic template.
        Waveforms are converted to spectrograms using the stored
        parameters for the template.

        Options:
        particles    number of particles in filter
        chains       number of simulation chains
        rwalk_scale  random walk in frames where power is low
        btrace       do backwards filter to find MAP estimate?
        cout         output some status info to this stream if not None
        """
        options = self.options.copy()
        options.update(kwargs)
        btrace = options.get('btrace',False)
        chains = options.get('chains',1)

        if signal.ndim==1:
            spec = self.matched_spectrogram(signal)
        elif signal.ndim==2:
            spec = signal
        else:
            raise ValueError, "Can't process arrays with more than 2 dimensions"

        specpow,spec,starttime = specprocess(spec, **kwargs)
        like = self.template.xcorr(spec, **options)
        proposal = template.frame_xcorr(spec, **options)

        pitch_mmse = nx.zeros((spec.shape[1],chains))
        if btrace:
            pitch_map = []
        for chain in xrange(chains):
            # may be some use in multithreading here
            if cout: cout.write("+ Chain %d: forward particle filter\n" % chain)
            pfilt = particle.smc(like, proposal, **options)
            pfilt.initialize(nparticles=options['particles'], seed=base_seed + chain * 1000)
            pitch_mmse[0,chain] = pfilt.integrate(func=lambda x : self.template.pgrid[x])

            for f,p,w in pfilt.iterate(rwalk_scale=options['rwalk_scale'], keep_history=btrace):
                pitch_mmse[f,chain] = pfilt.integrate(func=lambda x: self.template.pgrid[x])

            if btrace:
                if cout: cout.write("+ Chain %d: reverse Vitterbi filter\n" % chain)
                particle_values = nx.column_stack(pfilt.particle_history)
                pitch_map.append(vitterbi.filter(particle_values, pfilt.loglike, proposal, **kwargs))

        if btrace:
            pitch_map = nx.column_stack(pitch_map)
        else:
            pitch_map = None

        return starttime, specpow, pitch_mmse, pitch_map

    def matched_spectrogram(self, signal):
        """
        Calculate a spectrogram of a signal using the same parameters
        as the template.
        """
        options = self.options
        return libtfr.tfr_spec(signal, options['nfft'], options['shift'], options['winsize'],
                               options['tfr_order'], options['tfr_tm'], options['tfr_flock'],
                               options['tfr_tlock'], fgrid=self.template.fgrid)

    def spectrogram_options_str(self):
        out = """\
* Spectrogram Parameters:
** Window size = %(winsize)d
** FFT size = %(nfft)d
** Tapers = %(tfr_order)d
** Time support = %(tfr_tm)f
** Frequency locking = %(tfr_flock)f
** Time locking = %(tfr_tlock)f""" % self.options
        return out


    def particle_options_str(self):
        """ Print parameters that affect particle tracker """
        out = """\
* Particle filter parameters:
** Number of chains = %(chains)d
** Particles per chain = %(particles)d
** Random walk scale = %(rwalk_scale)f
** Backtrace pitch = %(btrace)s"""
        return out % self.options

    def template_options_str(self):
        """ Print parameters that affect template """
        out = """\
* Harmonic template parameters:
** Max pitch jump = %(max_jump)d
** Pitch power threshold = %(pow_thresh)f
** Number of lobes = %(lobes)d
** Lobe decay = %(lobe_decay)f
** Negative lobe amplitude = %(neg_ampl)f
** Negative lobe width = %(neg_width)f
** Frequency range: %(freq_range)s (rel)""" % self.options
        out += "\n** Pitch range: (%.3f, %.3f) (rel)" % (self.template.pgrid[0],self.template.pgrid[-1])
        out += "\n** Candidate pitch count: %d" % self.template.pgrid.size
        return out



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
    return specpow[ind[0]:ind[-1]+1], spec[:,ind[0]:ind[-1]+1], ind[0]

def hz2rel(freqs, samplerate):
    """
    Convert frequency values to relative units, if needed.  Inputs are
    considered to be Hz if they're greater than 1.0
    """
    fun = lambda x : float(x)/samplerate if x > 1.0 else x
    return tuple(fun(f) for f in freqs)

def summarize_stats(cout, offset,power,pmmse,pmap, tgrid, pgrid, samplerate):
    """
    Print average pitch and variance for each of the estimators.
    Assumes <stats> is a sequence with the following four components:
    offset of first frame, power(frame), mmse(frame,chain),
    map(frame,chain) [last may be None].
    """
    fields = ['time','power','p.mmse','p.mmse.sd']
    if pmap is not None:
        fields += ['p.map','p.map.sd']
        pmap = nx.take(pgrid, pmap) * samplerate
    print >> cout, "\t".join(fields)
    pmmse *= samplerate
    for i in xrange(power.size):
        cout.write("%6.2f\t%6.2f\t%6.4f\t%6.4f" % \
                       (tgrid[i+offset],
                        nx.log10(power[i])*10,
                        nx.mean(pmmse[i,:]), nx.std(pmmse[i,:]),))

        if pmap is not None:
            cout.write("\t%6.4f\t%6.4f" % (nx.mean(pmap[i,:]), nx.std(pmap[i,:])))
        cout.write("\n")


def cpitch(argv=None, cout=None, cerr=None, **kwargs):
    """
Usage: cpitch [-c <config.cfg>] [-m <mask.ebl>] <signal.wav>

Calculates pitch of <signal.wav>, with optional masking by
<mask.ebl>. Output is to stdout.  See documentation for
configuration file details.
    """
    import sys
    from ..version import version
    if argv is None:
        argv = sys.argv[1:]
    if cout is None:
        cout = sys.stdout
    if cerr is None:
        cerr = sys.stderr

    import getopt
    from ..common.config import configoptions
    defaults = tracker.options.copy()
    defaults.update(kwargs)
    config = configoptions(defaults,'cpitch')

    maskfile = None

    opts,args = getopt.getopt(argv, 'hvc:m:')
    for o,a in opts:
        if o == '-h':
            print cpitch.__doc__
            return -1
        elif o == '-v':
            print "cpitch version %s" % version
            return -1
        elif o == '-c':
            config.read(a)
        elif o == '-m':
            maskfile = a

    options = config.items()
    if len(args) < 1:
        print cpitch.__doc__
        return -1

    print >> cout, "* Program: cpitch"
    print >> cout, "** Version: %s" % version
    print >> cout, "* Input: %s" % args[0]

    from ..common.audio import wavfile
    try:
        fp = wavfile(args[0])
    except IOError:
        print >> cerr, "No such file %s" % args[0]
        return -2
    except:
        print >> cerr, "Input file %s must be in WAV format" % args[0]
        return -2

    pcm = fp.read()
    samplerate = fp.sampling_rate
    print >> cout, "** Samples:", pcm.size
    print >> cout, "** Samplerate:", samplerate


    # adjust frequencies to relative units
    options['freq_range'] = hz2rel(options['freq_range'], samplerate)
    options['pitch_range'] = hz2rel(options['pitch_range'], samplerate)

    pt = tracker(**options)
    print >> cout, pt.spectrogram_options_str()
    print >> cout, pt.template_options_str()

    print >> cout, "* DLFT spectrogram:"
    spec = pt.matched_spectrogram(pcm)
    tgrid = nx.linspace(0, float(pcm.size) / samplerate * 1000, spec.shape[1])
    print >> cout, "** Dimensions:", spec.shape

    print >> cout, pt.particle_options_str()
    if maskfile is not None:
        print >> cout, "* Mask file:", maskfile
        from ..common.geom import elementlist, rasterize, geometry
        elems = elementlist.read(maskfile)
        boxmask = config.getboolean('boxmask',False)

        enum = 0
        for elem in elems:
            etype = elems.element_type(elem)
            mspec = spec
            if etype == 'interval':
                bounds = elem[:]
                print >> cout, "** Element %d, interval bounds (%.2f, %.2f)" % (enum, bounds[0], bounds[1])
                cols = nx.nonzero((tgrid >= bounds[0]) & (tgrid <= bounds[1]))[0]
            else:
                bounds = elem.bounds
                if boxmask:
                    print >> cout, "** Element %d, polygon interval (%.2f, %.2f)" % (enum, bounds[0], bounds[2])
                    cols = nx.nonzero((tgrid >= bounds[0]) & (tgrid <= bounds[2]))[0]
                else:
                    print >> cout, "** Element %d, polygon mask with bounds %s" % (enum, bounds)
                    mask = rasterize(elem, pt.template.fgrid * samplerate / 1000., tgrid)
                    print >> cout, "*** Mask size: %d/%d points" % (mask.sum(),mask.size)
                    cols = nx.nonzero(mask.sum(0))[0]
                    mspec = (spec * mask)
            print >> cout, "*** Using spectrogram frames from %d to %d" % (cols[0], cols[-1])
            print >> cout, "*** Pitch for element %d:" % (enum)
            return mspec
            starttime, specpow, pitch_mmse, pitch_map = pt.track(mspec[:,cols], cout=cout, **options)
            summarize_stats(cout, starttime+cols[0], specpow, pitch_mmse, pitch_map,
                            tgrid, pt.template.pgrid, samplerate / 1000.)
            enum += 1

    else:
        print >> cout, "* No mask file; calculating pitch for entire signal"
        print >> cout, "** Element 0, interval (tgrid[0],tgrid[-1])"
        starttime, specpow, pitch_mmse, pitch_map = pt.track(spec, cout=cout, **options)
        summarize_stats(cout, starttime, specpow, pitch_mmse, pitch_map,
                        tgrid, pt.template.pgrid, samplerate / 1000.)

    return 0

# Variables:
# End:
