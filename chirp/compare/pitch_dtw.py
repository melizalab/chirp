# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
compare signals using dynamic time warping (or CC) of pitch traces

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-08-30
"""
import numpy as nx
from ..common import postfilter
from ..common.config import _configurable
from .base_comparison import base_comparison
from .feat_dtw import feat_dtw


class pitch_dtw(feat_dtw):
    """
    Compute pairwise distances between motifs using dynamic time
    warping of the pitch traces. Configurable options:

    estimator:    the estimator to use
    metric:       the metric for comparing pairs of time points in pitch traces
    cost_matrix:  the cost matrix controlling moves through the metric space
    dynamic_cost: use dynamic cost matrix to ensure finite distances

    Additional options specify the degree of postfiltering; see
    common.postfilter.pitchfilter
    """
    # short description
    _descr = "dynamic time warping of pitch traces (requires .plg files)"

    file_extension = '.plg'
    options = dict(estimator='p.map', **feat_dtw.options)
    config_sections = ('spectrogram', 'dtw', 'pitch_dtw')

    def __init__(self, configfile=None, **kwargs):
        feat_dtw.__init__(self, configfile=configfile, **kwargs)
        self.readconfig(configfile)
        self.options.update(kwargs)
        self.filter = postfilter.pitchfilter(configfile=configfile, **kwargs)

    def load_signal(self, locator, cout=None):
        return _load_plg(locator, self.filter, self.options['estimator'])

    def options_str(self):
        out = feat_dtw.options_str(self) + "\n** Estimator = %(estimator)s" % self.options
        return out


class pitch_cc(base_comparison, _configurable):
    """
    Compute pairwise distances between motifs using peak cross-correlation of
    the pitch traces. Configurable options:

    estimator:    the estimator to use
    """
    # short description
    _descr = "dynamic time warping of pitch traces (requires .plg files)"

    file_extension = '.plg'
    options = dict(estimator='p.map')
    config_sections = ('pitch_cc')

    def __init__(self, configfile=None, **kwargs):
        self.readconfig(configfile)
        self.options.update(kwargs)
        self.filter = postfilter.pitchfilter(configfile=configfile, **kwargs)

    def load_signal(self, locator, cout=None):
        return _load_plg(locator, self.filter, self.options['estimator'])

    def compare(self, ref, tgt):
        from .spcc import spectcc
        R = ref - ref.mean()
        T = tgt - tgt.mean()
        return (spectcc(R, T, biased_norm=True).sum(0).max(),)

    def options_str(self):
        out = "** Estimator = %(estimator)s" % self.options
        return out

    @property
    def compare_stat_fields(self):
        """ Return a tuple of the names for the statistics returned by compare() """
        return ("pcc",)


def _load_plg(locator, filt, estimator):
    """
    Load a pitch trace and filters it. If no points are
    reliable, returns None.
    """
    from ..common import plg
    pest = plg.read(locator)
    ind = filt(pest)
    if not any(ind):
        return None
    else:
        ind = postfilter.ind_endpoints(ind)
        return pest[estimator][ind[0]:ind[1] + 1]

# Variables:
# End:
