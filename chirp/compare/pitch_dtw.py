# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
compare signals using dynamic time warping of pitch traces

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-08-30
"""
import numpy as nx
from ..common import postfilter
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
    options = dict(estimator = 'p.map',
                   **feat_dtw.options)

    def __init__(self, configfile=None, **kwargs):
        feat_dtw.__init__(self, configfile=configfile, **kwargs)
        self.readconfig(configfile, ('pitch_dtw',))
        self.options.update(kwargs)
        self.filter = postfilter.pitchfilter(configfile=configfile, **kwargs)

    def list_signals(self, location='', *args, **kwargs):
        """
        Iterates through all the PLG files in the specified directory.
        The ID for the signal is the name of the file, with the
        extension stripped.
        """
        return feat_dtw.list_signals(self, location, '*.plg')

    def load_signal(self, id, locator, cout=None):
        """
        Loads the pitch trace and filters it. If no points are
        reliable, returns None.

        dtype: the data type to store the output in. Default is
               single-precision to reduce storage requirements.
        """
        from ..common import plg
        pest = plg.read(locator)
        ind = self.filter(pest)
        if not any(ind):
            return None
        else:
            ind = postfilter.ind_endpoints(ind)
            return pest[self.options['estimator']][ind[0]:ind[1]+1]

    @property
    def compare_stat_fields(self):
        """ Return a tuple of the names for the statistics returned by compare() """
        return ("dlen","dist","dnorm")

    def options_str(self):
        out = feat_dtw.options_str(self) + "\n** Estimator = %(estimator)s" % self.options
        return out

# Variables:
# End:
