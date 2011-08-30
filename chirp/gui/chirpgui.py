# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Define spectrographic elements of acoustic signals

chirp [-c chirp.cfg] [<input.wav>]

Copyright (C) 2009-2011 Daniel Meliza <dmeliza@dylan.uchicago.edu>
"""

from __future__ import division
import os,sys
import wx
import numpy as nx
from ..common import geom, audio, config, plg
from .wxcommon import *
from .TSViewer import RubberbandPainter
from .SpecViewer import SpecViewer
from .DrawMask import DrawMask, PolygonPainter
from .PitchOverlayMixin import PitchOverlayMixin

from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Polygon
from matplotlib import cm

from glob import glob

spec_methods = ['hanning','tfr']
colormaps = ['jet','Greys','hot']
_el_ext = geom.elementlist.default_extension
_pitch_ext = plg._default_extension

default_cfg = os.path.join(os.environ['HOME'],".chirp.cfg")

# checklist control
from wx.lib.mixins.listctrl import CheckListCtrlMixin, ListCtrlAutoWidthMixin
class CheckListCtrl(wx.ListCtrl, CheckListCtrlMixin, ListCtrlAutoWidthMixin):
    def __init__(self, parent, frame=None):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT | wx.SUNKEN_BORDER)
        CheckListCtrlMixin.__init__(self)
        ListCtrlAutoWidthMixin.__init__(self)
        self.frame = frame or parent

    @property
    def selected(self):
        return [i for i in xrange(self.GetItemCount()) if self.GetItemState(i, wx.LIST_STATE_SELECTED)]

    @property
    def checked(self):
        return [i for i in xrange(self.GetItemCount()) if self.IsChecked(i)]

    def add_selection(self, *values):
        """ Add values to the list """
        ncol = self.GetColumnCount()
        assert len(values) >= ncol, "Not enough values for add_selection"
        idx = self.InsertStringItem(sys.maxint, str(values[0]))
        for i in range(1,ncol):
            self.SetStringItem(idx, i, values[i])
        self.CheckItem(idx)
        return idx

    # don't see a way to do this with event bindings, so we pass the call up to the app
    def OnCheckItem(self, index, flag):
        self.frame.OnCheckItem(index, flag)


class SpecPicker(SpecViewer, DrawMask, PitchOverlayMixin):
    """ Combines TSViewer and DrawMask into a super magical class """

    _element_color = 'g'
    _element_lw_unselected = 1
    _element_lw_selected = 5

    def __init__(self, parent, id, figure=None, configfile=None):
        super(SpecPicker, self).__init__(parent, id, figure, configfile)
        PitchOverlayMixin.__init__(self, configfile)
        self.list = parent.GetParent().list
        self.selections = []
        self.trace_h = []
        self.set_colormap(self.handler.colormap)

    def on_key(self, event):
        """
        's': mark current selection
        'p': play current selection
        """
        if event.key=='s':
            painter = self.selected
            if isinstance(painter, RubberbandPainter):
                self.add_interval(painter.value)
            elif isinstance(painter, PolygonPainter):
                self.add_polygon(geom.vertices_to_polygon(painter.value))
        elif event.key=='p' and self.handler.signal is not None and hasattr(io,'play_wave'):
            if isinstance(self.selected, RubberbandPainter):
                tlim = self.selected.value
            else:
                tlim = self.axes.get_xlim()
            i0,i1 = (int(x*self.handler.Fs) for x in tlim)
            audio.play_wave(self.handler.signal[i0:i1], self.handler.Fs)
        else:
            super(SpecPicker, self).on_key(event)

    def add_interval(self, value):
        """ Plot an interval using a rectangle """
        t1,t2 = min(value),max(value)
        r = Rectangle((t1, self.axes.dataLim.ymin), t2-t1, self.axes.dataLim.height,
                      ec='k', lw=self._element_lw_unselected, fc=self.element_color, alpha=0.3)
        self.selections.append(r)
        self.axes.add_patch(r)
        return self.list.add_selection('','interval','%3.2f' % t1, '%3.2f' % t2)

    def add_polygon(self, poly):
        """
        Add a polygon patch to the spectrogram.  Only the exterior of
        the polygon is used (for now).
        """
        p = Polygon(nx.asarray(poly.exterior.coords), closed=True,
                    ec='k', lw=self._element_lw_unselected, fc=self.element_color, alpha=0.3)
        self.selections.append(p)
        self.axes.add_patch(p)
        bounds = poly.bounds
        return self.list.add_selection('','spectrotemporal',"%3.2f" % bounds[0], "%3.2f" % bounds[2],)

    def delete_selection(self, *index):
        """ Removes elements from the underlying list, since we have access to it """
        for i in reversed(sorted(index)):
            p = self.selections.pop(i)
            p.remove()
            self.list.DeleteItem(i)

    def get_selected(self):
        return list(i for i,p in enumerate(self.selections) if p.get_lw() > self._element_lw_unselected)
    def set_selected(self, selections):
        for i,p in enumerate(self.selections):
            if i in selections:
                p.set_lw(self._element_lw_selected)
            else:
                p.set_lw(self._element_lw_unselected)

    def get_element_color(self):
        return self._element_color
    def set_element_color(self, value):
        if value==self._element_color: return
        self._element_color = value
        for p in self.selections:
            p.set_facecolor(value)
    element_color = property(get_element_color, set_element_color)

    def set_colormap(self, value):
        if value=='Greys':
            self.polygon.PEN = wx.BLACK_PEN
            self.element_color = 'g'
        elif value in ('hot','jet'):
            self.polygon.PEN = wx.WHITE_PEN
            self.element_color = 'w'
        self.handler.colormap = value

    def clear(self):
        self.selections = []
        self.remove_trace()
        self.axes.clear()
        self.handler.image = None


class ChirpGui(wx.Frame):
    """ The main frame of the application """
    dpi = 100

    def __init__(self, title='chirp', size=(1000,350), configfile=None):
        super(ChirpGui, self).__init__(None, -1, title, size=size)
        # load configuration file if one's supplied
        self.configfile = config.configoptions(configfile)
        self.create_menu()
        self.create_main_panel()
        self.filename = None

    def create_menu(self):
        self.menubar = wx.MenuBar()

        menu_file = wx.Menu()
        m_open = menu_file.Append(-1, "&Open File...\tCtrl-O", "Open File...")
        m_next_file = menu_file.Append(-1, "&Next File\tCtrl-N", "Next File")
        m_prev_file = menu_file.Append(-1, "Previous File\tCtrl-B", "Previous File")
        m_save = menu_file.Append(-1, "&Save Elements\tCtrl-S", "Save Elements")
        m_save_params = menu_file.Append(-1, "Save Parameters", "Save Params")
        m_exit = menu_file.Append(-1, "E&xit\tCtrl-X", "Exit")
        self.Bind(wx.EVT_MENU, self.on_open, m_open)
        self.Bind(wx.EVT_MENU, self.on_next_file, m_next_file)
        self.Bind(wx.EVT_MENU, self.on_prev_file, m_prev_file)

        self.Bind(wx.EVT_MENU, self.on_save, m_save)
        self.Bind(wx.EVT_MENU, self.on_save_params, m_save_params)
        self.Bind(wx.EVT_MENU, self.on_exit, m_exit)

        menu_edit = wx.Menu()
        m_copy_name = menu_edit.Append(-1, "Copy &Recording Name\tCtrl-R", "Copy Recording Name")
        self.Bind(wx.EVT_MENU, self.on_copy_name, m_copy_name)

        menu_analysis = wx.Menu()
        m_pitch = menu_analysis.Append(-1, "Calculate &Pitch\tShift-Ctrl-P", "Calculate Pitch")
        m_pitch_l = menu_analysis.Append(-1, "Load &Pitch Data\tCtrl-P", "Load Pitch Data")
        m_clear = menu_analysis.Append(-1, "&Clear Analysis Output\tCtrl-C", "Clear Analysis Output")
        self.Bind(wx.EVT_MENU, self.on_calc_pitch, m_pitch)
        self.Bind(wx.EVT_MENU, self.on_load_pitch, m_pitch_l)
        self.Bind(wx.EVT_MENU, self.on_clear_pitch, m_clear)

        self.menubar.Append(menu_file, "&File")
        self.menubar.Append(menu_edit, "&Edit")
        self.menubar.Append(menu_analysis, "&Analysis")
        self.SetMenuBar(self.menubar)

    def create_main_panel(self):
        mainPanel = wx.Panel(self, -1)
        vbox = wx.BoxSizer(wx.VERTICAL)

        panel = wx.Panel(mainPanel, -1)
        self.list = CheckListCtrl(panel, self)
        self.list.InsertColumn(0, 'Show', width=40)
        self.list.InsertColumn(1, 'Type', width=120)
        self.list.InsertColumn(2, 'Start')
        self.list.InsertColumn(3, 'End')
        # bind list selection
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelectItem, id=self.list.GetId())
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnSelectItem, id=self.list.GetId())

        # Create the mpl Figure and FigCanvas objects.
        fig = Figure((8.0, 3.0), dpi=self.dpi)
        self.spec = SpecPicker(mainPanel, -1, fig, configfile=self.configfile)

        spec_controls = self.create_spec_controls(mainPanel)

        leftPanel = wx.Panel(panel, -1)
        sel = wx.Button(leftPanel, -1, 'Show All', size=(100, -1))
        des = wx.Button(leftPanel, -1, 'Hide All', size=(100, -1))
        fdel = wx.Button(leftPanel, -1, 'Delete', size=(100, -1))
        fmrg = wx.Button(leftPanel, -1, 'Merge', size=(100, -1))
        fsub = wx.Button(leftPanel, -1,  'Subtract', size=(100,-1))
        fspl = wx.Button(leftPanel, -1, 'Split', size=(100, -1))

        self.Bind(wx.EVT_BUTTON, self.OnSelectAll, id=sel.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnDeselectAll, id=des.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnDelete, id=fdel.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnMerge, id=fmrg.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnSubtract, id=fsub.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnSplit, id=fspl.GetId())


        # status bar
        self.status = wx.StatusBar(mainPanel, -1)

        # Layout
        vbox2 = wx.BoxSizer(wx.VERTICAL)
        vbox2.Add(sel, 0, wx.TOP, 5)
        vbox2.Add(des, 0, wx.TOP, 2)
        vbox2.Add((3, 10))
        vbox2.Add(fdel,0, wx.TOP, 2)
        vbox2.Add(fmrg,0, wx.TOP, 2)
        vbox2.Add(fsub,0, wx.TOP, 2)
        vbox2.Add(fspl,0, wx.TOP, 2)
        leftPanel.SetSizer(vbox2)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(leftPanel, 0, wx.EXPAND | wx.RIGHT, 5)
        hbox.Add(self.list, 1, wx.EXPAND | wx.BOTTOM | wx.RIGHT | wx.TOP,5)
        panel.SetSizer(hbox)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.spec, 2, wx.LEFT | wx.TOP | wx.GROW)
        vbox.Add(spec_controls, 0, wx.EXPAND | wx.TOP, 5)
        vbox.Add(panel, 1, wx.EXPAND | wx.TOP, 5)
        vbox.Add(self.status, 0, wx.EXPAND)

        mainPanel.SetSizer(vbox)
        vbox.Fit(self)
        mainPanel.SetFocus()

    def create_spec_controls(self, parent):

        font = wx.SystemSettings_GetFont(wx.SYS_SYSTEM_FONT)

        controls = wx.Panel(parent, -1)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        txt = wx.StaticText(controls, -1, 'Spectrogram type:')
        txt.SetFont(font)
        hbox.Add(txt, 0, wx.RIGHT | wx.LEFT, 5)
        self.spec_method = wx.ComboBox(controls, -1, choices=spec_methods, style=wx.CB_READONLY)
        self.spec_method.SetValue(self.spec.handler.method)
        hbox.Add(self.spec_method, 1)

        txt = wx.StaticText(controls, -1, 'Window size (ms):')
        txt.SetFont(font)
        hbox.Add(txt, 0, wx.RIGHT | wx.LEFT, 5)
        self.win_size = wx.TextCtrl(controls, -1, str(self.spec.handler.window_len), style=wx.TE_PROCESS_ENTER)
        hbox.Add(self.win_size, 1)

        txt = wx.StaticText(controls, -1, 'Shift (ms):')
        txt.SetFont(font)
        hbox.Add(txt, 0, wx.RIGHT | wx.LEFT, 5)
        self.shift_size = wx.TextCtrl(controls, -1, str(self.spec.handler.shift), style=wx.TE_PROCESS_ENTER)
        hbox.Add(self.shift_size, 1)

        txt = wx.StaticText(controls, -1, 'Freq Range:')
        txt.SetFont(font)
        hbox.Add(txt, 0, wx.RIGHT | wx.LEFT, 5)
        frange = self.spec.handler.fpass
        self.f_low = wx.TextCtrl(controls, -1, str(frange[0]), style=wx.TE_PROCESS_ENTER)
        hbox.Add(self.f_low, 1, wx.RIGHT, 5)
        self.f_high = wx.TextCtrl(controls, -1, str(frange[1]), style=wx.TE_PROCESS_ENTER)
        hbox.Add(self.f_high, 1)

        txt = wx.StaticText(controls, -1, 'Color Range (dB):')
        txt.SetFont(font)
        hbox.Add(txt, 0, wx.RIGHT | wx.LEFT, 5)
        self.dynrange = wx.TextCtrl(controls, -1, str(self.spec.handler.dynrange), style=wx.TE_PROCESS_ENTER)
        hbox.Add(self.dynrange, 1)

        txt = wx.StaticText(controls, -1, 'Colormap:')
        txt.SetFont(font)
        hbox.Add(txt, 0, wx.RIGHT | wx.LEFT, 5)
        self.cmap = wx.ComboBox(controls, -1, choices=colormaps, style=wx.CB_READONLY)
        self.cmap.SetValue(self.spec.handler.colormap)
        hbox.Add(self.cmap, 1)

        controls.Bind(wx.EVT_COMBOBOX, self.OnSpecMethod, self.spec_method)
        controls.Bind(wx.EVT_TEXT_ENTER, self.OnSpecControl)  # bind all text events
        controls.Bind(wx.EVT_COMBOBOX, self.OnColorMap, self.cmap)

        controls.SetSizer(hbox)
        return controls

    def load_file(self, fname):
        fp = audio.wavfile(fname)
        sig,Fs = fp.read(), fp.sampling_rate / 1000
        self.filename = fname
        self.SetTitle(fname)
        self.spec.clear()
        self.list.DeleteAllItems()
        self.spec.plot_data(sig, Fs)
        el = self.load_elements(fname)
        if el: self.status.SetStatusText("Opened file %s; loaded %d elements" % (fname, len(el)))
        else: self.status.SetStatusText("Opened file %s" % fname)

    def load_elements(self, fname):
        el = None
        elfilename = os.path.splitext(fname)[0] + _el_ext
        if os.path.exists(elfilename):
            el = geom.elementlist.read(elfilename)
        if el:
            for elm in el:
                if isinstance(elm, geom.Polygon):
                    self.spec.add_polygon(elm)
                else:
                    self.spec.add_interval(elm)
            self.spec.draw()
        return el

    def get_selected(self,obj_type=None):
        objs = []
        for i in self.list.selected:
            p = self.spec.selections[i]
            if obj_type:
                if isinstance(p, obj_type): objs.append((i,p))
            else:
                objs.append((i,p))
        return objs

    def OnSelectAll(self, event):
        num = self.list.GetItemCount()
        for i in range(num):
            self.list.CheckItem(i)

    def OnDeselectAll(self, event):
        num = self.list.GetItemCount()
        for i in range(num):
            self.list.CheckItem(i, False)

    def OnCheckItem(self, index, flag):
        self.spec.selections[index].set_visible(flag)
        self.spec.draw()

    def OnSelectItem(self, event):
        sel = self.spec.get_selected()
        if not sel==self.list.selected:
            self.spec.set_selected(self.list.selected)
            self.spec.draw()

    def OnDelete(self, event):
        x = self.list.selected
        if x:
            self.spec.delete_selection(*x)
            self.spec.draw()
            self.status.SetStatusText("Deleted " + ', '.join(str(i+1) for i in x))

    def OnMerge(self, event):
        polys = self.get_selected(Polygon)
        if len(polys) < 2:
            self.status.SetStatusText("Select at least 2 spectrotemporal segments to merge.")
        else:
            i,p = zip(*polys)
            p1 = geom.merge_patches(p)
            self.spec.delete_selection(*i)
            # if polygons are disjoint, may return a multipolygon; split into separate segments
            new_elem = [self.spec.add_polygon(p) for p in geom.polygon_components(p1)]
            self.spec.draw()
            self.status.SetStatusText("Merged elements %s into %s" % (list(i for i,p in polys), new_elem))

    def OnSubtract(self, event):
        """ Subtract smaller polygon(s) from larger """
        polys = self.get_selected(Polygon)
        if len(polys) < 2:
            self.status.SetStatusText("Select at least 2 spectrotemporal segments.")
        else:
            ind,patches = zip(*polys)
            ipoly,new_poly = geom.subtract_patches(patches)
            self.spec.delete_selection(*ind)
            new_elem = [self.spec.add_polygon(p) for p in geom.polygon_components(new_poly)]
            self.status.SetStatusText("Subtracted %d elements from element %d" % (len(ind)-1,ind[ipoly]))


    def OnSplit(self, event):
        polys = self.get_selected(Polygon)
        if len(polys) != 2:
            self.status.SetStatusText("Select two spectrotemporal segments to split.")
        else:
            p1,p2 = (geom.convert_patch(p) for i,p in polys)
            if p1.disjoint(p2):
                self.status.SetStatusText("Segments do not intersect.")
            else:
                new_polys = geom.split_polygons(p1,p2)
                new_elem = [self.spec.add_polygon(p) for p in geom.polygon_components(*new_polys)]
                self.spec.delete_selection(polys[1][0],polys[0][0])
                self.spec.draw()
                self.status.SetStatusText("Split elements %s into %s" % (list(i for i,p in polys), new_elem))


    def OnSpecControl(self, event):
        # this is sort of cheap - just check all the values against the handler's values
        # and update the ones that have changed
        f_min = float(self.f_low.GetValue())
        f_max = float(self.f_high.GetValue())
        self.spec.handler.fpass = (f_min, f_max)
        self.spec.handler.window_len = float(self.win_size.GetValue())
        self.spec.handler.shift = float(self.shift_size.GetValue())
        self.spec.handler.dynrange = float(self.dynrange.GetValue())

    def OnColorMap(self, event):
        self.spec.set_colormap(self.cmap.GetValue())

    def OnSpecMethod(self, event):
        self.spec.handler.method = self.spec_method.GetValue()

    def on_open(self, event):
        fdlg = wx.FileDialog(self, "Select a file to open",
                             wildcard="WAV files (*.wav)|*.wav|Element files (*.ebl)|*.ebl|Pitch files (*.plg)|*.plg",
                             style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        val = fdlg.ShowModal()
        if val==wx.ID_OK:
            infile = os.path.join(fdlg.GetDirectory(), fdlg.GetFilename())
            file_type = os.path.splitext(infile)[1]
            if file_type==_el_ext:
                el = self.load_elements(infile)
                if el: self.status.SetStatusText("Loaded %d elements from %s" % (len(el), infile))
            elif file_type==_pitch_ext:
                try:
                    self.read_plg(infile)
                    self.status.SetStatusText("Loaded pitch data from %s" % infile)
                except Exception:
                    self.status.SetStatusText("Error reading pitch data from %s" % infile)
            else:
                self.load_file(infile)

    def _next_file(self, step=1):
        if self.filename is None: return
        pn,fn = os.path.split(self.filename)
        files = sorted(glob(pn + "/*.wav"))
        try:
            idx = files.index(self.filename)
        except ValueError:
            idx = -1

        idx += step
        if idx < 0 or idx >= len(files):
            return
        self.load_file(files[idx])

    def on_next_file(self, event):
        """ Open next file in current directory """
        self._next_file()

    def on_prev_file(self, event):
        """ Open previous file in current directory"""
        self._next_file(-1)


    def on_save(self, event):
        """ save elements to a file """
        # all of the patches are going to have 2D vertices
        el = patches_to_elist(self.spec.selections)
        if el:
            outfile = os.path.splitext(self.filename)[0] + _el_ext
            el.write(outfile)
            self.status.SetStatusText("Wrote %d elements to %s" % (len(el), outfile))


    def on_save_params(self, event):
        try:
            self.configfile.update('spectrogram',
                                   freq_range=(float(self.f_low.GetValue()), float(self.f_high.GetValue())),
                                   window_len=float(self.win_size.GetValue()),
                                   window_shift=float(self.shift_size.GetValue()),
                                   dynrange=float(self.dynrange.GetValue()),
                                   spec_method=self.spec_method.GetValue(),
                                   colormap=self.cmap.GetValue())
            self.configfile.write(default_cfg)
            self.status.SetStatusText("Saved default configuration to %s" % default_cfg)
        except Exception, e:
            self.status.SetStatusText("Error saving configuration: %s" % e)
            raise e

    def on_copy_name(self, event):
        if self.filename is None: return
        basename = os.path.splitext(os.path.split(self.filename)[-1])[0]
        clipdata = wx.TextDataObject()
        clipdata.SetText(basename)
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipdata)
        wx.TheClipboard.Close()

    def on_calc_pitch(self, event):
        """
        This function takes all the selected elements, or all of them
        if none are selected, and calculates the pitch for each.
        """
        elems = self.get_selected()
        if len(elems) < 1: elems = self.spec.selections
        if len(elems) < 1: elems = None
        else: elems = patches_to_elist(elems)
        try:
            self.status.SetStatusText("Calculating pitch...")
            wx.BeginBusyCursor()
            sig,Fs = self.spec.handler.signal, self.spec.handler.Fs
            self.spec.plot_calcd_pitch(sig, Fs, elems)
            self.status.SetStatusText("Calculating pitch...done")
        except Exception, e:
            self.status.SetStatusText("Error calculating pitch: %s" % e)
        finally:
            wx.EndBusyCursor()

    def on_load_pitch(self, event):
        if self.filename is None: return
        pitchfile = os.path.splitext(self.filename)[0] + _pitch_ext
        if os.path.exists(pitchfile):
            self.spec.plot_plg(pitchfile)
            self.status.SetStatusText("Loaded pitch data from %s" % pitchfile)
        else:
            self.status.SetStatusText("No pitch data for %s" % self.filename)

    def on_clear_pitch(self, event):
        self.spec.remove_trace()

    def on_exit(self, event):
        self.Destroy()

def patches_to_elist(elements):
    elist = geom.elementlist()
    for patch in elements:
        trans = patch.get_data_transform().inverted()
        v = patch.get_verts()
        if isinstance(patch, Rectangle):
            q = [x[0] for x in trans.transform(v[:2])]
            elist.append(q)
        elif isinstance(patch, Polygon):
            q = [(x,y) for x,y in trans.transform(v)]
            elist.append(geom.Polygon(q))
    return elist


def main(argv=None):
    import sys, getopt
    from ..version import version
    if argv is None:
        argv = sys.argv[1:]

    # this is the default location for the chirp config file
    configfile = default_cfg
    opts,args = getopt.getopt(argv,'hc:')
    for o,a in opts:
        if o =='-h':
            print __doc__
            return 0
        elif o =='-c':
            configfile=a

    print "Starting chirp version", version
    app = wx.PySimpleApp()
    app.frame = ChirpGui(configfile=configfile)
    if len(args) > 0:
        app.frame.load_file(args[0])
    app.frame.Show()
    app.MainLoop()

# Variables:
# End:
