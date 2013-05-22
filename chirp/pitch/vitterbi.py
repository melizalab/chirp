# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
reverse vitterbi filter finds MAP path through particle filter output

Copyright (C) 2011 Dan Meliza <dan // meliza.org>
Created 2011-08-02
"""

import numpy as nx
import _vitterbi

def filter(particles, loglikelihood, proposal, rwalk_scale=1e-2, min_loglike=-100, **kwargs):
    """
    Run the Vitterbi reverse filter. This is an O(N^2t) operation that
    finds the MAP path through the posterior density.

    particles: the values of the particles at each time point,
               N particles by K time points
    likelihood: the loglikelihood associated with all valid values, L by K
    proposal:   P(x_i|x_{i-1}), P by K-1
    """
    # do some precalculations expected by _vitterbi
    logprop = nx.log(nx.maximum(proposal,nx.exp(min_loglike)))
    P   = logprop.shape[0]
    idx = nx.arange(-P/2,P/2)
    lognorm = -0.5 * (nx.log(2 * nx.pi * rwalk_scale**2) + (idx.astype('d') / rwalk_scale)**2)

    return _vitterbi.filter(particles, loglikelihood, logprop, lognorm, min_loglike)

# Variables:
# End:
