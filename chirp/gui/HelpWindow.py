# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
Display help information in HTML dialogs
"""
from .. import version
from matplotlib import __version__ as mplver
import wx
import wx.html
import sys

vers = dict(wxver=wx.VERSION_STRING,
            mplver=mplver, **version.lib_versions())

about_txt = """
<p>This is Chirp version %(chirp)s, Copyright (C) 2012 Dan Meliza</p>

<br/>
<table border="0" cellpadding="0">
<tr>
<td colspan="2">Component libraries:</td>
</tr>
<tr><td>Python</td><td>%(python)s</td></tr>
<tr><td>wxpython</td><td>%(wxver)s</td></tr>
<tr><td>matplotlib</td><td>%(mplver)s</td></tr>
<tr><td>libtfr</td><td>%(libtfr)s</td></tr>
<tr><td>GEOS/shapely</td><td>%(geos)s</td></tr>
</table>
<br/>

<p><a href="http://github.com/dmeliza/chirp">Project Site</a></p>
""" % vers

help_txt = """
<table border="0" cellpadding="0">
<tr>
<td colspan="2">Spectrogram Navigation:</td>
</tr>
<tr><td>left mouse:</td><td>start drawing polygon; click to close</td></tr>
<tr><td>middle mouse:</td><td>drag to highlight temporal interval</td></tr>
<tr><td>right mouse:</td><td>drag to zoom to frequency range</td></tr>
<tr><td>down arrow:</td><td>zoom in to temporal interval</td></tr>
<tr><td>up arrow:</td><td>zoom out to previous temporal range</td></tr>
<tr><td>shift up arrow:</td><td>zoom out to previous freqency range</td></tr>
<tr><td>left arrow:</td><td>pan to earlier segment</td></tr>
<tr><td>right arrow:</td><td>pan to later segment</td></tr>
</table>
<p>

<table border="0" cellpadding="0">
<tr>
<td colspan="2">Element creation:</td>
</tr>
<tr><td>s:</td><td>create element using current selection (temporal interval or polygon)</td></tr>
<tr><td>x:</td><td>subtract current drawn polygon from all polygon elements</td></tr>
<tr><td>a:</td><td>add current drawn polygon to all polygon elements</td></tr>
<tr><td>p:</td><td>play audio of current selection (if supported)</td></tr>
</table>
"""


class HtmlWindow(wx.html.HtmlWindow):

    def __init__(self, parent, id, size=(600, 400)):
        wx.html.HtmlWindow.__init__(self, parent, id, size=size)
        if "gtk2" in wx.PlatformInfo:
            self.SetStandardFonts()

    def OnLinkClicked(self, link):
        wx.LaunchDefaultBrowser(link.GetHref())


class AboutBox(wx.Dialog):
    def __init__(self, parent=None, title='', text=''):
        wx.Dialog.__init__(self, parent, -1, title,
                           style=wx.DEFAULT_DIALOG_STYLE | wx.THICK_FRAME | wx.RESIZE_BORDER)
        hwin = HtmlWindow(self, -1, size=(400, 200))
        hwin.SetPage(text)
        btn = hwin.FindWindowById(wx.ID_OK)
        irep = hwin.GetInternalRepresentation()
        hwin.SetSize((irep.GetWidth() + 25, irep.GetHeight() + 10))
        self.SetClientSize(hwin.GetSize())
        self.CentreOnParent(wx.BOTH)
        self.SetFocus()

# Variables:
# End:
