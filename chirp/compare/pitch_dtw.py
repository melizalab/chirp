# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Compare signals using dynamic time warping of pitch traces

Copyright (C) 2011 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2011-08-30
"""

import numpy as nx
from ..common.config import _configurable
from ..common import postfilter
from .base_comparison import base_comparison

class pitch_dtw(base_comparison, _configurable):
    """
    Compute pairwise distances between motifs using spectrographic
    cross-correlation (SPCC). Configurable options:

    estimator:    the estimator to use
    metric:       the metric for comparing pairs of time points in pitch traces
    cost_matrix:  the cost matrix controlling moves through the metric space
    dynamic_cost: use dynamic cost matrix to ensure finite distances

    Additional options specify the degree of postfiltering; see
    common.postfilter.pitchfilter
    """
    options = dict(estimator = 'p.map',
                   metric = 'euclidean',
                   cost_matrix = [(1,1,1),(1,2,2),(2,1,2)],
                   dynamic_cost = True)

    def __init__(self, configfile=None, **kwargs):
        self.readconfig(configfile, ('spectrogram','ccompare_pitch_dtw',))
        self.options.update(kwargs)
        self.filter = postfilter.pitchfilter(configfile=configfile, **kwargs)

    def list_signals(self, location='', *args, **kwargs):
        """
        Iterates through all the PLG files in the specified directory.
        The ID for the signal is the name of the file, with the
        extension stripped.
        """
        return base_comparison.list_signals(self, location, '*.plg')

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

    def compare(self, ref, tgt):
        try:
            metric = metrics[self.options['metric']]
        except KeyError:
            raise ValueError, "%(metric)s has not been defined" % self.options

        T = metric(ref, tgt)

        if not self.options['dynamic_cost']:
            costmat = self.options['cost_matrix']
            p,q,D = dtw(T, costmat)
            dcost = totcost(p,q,D)
        else:
            # adaptively increases the permitted range of jumps until we get a real value
            dcost = nx.inf
            fudge = 0
            while not nx.isfinite(dcost):
                costmat = dtw_cost_dynamic(ref.size,tgt.size,fudge)
                p,q,D = dtw(T, costmat)
                dcost = totcost(p,q,D)
                fudge += 1
        return pathlen(p,q), dcost, dcost / min(ref.size, tgt.size)

    @property
    def compare_stat_fields(self):
        """ Return a tuple of the names for the statistics returned by compare() """
        return ("dlen","dist","dnorm")

    def options_str(self):
        out = """\
* DTW parameters:
** Estimator = %(estimator)s
** Metric %(metric)s
** Cost matrix = %(cost_matrix)s
** Dynamic cost matrix = %(dynamic_cost)s""" % self.options
        return out

def euclidean(x,y):
    """
    Compute euclidean distance matrix for all pairs of time points in
    two univariate time series.
    """
    T = (x - y[:,nx.newaxis])
    return T**2

metrics = {'euclidean' : euclidean}
    
def dtw_cost_dynamic(nref,ntgt,extra_steps=0):
    """
    Generates a symmetric cost matrix that is guaranteed to give a
    real number, but allows no more wiggle room than needed.
    """
    base = [(1,1,1),(1,2,2),(2,1,2)]
    min_warp = int(nx.ceil((1.0 * nref/ntgt) ** nx.sign(nref - ntgt))) + extra_steps
    if min_warp > 2: base.extend(((1,3,3),(3,1,3)))
    base.extend((1,n,nx.exp(n)/3) for n in range(4,min_warp+1))
    base.extend((n,1,nx.exp(n)/3) for n in range(4,min_warp+1))
    return base
    

def dtw(M, C=None):
    """
    Compute the minimum-cost path through a distance matrix using dynamic programming.

    M - cost matrix. Must contain no NaN values.  Should be positive for best results
    C - weighting function for step types.  3xN matrix, default ([1 1 1.0;0 1 1.0;1 0 1.0])
        An asymmetric C can enforce constraints on how much the inputs can be warped;
        e.g. C = ([1 1 1; 1 0 1; 1 2 1]) limits paths to a parallelogram with slope btw 1/2 and 2
        (i.e. the Itakura constraint)

    Adapted from dpfast.m/dpcore.c, by Dan Ellis <dpwe@ee.columbia.edu>

    """
    from scipy import weave

    if C==None:
        C = ([1, 1, 1.0],[0, 1, 1.0],[1, 0, 1.0])
    C = nx.asarray(C, dtype=M.dtype)

    assert C.ndim == 2 and C.shape[1]==3, "C must be an Nx3 array"
    assert nx.isfinite(M).sum()==M.size, "M can only contain finite values"
    if M.min() < 0: print "Warning: M contins negative values"

    D = nx.zeros_like(M)
    S = nx.zeros(M.shape, dtype='i')

    code = """
        #line 133 "pitch_dtw.py"
        double d1, d2, v, weight, _max;
        int stepi, stepj, beststep;

        v = M(0,0);
        _max = blitz::infinity(v);
        beststep = 1;
        for (int i = 0; i < M.rows(); i++) {
            for (int j = 0; j < M.cols(); j++) {
                d1 = M(i,j);
                for (int k = 0; k < C.rows(); k++) {
                    stepi = (int)C(k,0);
                    stepj = (int)C(k,1);
                    weight = C(k,2);
                    if (i >= stepi && j >= stepj) {
                        d2 = weight * d1 + D(i-stepi, j-stepj);
                        if (d2 < v) {
                             v = d2;
                             beststep = k;
                        }
                    }
                }
                D(i,j) = v;
                S(i,j) = beststep;
                v = _max;
            }
        }
    """

    weave.inline(code, ['M','C','D','S'],
                 headers=['"blitz/numinquire.h"'],
                 type_converters=weave.converters.blitz)

    # traceback
    i = M.shape[0] - 1
    j = M.shape[1] - 1
    p = [i]
    q = [j]
    while i > 0 and j > 0:
        tb = S[i,j]
        i = i - C[tb,0]
        j = j - C[tb,1]
        p.append(i)
        q.append(j)

    return nx.asarray(p[::-1], dtype='i'), nx.asarray(q[::-1], dtype='i'), D


def pathlen(p, q):
    """
    Computes the length of the DTW path. Normally this is just the
    size of the index vectors, but if the step-cost function has
    double steps (e.g. (1,2)) this has to be corrected.  Given a step
    size (x,y) the length of the step is defined as max(x,y), and the
    total math length is the sum of all the distances.
    """
    P = nx.diff(p)
    Q = nx.diff(q)
    return nx.sum(nx.maximum(P,Q))


def totcost(p,q,D):
    return D[p[-1],q[-1]]

# Variables:
# End:
