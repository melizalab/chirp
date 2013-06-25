# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
Plotting utilities

Copyright (C) 2011 Dan Meliza <dan // meliza.org>
Created 2011-08-10
"""


def axgriditer(gridfun=None, figfun=None, **figparams):
    """
    Generates axes for multiple gridded plots.  Initial call
    to generator specifies plot grid (default 1x1).  Yields axes
    on the grid; when the grid is full, opens a new figure and starts
    filling that.

    Arguments:
    gridfun - function to open figure and specify subplots. Needs to to return
              fig, axes. Default function creates one subplot in a figure.

    figfun - called when the figure is full or the generator is
             closed.  Can be used for final figure cleanup or to save
             the figure.  Can be callable, in which case the
             signature is figfun(fig); or it can be a generator, in
             which case its send() method is called.

    additional arguments are passed to the figure() function
    """
    if gridfun is None:
        from matplotlib.pyplot import subplots
        gridfun = lambda: subplots(1, 1)

    fig, axg = gridfun(**figparams)
    try:
        while 1:
            for ax in axg.flat:
                yield ax
            if callable(figfun): figfun(fig)
            elif hasattr(figfun, 'send'): figfun.send(fig)
            fig, axg = gridfun(**figparams)
    except:
        # cleanup and re-throw exception
        if callable(figfun): figfun(fig)
        elif hasattr(figfun, 'send'): figfun.send(fig)
        raise


# Variables:
# End:
