# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
Compare signals using dynamic time warping of features (base class
only).

Copyright (C) 2011 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2011-09-01
"""

import numpy as nx
from ..common.config import _configurable
from .base_comparison import base_comparison

class feat_dtw(base_comparison, _configurable):
    """
    Compute pairwise distances between motifs using dynamic time
    warping of one or more features. This class is abstract; deriving
    classes need to implement a concrete method for loading the
    features from a file (and preprocessing as needed).

    Configurable options:

    metric:       the metric for comparing pairs of time points in pitch traces
    cost_matrix:  the cost matrix controlling moves through the metric space
    dynamic_cost: use dynamic cost matrix to ensure finite distances
    """
    options = dict(cost_matrix = [(1,1,1),(1,2,2),(2,1,2)],
                   metric = 'euclidean',
                   dynamic_cost = True)
    config_sections = ('dtw',)

    def __init__(self, configfile=None, **kwargs):
        self.readconfig(configfile)
        self.options.update(kwargs)

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
** Distance metric = %(metric)s
** Cost matrix = %(cost_matrix)s
** Dynamic cost matrix = %(dynamic_cost)s""" % self.options
        return out

def dist_euclidean(x,y):
    """
    Compute euclidean distance matrix for all pairs of time points in
    two time series. Time series can be multivariate, with
    observations in rows and variables in columns.
    """
    T = (x - y[:,nx.newaxis])
    if T.ndim > 2:
        return (T**2).sum(2)
    else:
        return T**2

def dist_cos(x,y):
    """
    Compute distance matrix for all pairs of time points in two time
    series as the cosine of the angle between vectors at each
    time. Inputs must be multivariate, with observations in rows and
    variables in columns.
    """
    if not (x.ndim == 2 and y.ndim == 2):
        raise ValueError, "inputs must be multivariate, observations x variables"
    xpow = nx.sqrt((x**2).sum(1))
    ypow = nx.sqrt((y**2).sum(1))
    return nx.absolute(1 - nx.asarray(nx.asmatrix(y) * nx.asmatrix(x).T) / nx.outer(ypow,xpow))

metrics = {'euclidean' : dist_euclidean,
           'cosine': dist_cos}

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
    """
    from _dtw import dtw_forward

    if C==None:
        C = ([1, 1, 1.0],[0, 1, 1.0],[1, 0, 1.0])
    C = nx.asarray(C, dtype=M.dtype)

    assert C.ndim == 2 and C.shape[1]==3, "C must be an Nx3 array"
    assert nx.isfinite(M).sum()==M.size, "M can only contain finite values"
    if M.min() < 0:
        #raise Exception, "M contains negative values"
        print "Warning: M contins negative values"

    D,S = dtw_forward(M,C)

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
