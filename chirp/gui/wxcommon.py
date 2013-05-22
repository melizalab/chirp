# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
various wxpython-related tools

Copyright (C) 2009 Daniel Meliza <dan // meliza.org>
Created 2009-07-08
"""
import wx
import matplotlib
matplotlib.use('WXAgg')

# set display parameters; this is especially important for the standalone app
mpl_params = {'axes.hold': False,
              'axes.linewidth': 0.5,
              'ytick.labelsize' : 'small',
              'ytick.direction' : 'out',
              'xtick.labelsize' : 'small',
              'xtick.direction' : 'out',
              'image.aspect' : 'auto',
              'image.origin' : 'lower',
              }
matplotlib.rcParams.update(mpl_params)

from matplotlib.backend_bases import MouseEvent
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from collections import deque

class defaultstack(deque):
    def __init__(self, *args, **kwargs):
        super(defaultstack, self).__init__(*args)
        self.default = kwargs.get("default",None)
    def pop(self):
        return super(defaultstack, self).pop() if self else self.default
    def peek(self):
        return super(defaultstack, self).__getitem__(-1) if self else self.default


class FigCanvas(FigureCanvasWxAgg):
    """
    Define a basic figure canvas with a single axes. Contains
    some basic functionality and a few monkey patches
    """
    def __init__(self, parent, id, figure=None, size=(7.0, 3.0), dpi=100):
        if figure==None:
            figure = Figure(size, dpi)
        super(FigCanvas, self).__init__(parent, id, figure)

        self.figure.set_edgecolor('black')
        self.figure.set_facecolor('white')
        self.SetBackgroundColour(wx.WHITE)
        self.axes = self.figure.add_axes((0.05,0.1,0.92,0.85))

        # monkey patch for middle button capture
        self.Bind(wx.EVT_MIDDLE_DOWN, self._onMiddleButtonDown)
        self.Bind(wx.EVT_MIDDLE_DCLICK, self._onMiddleButtonDown)
        self.Bind(wx.EVT_MIDDLE_UP, self._onMiddleButtonUp)

        self.mpl_connect('figure_enter_event', self.figure_enter_event)

        # keep a collection of painters
        self.painters = []
        # keep a track of the current selection mode
        self.selector = None

    def _xypos(self, evt):
        return evt.GetX(), evt.GetY()

    def _inaxes(self, x, y):
        evt = MouseEvent('', self, x, self.figure.bbox.height - y)
        return self.axes.in_axes(evt)

    def transform_data(self, point):
        """ Convert canvas location to data location """
        x,y = point
        y = self.figure.bbox.height - y
        return self.axes.transData.inverted().transform_point((x,y))

    def transform_canvas(self, point):
        """ Convert data location to canvas location """
        x,y = self.axes.transData.transform_point(point)
        return x, self.figure.bbox.height - y

    def figure_enter_event(self, event):
        self.SetFocus()

    #Add middle button events
    def _onMiddleButtonDown(self, evt):
        """Start measuring on an axis."""
        x = evt.GetX()
        y = self.figure.bbox.height - evt.GetY()
        evt.Skip()
        self.CaptureMouse()
        super(FigCanvas,self).button_press_event(x, y, 2, guiEvent=evt)

    def _onMiddleButtonUp(self, evt):
        """End measuring on an axis."""
        x = evt.GetX()
        y = self.figure.bbox.height - evt.GetY()
        evt.Skip()
        if self.HasCapture(): self.ReleaseMouse()
        super(FigCanvas,self).button_release_event(x, y, 2, guiEvent=evt)

    # handle draw and paint events by calling .draw() on all the painters
    def _onPaint(self, evt):
        # call super to draw figure
        self.insideOnPaint = True
        super(FigCanvas, self)._onPaint(evt)
        self.insideOnPaint = False
        dc = wx.PaintDC(self)
        for painter in self.painters:
            painter.draw(dc)

    def clear_painters(self):
        """ Clear all registered painters, prior to trying to draw something new """
        for painter in self.painters:
            if painter.selector: painter.clear()
        self.selector = None
        self.draw()

    @property
    def selected(self):
        """ Return the first selector with a non-null value, or None if there is no active selection """
        for painter in self.painters:
            if painter.value: return painter
        return None

# borrowed from wxmpl
class Painter(object):
    """
    Painters encapsulate the mechanics of drawing values in a canvas. The only
    method subclasses need to implement is draw(), which is called whenever
    the object needs to be repainted. Default implementation stores current and previous
    values, and erases the previous value whenever a new value is supplied.

    @cvar PEN: C{wx.Pen} to use (defaults to C{wx.BLACK_PEN})
    @cvar BRUSH: C{wx.Brush} to use (defaults to C{wx.TRANSPARENT_BRUSH})
    @cvar FUNCTION: Logical function to use (defaults to C{wx.COPY})
    @cvar FONT: C{wx.Font} to use (defaults to C{wx.NORMAL_FONT})
    @cvar TEXT_FOREGROUND: C{wx.Colour} to use (defaults to C{wx.BLACK})
    @cvar TEXT_BACKGROUND: C{wx.Colour} to use (defaults to C{wx.WHITE})
    """

    PEN = wx.BLACK_PEN
    BRUSH = wx.TRANSPARENT_BRUSH
    FUNCTION = wx.COPY
    FONT = wx.NORMAL_FONT
    TEXT_FOREGROUND = wx.BLACK
    TEXT_BACKGROUND = wx.WHITE

    def __init__(self, view):
        self.view = view
        self.lastValue = None
        self.value = None

    def set(self, value):
        self.lastValue = self.value
        self.value = value
        self.draw()

    def clear(self):
        self.lastValue = self.value = None

    def draw(self, dc=None):
        if dc is None:
            dc = wx.ClientDC(self.view)

        dc.SetPen(self.PEN)
        dc.SetBrush(self.BRUSH)
        dc.SetFont(self.FONT)
        dc.SetTextForeground(self.TEXT_FOREGROUND)
        dc.SetTextBackground(self.TEXT_BACKGROUND)
        dc.SetLogicalFunction(self.FUNCTION)
        dc.BeginDrawing()

        if self.lastValue is not None:
            self.clearValue(dc, self.lastValue)
            self.lastValue = None

        if self.value is not None:
            self.drawValue(dc, self.value)

        dc.EndDrawing()

    def drawValue(self, dc, value):
        pass

    def clearValue(self, dc, value):
        pass

# convenience methods
def addCheckableMenuItems(menu, items):
    ''' Add a checkable menu entry to menu for each item in items. This
        method returns a dictionary that maps the menuIds to the
        items. '''
    idToItemMapping = {}
    for item in items:
        menuId = wx.NewId()
        idToItemMapping[menuId] = item
        menu.Append(menuId, str(item), kind=wx.ITEM_CHECK)
    return idToItemMapping


# Variables:
# End:
