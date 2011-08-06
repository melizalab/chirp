# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
vitterbi.py  Reverse vitterbi filter finds MAP path through particle filter output

Copyright (C) 2011 Dan Meliza <dmeliza@gmail.com>
Created 2011-08-02
"""

# currently implemented using weave; change to cython for portability
import numpy as nx
from scipy import weave

code = """
        typedef blitz::Array<double,2> dmatrix;
        typedef blitz::Array<double,1> dvector;
        typedef blitz::Array<int,2> imatrix;
        typedef blitz::Array<int,1> ivector;

	int i,j,k;
	int x_i,x_j;  // state values
	int N = particle_values.rows();
	int K = particle_values.cols();
        int njumps = proposal.rows();
        int npitch = likelihood.rows();

	dmatrix delta(N,K);  // some wasted space, but potentially useful in debug
	imatrix phi(N,K);
	dvector arg(N);

	// initialization
	for (i = 0; i < N; i++) {
		x_i = particle_values(i,0);
		delta(i,0) = likelihood(x_i,0);  // guaranteed to be in bounds
	}
	// recursion
	for (k = 1; k < K; k++) {
		for (j = 0; j < N; j++) {
			x_j = particle_values(j,k);
			for (i = 0; i < N; i++) {
				arg(i) = delta(i,k-1);
				x_i = particle_values(i,k-1);
				int jump = x_j - x_i + njumps / 2;
                                if ((jump < 0) || (jump >= njumps))
					arg(i) += min_loglike;
				else if (proposal(jump,k-1) <= 0)
					// random walk
					arg(i) += -0.5 * (log(2 * M_PI * rwalk_scale * rwalk_scale) +
							  pow(double(x_j - x_i) / rwalk_scale, 2.0));
				else
					arg(i) += log(proposal(jump,k-1));
			}
			phi(j,k) = blitz::maxIndex(arg)(0);
			delta(j,k) = arg(phi(j,k));
			if ((x_j < 0) || (x_j >= npitch))
				delta(j,k) += min_loglike;
			else
				delta(j,k) += likelihood(x_j,k);
		}
	}
	ivector particle_idx(K);
	pitch.resize(K);

	particle_idx(K-1) = blitz::maxIndex(delta(blitz::Range::all(),K-1))(0);
	for (k = K-2; k >= 0; --k)
		particle_idx(k) = phi(particle_idx(k+1),k+1);
	for (k = 0; k < K; ++k)
		pitch(k) = particle_values(particle_idx(k),k);
"""

def filter(particle_values, likelihood, proposal, rwalk_scale=1e-2, min_loglike=-100, **kwargs):
    """
    Run the Vitterbi reverse filter. This requires the particle values
    for each time frame, the likelihood function, and the proposal
    function.
    """
    pitch = nx.zeros(particle_values.shape[1],dtype=particle_values.dtype)
    weave.inline(code, ['particle_values','likelihood','proposal','rwalk_scale','min_loglike','pitch'],
                 type_converters=weave.converters.blitz)
    return pitch

# Variables:
# End:
