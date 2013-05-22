# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
gui classes for selecting regions of an image with the mouse.

Copyright (C) 2009 Daniel Meliza <dan // meliza.org>
Created 2009-07-08
"""
import wx
from .wxcommon import Painter,FigCanvas,defaultstack

class PolygonPainter(Painter):
    """ Handles the actual drawing of the vertices onto the canvas """

    PEN = wx.BLACK_PEN
    BRUSH = wx.TRANSPARENT_BRUSH
    FUNCTION = wx.COPY
    selector = True

    def __init__(self, canvas):
        # vertex store
        super(PolygonPainter, self).__init__(canvas)
        self.value = defaultstack()

    def clear(self):
        self.value = defaultstack()

    def draw(self, dc=None):
        self._paint(self.value, dc)

    def _paint(self, points, dc=None):
        if dc==None:
            dc = wx.ClientDC(self.view)

        dc.SetPen(self.PEN)
        dc.SetBrush(self.BRUSH)
        dc.SetLogicalFunction(self.FUNCTION)
        dc.BeginDrawing()
        if len(points) < 2: return
        transpoints = [self.view.transform_canvas(x) for x in points]
        dc.DrawLines(transpoints)
        dc.EndDrawing()

    def add_vertex(self, x1, y1):
        """ Add a new point to the path """
        # clip values to current viewport
        x1,y1 = self.view.transform_data((x1,y1))
        bbox = self.view.axes.dataLim
        x1 = max(min(x1,bbox.x1),bbox.x0)
        y1 = max(min(y1,bbox.y1),bbox.y0)
        x0,y0 = self.value.peek() or (None,None)
        if not (x1==x0 and y1==y0):
            self.value.append((x1,y1))
            if not x0==None: self._paint(((x0,y0),(x1,y1)))

    def close_path(self):
        if len(self.value) > 2:
            self.value.append(self.value[0])
            self._paint((self.value[-2],self.value[-1]))

class DrawMask(FigCanvas):
    """
    Defines functionality for a FigCanvas to allow drawing polygonal
    masks on a graph.  The user clicks the left mouse button to start
    drawing, moves the mouse around the region of interest, and clicks
    again to close the polygon.
    """

    def __init__(self, parent, id=-1, figure=None, configfile=None):
        super(DrawMask,self).__init__(parent, id, figure)
        # state variables
        self.drawing = False
        # bind motion
        self.Bind(wx.EVT_MOTION, self.drawMotion)
        self.polygon = PolygonPainter(self)
        self.painters.append(self.polygon)

    def _onLeftButtonDown(self, evt):
        x,y = self._xypos(evt)
        if self.drawing:
            # close polygon
            self.polygon.close_path()
            self.drawing = False
            self.selector = None
        elif self._inaxes(x,y) and self.selector is None:
            # only start if in the axes
            self.drawing = True
            self.clear_painters()
            self.selector = self.polygon
            self.polygon.add_vertex(x,y)

    def drawMotion(self, evt):
        if self.drawing and self.selector==self.polygon:
            x,y = self._xypos(evt)
            self.polygon.add_vertex(x,y)
        else:
            evt.Skip()

def test():

    import matplotlib.cm as cm
    from matplotlib.figure import Figure
    import numpy as nx
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
            super(TSViewFrame, self).__init__(parent, title="DrawMask Test App", size=(1000,300),
                style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)
            self.figpanel = DrawMask(self, -1, Figure((7.0, 3.0)))
            plot_image(self.figpanel.axes)

    app = wx.PySimpleApp()
    app.frame = TSViewFrame()
    app.frame.Show()
    app.MainLoop()


# Variables:
# End:
