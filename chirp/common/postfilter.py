# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
postfiltering of pitch traces

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-08-29
"""
import numpy as nx
from ..common.config import _configurable

class pitchfilter(_configurable):
    """
    Postfilters pitch estimates based on particle variance and
    between-chain variance.  Configurable options are
    thresholds. These affect the beginnings and ends of signals,
    unless otherwise noted.  Set any threshold to 0 to disable.

    """
    options = dict(max_particle_sd=400,
                   max_chain_sd=0)
    config_options = ('postfilter',)

    def __init__(self, configfile=None, **kwargs):
        """
        Initialize the filter, setting options

        max_particle_sd: if the standard deviation of the particles
        exceeds this threshold, the estimate is considered
        unreliable. In Hz.

        max_chain_sd: similar to max_particle_sd, but applies to the
        standard deviation between chains.  Note that chain variance
        tends to be high for the MMSE estimator at the beginning of
        the signal because the chains need to converge; the opposite
        applies to the MAP estimator.  Therefore, this threshold
        applies to the maximum of the two interchain SDs. In Hz.
        """
        self.readconfig(configfile)
        self.options.update(kwargs)

    def __call__(self, pitch):
        """
        Given an input recarray or dictionary, return a logical array
        which is true for every time point where the pitch estimate is
        reliable.  The input must have a 'p.sd' field, and if the
        values are 2D the returned arrays will be as well.
        """
        if isinstance(pitch, nx.recarray):
            fields = pitch.dtype.names
            ind = nx.ones(pitch.size,dtype='bool')
        else:
            fields = pitch.keys()
            # should be guaranteed a p.sd field with current version of library
            ind = nx.ones(pitch['p.sd'].shape,dtype='bool')

        if 'p.sd' in fields and self.options['max_particle_sd'] > 0:
            ind &= pitch['p.sd'] < (0.001 * self.options['max_particle_sd'])
        if self.options['max_chain_sd'] > 0:
            sd = [pitch[f] for f in fields if (f in ('p.mmse.sd','p.map.sd'))]
            if len(sd) > 0:
                sd = nx.amax(sd, axis=0)
                ind &= sd[:,nx.newaxis] < (0.001 * self.options['max_chain_sd'])
        return ind

    def options_str(self):
        return """\
* Postfilter parameters:
** Max particle SD: %(max_particle_sd)f
** Max chain SD: %(max_chain_sd)f """ % self.options

def ind_endpoints(ind):
    """
    Given a 1D logical array, returns the first and last points that are True
    """
    q = nx.nonzero(ind)[0]
    return q[0], q[-1]

# Variables:
# End:
