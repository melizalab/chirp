#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
widget for viewing and browsing time series data, in particular
spectrogram-type data in which there are fixed Y limits.  The user can
zoom in on particular time segments of the data by selecting regions
with the middle mouse button and pushing the down arrow key.  In
zoomed mode the left and right keys move the viewport.

Copyright (C) 2009 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2009-07-06
"""

import wx
from .wxcommon import *
from ..common.config import _configurable

class RubberbandPainter(Painter):
    """
    Draws a selection rubberband from one point to another.
    """

    PEN = wx.WHITE_PEN
    FUNCTION = wx.XOR
    selector = True

    def set(self, value):
        # axis coordinates
        if value!=None:
            value = [self.view.transform_data((x,0))[0] for x in value]
        super(RubberbandPainter,self).set(value)

    def drawValue(self, dc, value):
        # transform to figure coordinates
        x1,x2 = [self.view.transform_canvas((x,0))[0] for x in value]
        height = self.view.figure.bbox.height
        y1,y2 = [height-y for y in self.view.axes.bbox.intervaly]
        dc.DrawLine(x1,y1,x1,y2)
        dc.DrawLine(x2,y1,x2,y2)

    def clearValue(self, dc, value):
        self.drawValue(dc,value)


class TSDataHandler(object):
    """
    Encapsulates all the data-navigation logic for TSViewer. Default
    implementation just stores the data in the axes and uses builtin
    mpl commands to change the viewport.
    """

    def set_axes(self, axes):
        """ Set the location where the handler will draw the data """
        self.axes = axes
        self.canvas = axes.figure.canvas

    # override these methods to change how data is pushed to the plot
    def plot_data(self, func):
        """ Calls func(self.axes) to populate the axes with data """
        func(self.axes)

    def _set_xlim(self, *value):
        """ Set the viewport on existing data then redraw the canvas """
        self.axes.set_xlim(*value)
        self.draw()

    def draw(self):
        """ Update the display after changing data or viewport """
        self.canvas.draw()

    @property
    def dataLim(self):
        """ The mininum and maximum values for the data """
        return self.axes.dataLim.intervalx

    # convenience viewport values access:
    def get_tlim(self):
        return self.axes.get_xlim()
    def set_tlim(self, value):
        """
        Set the viewport bounds; None indicates data limit.  Automatically
        adjust endpoints if they overstep the data bounds.  Calls _set_xlim,
        which does the actual work of updating the plot.
        """
        x1,x2 = self.dataLim
        t1,t2 = value
        if t1==None:
            t1 = x1
        if t2==None:
            t2 = x2
        if t1 > t2:
            t1,t2 = t2,t1
        if t1 < x1:
            t2 += x1 - t1
            t1 = x1
        if t2 > x2:
            t1 = max(x1, t1 - (t2 - x2))
            t2 = x2
        self._set_xlim((t1,t2))
    tlim = property(get_tlim, set_tlim)


class TSViewer(FigCanvas, _configurable):
    """
    The TSViewer subclasses FigureCanvasWxAgg and contains a single
    axes which supports the following interactions:

    * middle-button drag to select a region of the time series
    * up-down keys to zoom and unzoom
    * left-right keys to navigate a zoomed time series

    A separate object is used for data handling; by default this is a
    TSDataHandler instance, which just pushes data to the underlying
    axes object.
    """
    options = dict(pan_proportion = 0.8)
    
    def __init__(self, parent, id=-1, figure=None, handler=TSDataHandler, configfile=None):
        super(TSViewer, self).__init__(parent, id, figure)
        self.readconfig(configfile,('spectrogram',))

        # data handler
        if isinstance(handler,type):
            handler = handler()
        self.handler = handler
        self.handler.set_axes(self.axes)

        # 1D rubberband
        self.select_start = None
        self.rubberband = RubberbandPainter(self)
        self.painters.append(self.rubberband)

        # keep track of viewports
        self.tlims = defaultstack()

        # handlers
        # have to bind our own motion handler to permit multiple inheritance
        self.Bind(wx.EVT_MOTION, self.onMotion)
        self.mpl_connect('key_press_event', self.on_key)

    def plot_data(self, *args, **kwargs):
        """ Calls the handler's plot_data method to populate the figure with data """
        self.handler.plot_data(*args, **kwargs)

    def zoom_viewport(self, value):
        """
        Zoom viewport. +1 for in to selected region; -1 for out to
        last zoom level, either the previous limits if the current
        position is still in the old region, or to a region centered
        around the current position.
        """
        if value==1 and self.rubberband.value:
            t1,t2 = self.rubberband.value
            self.tlims.append(self.get_tlim())
            self.rubberband.clear()
            self.handler.tlim = t1,t2
        elif value==-1:
            prev = self.tlims.pop()
            if not prev==None:
                curr = self.get_tlim()
                if curr[0] > prev[0] and curr[1] < prev[1]:
                    # reset to previous viewport
                    self.handler.tlim = prev
                else:
                    # use previous zoom level centered around current location
                    xhw = (prev[1] - prev[0]) / 2.
                    xmid = (curr[1] - curr[0]) / 2. + curr[0]
                    self.handler.tlim = (xmid - xhw, xmid + xhw)


    def pan_viewport(self, pos):
        """
        Move the viewport left or right. Pos is equal to the
        proportion of the current viewport; negative values for left,
        positive for right.
        """
        x1,x2 = self.handler.dataLim
        curr = self.get_tlim()
        if curr[0] >= x1 and curr[1] <= x2:
            xext = curr[1] - curr[0]
            self.handler.tlim = (curr[0] + pos*xext, curr[1] + pos*xext)

    def get_tlim(self):
        return tuple(self.axes.get_xlim())

    # Event dispatching
    def _onMiddleButtonDown(self, evt):
        x,y = self._xypos(evt)
        if self._inaxes(x,y) and self.selector is None:
            self.clear_painters()
            self.selector = self.rubberband
            self.select_start = x
            self.CaptureMouse()

    def _onMiddleButtonUp(self, evt):
        x,y = self._xypos(evt)
        if self.HasCapture():
            self.ReleaseMouse()
            if self.select_start==x: self.rubberband.clear()
            self.select_start = None
            self.selector = None

    def onMotion(self, evt):
        if evt.Dragging() and self.select_start!=None:
            x0 = self.select_start
            x,y = self._xypos(evt)
            if self._inaxes(x,y):
                self.rubberband.set((x0,x))
        else:
            evt.Skip()

    def on_key(self, event):
        """ Handle arrow keys """
        if event.key=='down':
            self.zoom_viewport(1)
        elif event.key=='up':
            self.zoom_viewport(-1)
        elif event.key=='left':
            self.pan_viewport(-self.options['pan_proportion'])
        elif event.key=='right':
            self.pan_viewport(self.options['pan_proportion'])

def test():

    import numpy as nx
    import matplotlib.cm as cm
    def plot_image(axes):
        def func3(x,y):
            return (1- x/2 + x**5 + y**3)*nx.exp(-x**2-y**2)

        dx, dy = 0.025, 0.025
        x = nx.arange(-3.0, 3.0, dx)
        y = nx.arange(-3.0, 3.0, dy)
        X,Y = nx.meshgrid(x, y)
        Z = func3(X, Y)

        im = axes.imshow(Z, cmap=cm.jet, extent=(-3, 3, -3, 3))

    class TSViewFrame(wx.Frame):
        def __init__(self, parent=None):
            super(TSViewFrame, self).__init__(parent, title="TSViewer Test App", size=(1000,300),
                style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)
            self.figpanel = TSViewer(self, -1)
            self.figpanel.plot_data(plot_image)


    app = wx.PySimpleApp()
    app.frame = TSViewFrame()
    app.frame.Show()
    app.MainLoop()



# Variables:
# End:
