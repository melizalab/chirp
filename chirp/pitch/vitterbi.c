/* @file vitterbi.c
 *
 * Copyright (C) 2011 C Daniel Meliza <dan // meliza.org>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */
#include <stdlib.h>
#include <stdio.h>
#include <math.h>

void
filter(int * map, int const * particles, double const * loglikelihood,
       double const * logproposal, double const * lognormal, double minlog,
       int N, int K, int nL, int nP)
{

	int i,j,k;
	int x_i,x_j,jump,maxi;
	double arg, maxarg, lp;
	double *delta = (double*) calloc(N*K, sizeof(double));
	int *phi = (int*) calloc(N*K, sizeof(int));
	int *idx = (int*) calloc(K, sizeof(int));

	// initialization
	for (i = 0; i < N; i++) {
		x_i = particles[i*K+0];
		delta[i*K+0] = loglikelihood[x_i*K+0];
	}

	// recursion
	for (k = 1; k < K; k++) {
		for (j = 0; j < N; j++) {
			x_j = particles[j*K+k];
			maxarg = 0;
			maxi = 0;
			for (i = 0; i < N; i++) {
				arg = delta[i*K+k-1];
				x_i = particles[i*K+k-1];
				jump = x_j - x_i + nP / 2;
				if ((jump < 0) || (jump >= nP))
					arg += minlog;
				else {
					lp = logproposal[jump*(K-1)+k-1];
					if (lp <= minlog)
						arg += lognormal[jump];
					else
						arg += lp;
				}
				if ((arg > maxarg) || (i==0)) {
					maxarg = arg;
					maxi = i;
				}
			}
			phi[j*K+k] = maxi;
			delta[j*K+k] = maxarg;
			if ((x_j < 0) || (x_j >= nL))
				delta[j*K+k] += minlog;
			else
				delta[j*K+k] += loglikelihood[x_j*K+k];
		}
	}

	// backtrace
	maxarg = 0;
	maxi = 0;
	for (i = 0; i < N; ++i) {
		if ((i==0) || (delta[i*K+K-1] > maxarg)) {
			maxarg = delta[i*K+K-1];
			maxi = i;
		}
	}
	idx[K-1] = maxi;
	for (k = K-2; k >= 0; --k)
		idx[k] = phi[idx[k+1]*K + k+1];
	for (k = 0; k < K; ++k)
		map[k] = particles[idx[k]*K + k];

	free(delta);
	free(phi);
	free(idx);
}
