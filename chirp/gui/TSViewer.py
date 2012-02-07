# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
widget for viewing and browsing time series data, in particular
spectrogram-type data in which there are fixed Y limits.  The user can
zoom in on particular time segments of the data by selecting regions
with the middle mouse button and pushing the down arrow key.  In
zoomed mode the left and right keys move the viewport.

Copyright (C) 2009 Daniel Meliza <dan // meliza.org>
Created 2009-07-06
"""
import wx
from .wxcommon import Painter,FigCanvas,defaultstack
from ..common.config import _configurable

class RubberbandPainter(Painter):
    PEN = wx.WHITE_PEN
    FUNCTION = wx.XOR
    selector = True

    def clearValue(self, dc, value):
        self.drawValue(dc,value)

class XRubberbandPainter(RubberbandPainter):
    """ Draws a vertical selection rubberband (for selecting x ranges). """

    def set(self, value):
        # axis coordinates
        if value!=None:
            value = [self.view.transform_data((x,0))[0] for x in value]
        Painter.set(self, value)

    def drawValue(self, dc, value):
        # transform to figure coordinates
        x1,x2 = [self.view.transform_canvas((x,0))[0] for x in value]
        height = self.view.figure.bbox.height
        y1,y2 = [height-y for y in self.view.axes.bbox.intervaly]
        dc.DrawLine(x1,y1,x1,y2)
        dc.DrawLine(x2,y1,x2,y2)


class YRubberbandPainter(RubberbandPainter):
    """ Draws a horizontal selection rubberband (for selecting y ranges). """

    def set(self, value):
        # axis coordinates
        if value!=None:
            value = [self.view.transform_data((0,y))[1] for y in value]
        Painter.set(self, value)

    def drawValue(self, dc, value):
        # transform to figure coordinates
        y1,y2 = [self.view.transform_canvas((0,y))[1] for y in value]
        x1,x2 = self.view.axes.bbox.intervalx
        dc.DrawLine(x1,y1,x2,y1)
        dc.DrawLine(x1,y2,x2,y2)


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

    def draw(self):
        """ Update the display after changing data or viewport """
        self.canvas.draw()

    @property
    def xdatalim(self):
        """ The mininum and maximum x values for the data """
        return tuple(self.axes.dataLim.intervalx)

    @property
    def ydatalim(self):
        """ The mininum and maximum y values for the data """
        return tuple(self.axes.dataLim.intervaly)

    @staticmethod
    def _check_limits(v1,v2,minv,maxv):
        """
        Adjusts limits v1 and v2 so that they're ordered and they fit
        into minv/maxv.  The spacing between v1 and v2 is maintained.
        If v1 and/or v2 are None, they are set to the limit.
        """
        if v1==None:
            v1 = minv
        if v2==None:
            v2 = maxv
        if v1 > v2:
            v1,v2 = v2,v1
        if v1 < minv:
            v2 += minv - v1
            v1 = minv
        if v2 > maxv:
            v1 = max(minv, v1 - (v2 - maxv))
            v2 = maxv
        return v1,v2

    def get_xlim(self):
        return self.axes.get_xlim()
    def set_xlim(self, value):
        """
        Set the viewport bounds; None indicates data limit.  Automatically
        adjust endpoints if they overstep the data bounds.
        """
        t1,t2 = self._check_limits(*(value + self.xdatalim))
        self.axes.set_xlim(t1,t2)
        self.draw()
    tlim = property(get_xlim, set_xlim)

    def get_ylim(self):
        return self.axes.get_ylim()
    def set_ylim(self, value):
        """
        Set the viewport bounds; None indicates data limit.  Automatically
        adjust endpoints if they overstep the data bounds.
        """
        y1,y2 = self._check_limits(*(value + self.ydatalim))
        self.axes.set_ylim(y1,y2)
        self.draw()
    ylim = property(get_ylim, set_ylim)


class TSViewer(FigCanvas, _configurable):
    """
    The TSViewer subclasses FigureCanvasWxAgg and contains a single
    axes which supports the following interactions:

    * middle-button drag to select a region of the time series
    * up-down keys to zoom and unzoom horizontally
    * left-right keys to navigate a zoomed time series horizontally
    * right-button drag to select a vertical region
    * shift up-down keys to zoom and unzoom vertically

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
        self.xrubberband = XRubberbandPainter(self)
        self.painters.append(self.xrubberband)
        self.yrubberband = YRubberbandPainter(self)
        self.painters.append(self.yrubberband)

        # keep track of viewports
        self.tlims = defaultstack()
        self.ylims = defaultstack()

        # handlers
        # have to bind our own motion handler to permit multiple inheritance
        self.Bind(wx.EVT_MOTION, self.onMotion)
        self.Bind(wx.EVT_CHAR, self.on_key)

    def plot_data(self, *args, **kwargs):
        """ Calls the handler's plot_data method to populate the figure with data """
        self.handler.plot_data(*args, **kwargs)

    def xzoom_viewport(self, value):
        """
        Zoom viewport. +1 for in to selected region; -1 for out to
        last zoom level, either the previous limits if the current
        position is still in the old region, or to a region centered
        around the current position.
        """
        if value==1 and self.xrubberband.value:
            t1,t2 = self.xrubberband.value
            self.tlims.append(self.handler.tlim)
            self.xrubberband.clear()
            self.handler.tlim = t1,t2
        elif value==-1:
            prev = self.tlims.pop()
            if not prev==None:
                curr = self.handler.tlim
                if curr[0] > prev[0] and curr[1] < prev[1]:
                    # reset to previous viewport
                    self.handler.tlim = prev
                else:
                    # use previous zoom level centered around current location
                    xhw = (prev[1] - prev[0]) / 2.
                    xmid = (curr[1] - curr[0]) / 2. + curr[0]
                    self.handler.tlim = (xmid - xhw, xmid + xhw)

    def yzoom_viewport(self, value):
        """
        Zoom viewport vertically. Same semantics as xzoom_viewport,
        except if there's no previous value in the stack, pops out to
        the data limit.  Also, because panning is unsupported, we
        don't have to check current location
        """
        if value==1 and self.yrubberband.value:
            y1,y2 = self.yrubberband.value
            self.ylims.append(self.handler.ylim)
            self.yrubberband.clear()
            self.handler.ylim = y1,y2
        elif value==-1:
            prev = self.ylims.pop()
            if not prev==None:
                self.handler.ylim = prev
            else:
                self.handler.ylim = None,None


    def xpan_viewport(self, pos):
        """
        Move the viewport left or right. Pos is equal to the
        proportion of the current viewport; negative values for left,
        positive for right.
        """
        x1,x2 = self.handler.xdatalim
        curr = self.handler.tlim
        if curr[0] >= x1 and curr[1] <= x2:
            xext = curr[1] - curr[0]
            self.handler.tlim = (curr[0] + pos*xext, curr[1] + pos*xext)


    # Event dispatching
    def _onMiddleButtonDown(self, evt):
        x,y = self._xypos(evt)
        if self._inaxes(x,y) and self.selector is None:
            self.clear_painters()
            self.selector = self.xrubberband
            self.select_start = x
            self.CaptureMouse()

    def _onMiddleButtonUp(self, evt):
        x,y = self._xypos(evt)
        if self.HasCapture():
            self.ReleaseMouse()
            if self.select_start==x: self.xrubberband.clear()
            self.select_start = None
            self.selector = None

    def _onRightButtonDown(self, evt):
        x,y = self._xypos(evt)
        if self._inaxes(x,y) and self.selector is None:
            self.clear_painters()
            self.selector = self.yrubberband
            self.select_start = y
            self.CaptureMouse()

    def _onRightButtonUp(self, evt):
        x,y = self._xypos(evt)
        if self.HasCapture():
            self.ReleaseMouse()
            if self.select_start==y: self.yrubberband.clear()
            self.select_start = None
            self.selector = None
            self.yzoom_viewport(1)


    def onMotion(self, evt):
        if evt.Dragging() and self.select_start!=None:
            if self.selector == self.xrubberband:
                x0 = self.select_start
                x,y = self._xypos(evt)
                if self._inaxes(x,y):
                    self.xrubberband.set((x0,x))
            elif self.selector == self.yrubberband:
                y0 = self.select_start
                x,y = self._xypos(evt)
                if self._inaxes(x,y):
                    self.yrubberband.set((y0,y))
        else:
            evt.Skip()

    def on_key(self, event):
        """ Handle navigation keys """
        key = event.GetKeyCode()
        if key==wx.WXK_DOWN:
            self.xzoom_viewport(1)
        elif key==wx.WXK_UP:
            if event.ShiftDown():
                self.yzoom_viewport(-1)
            else:
                self.xzoom_viewport(-1)
        elif key==wx.WXK_LEFT:
            self.xpan_viewport(-self.options['pan_proportion'])
        elif key==wx.WXK_RIGHT:
            self.xpan_viewport(self.options['pan_proportion'])
        else:
            event.Skip()

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
