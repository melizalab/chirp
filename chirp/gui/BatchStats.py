# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
Dialog for calculating batch pitch statistics

Copyright (C) 2012 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2012-02-13
"""

import os,wx,sys
from .BatchPitch import FileListBox
from ..misc import pitchstats
from ..common.config import configoptions

class BatchStats(wx.Frame):

    def __init__(self, parent=None):
        wx.Frame.__init__(self, parent, title="Pitch Statistics", size=(400,500),
                          style=wx.MINIMIZE_BOX|wx.CAPTION|wx.CLOSE_BOX|wx.NO_FULL_REPAINT_ON_RESIZE)
        self.create_main_panel()

    def create_main_panel(self):
        font = wx.SystemSettings_GetFont(wx.SYS_SYSTEM_FONT)
        mainPanel = wx.Panel(self, -1)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # file list
        txt = wx.StaticText(mainPanel, -1, 'Select files to analyze:')
        txt.SetFont(font)
        vbox.Add(txt, 0, wx.LEFT|wx.RIGHT|wx.TOP, 5)
        self.file_list = FileListBox(mainPanel, -1, wildcard="PLG files (*.plg)|*.plg")
        vbox.Add(self.file_list, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, 5)

        # config file
        txt = wx.StaticText(mainPanel, -1, 'Select configuration file:')
        txt.SetFont(font)
        vbox.Add(txt, 0, wx.ALL, 5)

        self.config = wx.FilePickerCtrl(mainPanel, -1,
                                        message="Select configuration file",
                                        wildcard="CFG files (*.cfg)|*.cfg",
                                        style = wx.FLP_OPEN|wx.FLP_FILE_MUST_EXIST|wx.FLP_USE_TEXTCTRL)
        vbox.Add(self.config,0,wx.EXPAND|wx.LEFT|wx.RIGHT,5)


        # output file
        txt = wx.StaticText(mainPanel, -1, 'Select output file:')
        txt.SetFont(font)
        vbox.Add(txt, 0, wx.LEFT|wx.RIGHT|wx.TOP, 5)
        self.outfile = wx.FilePickerCtrl(mainPanel, -1,
                                         message="Select output file",
                                         wildcard="CSV files (*.csv)|*.csv",
                                        style = wx.FLP_SAVE|wx.FLP_OVERWRITE_PROMPT|wx.FLP_USE_TEXTCTRL)
        vbox.Add(self.outfile,0,wx.EXPAND|wx.LEFT|wx.RIGHT,5)

        # run button; status bar; cancel
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_start = wx.Button(mainPanel,wx.ID_OK,'Start', size=(100,-1))
        self.btn_cancel = wx.Button(mainPanel,wx.ID_CANCEL,'Close', size=(100,-1))
        self.Bind(wx.EVT_BUTTON, self.on_start, id=self.btn_start.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_cancel, id=self.btn_cancel.GetId())
        hbox.Add(self.btn_start,0,wx.RIGHT,5)
        hbox.Add(self.btn_cancel)
        vbox.Add(hbox,0,wx.ALIGN_RIGHT|wx.ALL,5)

        self.status = wx.StatusBar(mainPanel, -1)
        vbox.Add(self.status, 0, wx.EXPAND)

        mainPanel.SetSizer(vbox)

    def on_start(self, event):
        # load data from controls. I wind up duplicating a lot
        # of stuff in ccompare.main, unfortunately
        files = self.file_list.files
        nfiles = len(files)
        if len(files)==0:
            self.status.SetStatusText("No files selected")
            return
        out   = self.outfile.GetPath()
        if len(out)==0:
            self.status.SetStatusText("No output file selected")
            return
        if not os.path.isabs(out):
            out = os.path.join(os.path.split(files[0])[0], out)
        cfg   = self.config.GetPath()
        if len(cfg)==0:
            cfg = None

        # load classes
        summarizer = pitchstats.summary(cfg)
        self.status.SetStatusText("Writing statistics to %s" % out)
        wx.BeginBusyCursor()
        with open(out,'wt') as fp:
            try:
                summarizer.summarize(files, fp, delim=',')
                self.status.SetStatusText("Finished writing statistics to %s" % out)
            except Exception, e:
                self.status.SetStatusText("Error calculating statistics: %s" % e)
        wx.EndBusyCursor()

    def on_cancel(self, event):
        self.Destroy()


def test():

    app = wx.PySimpleApp()
    app.frame = BatchStats()
    app.frame.Show()

# Variables:
# End:
