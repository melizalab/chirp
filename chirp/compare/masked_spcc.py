# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
masked_spcc.py

Copyright (C) 2011 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2011-08-30
"""

import os.path
from .spcc import *
from ..common.geom import elementlist, masker


class masked_spcc(spcc):
    """
    Extends the spcc class to support use of polygon masks for
    denoising.  Can do a full 2D mask or just use the bounding box for
    the start/stop times of the mask.
    """
    options = dict(boxmask = True,
                   **spcc.options)

    def __init__(self, configfile=None, **kwargs):
        self.readconfig(configfile, ('spectrogram','compare_spcc',))
        self.options.update(kwargs)
        self.masker = masker(boxmask=self.options['boxmask'])

    def load_signal(self, id, locator, dtype='d'):
        eblfile = os.path.splitext(locator)[0] + elementlist.default_extension
        if not os.path.exists(eblfile):
            return spcc.load_signal(self, id, locator, dtype)

        from ..common.audio import wavfile
        fp = wavfile(locator)
        signal = fp.read()
        Fs = fp.sampling_rate
        S,F,T = linspect(signal, Fs, self.options['freq_range'],
                         self.options['nfreq'], self.options['shift'])

        mask = elementlist.read(eblfile)
        imask = self.masker.mask(mask, T * 1000., F / 1000.)
        S[~imask] = 0
        return S.astype(dtype)

    def options_str(self):
        return spcc.options_str(self) + "\n** Using full mask = %s" % self.options['boxmask']

    @property
    def compare_stat_fields(self):
        """ Return a tuple of the names for the statistics returned by compare() """
        if self.options['boxmask']: return ("spcc",)
        else: return ("spcc_mask",)
    
# Variables:
# End:
