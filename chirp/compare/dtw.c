/* @file dtw.c
 *
 * Copyright (C) 2011 C Daniel Meliza <dan // meliza.org>
 *
 * Adapted from dpfast.m/dpcore.c, by Dan Ellis <dpwe@ee.columbia.edu>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */

/* A note to myself about storage order:
 *
 * Arguments should be passed in C storage order, with last element
 * varying fastest. So that means a numpy index A[i,j] turns into
 * A[i*N+j] where N is the number of columns in A.
 */

#include <math.h>

/**
 * Performs the forward step of the dynamic time warping algorithm.
 *
 * @param M pairwise distance metric, nrow x ncol. No NaNs,
 *          should be positive.
 *
 * @param C move cost matrix, ncost x 3, defines weights for different
 *          types of steps.  Standard choice is ([1 1 1.0;0 1 1.0;1 0
 *          1.0]), some prefer Itakura constraint [(1,1,1),(1,2,2),(2,1,2)]
 *
 * @param D output distance matrix, nrow x ncol.
 *
 * @param S output step size matrix, nrow x ncol.
 */
void
dtw_forward(double const * M, double const * C, double * D, int * S,
	    int nrow, int ncol, int ncost)
{
	double const _max = INFINITY;

	double v = M[0];
	int beststep = 1;
      int i,j,k;
	for (i = 0; i < nrow; ++i) {
		for (j = 0; j < ncol; ++j) {
			double d1 = M[i*ncol+j];
			for (k = 0; k < ncost; ++k) {
				int stepi = (int)C[k*3+0];
				int stepj = (int)C[k*3+1];
				double weight = C[k*3+2];
				if (i >= stepi && j >=stepj) {
					double d2 = weight * d1 + D[(i-stepi)*ncol+(j-stepj)];
					if (d2 < v) {
						v = d2;
						beststep = k;
					}
				}
			}
			D[i*ncol+j] = v;
			S[i*ncol+j] = beststep;
			v = _max;
		}
	}
}
