# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
Dialog for running batch pitch comparisons.

Copyright (C) 2012 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2012-02-13
"""

import os
import wx
import sys
import threading
from .events import EVT_STAGE, myEVT_STAGE, EVT_COUNT, BatchEvent, BatchConsumer
from ..compare import plugins, ccompare
from ..common.config import configoptions


class StagedBatchConsumer(BatchConsumer):
    def __init__(self, parent, descr=''):
        BatchConsumer.__init__(self, parent)
        self.descr = descr

    def __call__(self):
        evt = BatchEvent(myEVT_STAGE, -1, (self.njobs, self.descr))
        wx.PostEvent(self._parent, evt)
        BatchConsumer.__call__(self)


class CompareThread(threading.Thread):
    # This is a bit more complex because the operation has two stages
    def __init__(self, parent, storager, comparator, nworkers):
        self.parent = parent
        self.storager = storager
        self.comparator = comparator
        self.nworkers = nworkers
        self.mgr = ccompare.multiprocessing.Manager()
        self.consumer = None
        threading.Thread.__init__(self)

    def run(self):
        self.consumer = StagedBatchConsumer(self.parent, "Loading signals...")
        data = ccompare.load_data(self.storager, self.comparator, self.mgr, self.consumer, nworkers=self.nworkers,
                                  cout=sys.stderr)
        self.consumer()  # this will block
        self.storager.output_signals()

        self.consumer = StagedBatchConsumer(self.parent, "Comparing signals...")
        nq = ccompare.run_comparisons(self.storager, self.comparator, data, self.mgr, self.consumer,
                                      nworkers=self.nworkers, cout=sys.stderr)
        if nq > 0:
            self.consumer()
        evt = BatchEvent(myEVT_STAGE, -1, (None, "Operation completed"))
        wx.PostEvent(self.parent, evt)
        self.consumer = None

    def stop(self):
        if self.consumer:
            self.consumer.stop()


class BatchCompare(wx.Frame):

    _inactive_controls = ('filedir', 'config', 'nworkers', 'method', 'storage', 'storageloc', 'storage_pick',
                          'restrict', 'skipcompl', 'btn_start')

    def __init__(self, parent=None):
        wx.Frame.__init__(self, parent, title="Batch Comparison", size=(400, 400),
                          style=wx.MINIMIZE_BOX | wx.CAPTION | wx.CLOSE_BOX | wx.NO_FULL_REPAINT_ON_RESIZE)
        self.create_main_panel()
        self.batch_thread = None

    def create_main_panel(self):
        font = wx.SystemSettings_GetFont(wx.SYS_SYSTEM_FONT)
        mainPanel = wx.Panel(self, -1)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # file list
        txt = wx.StaticText(mainPanel, -1, 'Select directory of files to analyze:')
        txt.SetFont(font)
        vbox.Add(txt, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)

        self.filedir = wx.DirPickerCtrl(mainPanel, -1,
                                        message="Select a directory",
                                        style=wx.DIRP_DIR_MUST_EXIST | wx.DIRP_USE_TEXTCTRL)
        vbox.Add(self.filedir, 0, wx.EXPAND | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        # config file
        txt = wx.StaticText(mainPanel, -1, 'Select configuration file:')
        txt.SetFont(font)
        vbox.Add(txt, 0, wx.ALL, 5)

        self.config = wx.FilePickerCtrl(mainPanel, -1,
                                        message="Select configuration file",
                                        wildcard="CFG files (*.cfg)|*.cfg",
                                        style=wx.FLP_OPEN | wx.FLP_FILE_MUST_EXIST | wx.FLP_USE_TEXTCTRL)
        vbox.Add(self.config, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        # number of workers
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(mainPanel, -1, 'Number of processes to run:')
        txt.SetFont(font)
        hbox.Add(txt, 0, wx.ALIGN_CENTER)
        self.nworkers = wx.SpinCtrl(mainPanel, -1, size=(60, -1))
        self.nworkers.SetRange(1, ccompare.multiprocessing.cpu_count())
        self.nworkers.SetValue(1)
        hbox.Add(self.nworkers, 0, wx.LEFT, 5)
        vbox.Add(hbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        # comparison method
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(mainPanel, -1, 'Select comparison method:')
        txt.SetFont(font)
        hbox.Add(txt, 0, wx.ALIGN_CENTER)
        self.method = wx.Choice(mainPanel, -1, choices=plugins.methods.names())
        hbox.Add(self.method, 1, wx.LEFT, 5)
        vbox.Add(hbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        # storage method
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(mainPanel, -1, 'Select storage format:')
        txt.SetFont(font)
        hbox.Add(txt, 0, wx.ALIGN_CENTER)
        self.storage = wx.Choice(mainPanel, -1, choices=plugins.storage.names())
        hbox.Add(self.storage, 1, wx.LEFT, 5)
        vbox.Add(hbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        # output file
        txt = wx.StaticText(mainPanel, -1, 'Select storage location:')
        txt.SetFont(font)
        vbox.Add(txt, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.storageloc = wx.TextCtrl(mainPanel, -1)
        hbox.Add(self.storageloc, 1, wx.EXPAND | wx.RIGHT, 5)
        self.storage_pick = wx.Button(mainPanel, -1, "Browse")
        self.Bind(wx.EVT_BUTTON, self.on_pick_storage, id=self.storage_pick.GetId())
        hbox.Add(self.storage_pick, 0)
        vbox.Add(hbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        # Restrict to database?
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(mainPanel, -1, 'Restrict to files in database (database formats only):')
        txt.SetFont(font)
        hbox.Add(txt, 0, wx.ALIGN_CENTER)
        self.restrict = wx.CheckBox(mainPanel, -1)
        self.restrict.SetValue(0)
        hbox.Add(self.restrict, 0, wx.LEFT, 5)
        vbox.Add(hbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        # Skip completed pairs
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(mainPanel, -1, 'Skip completed pairs (database formats only):')
        txt.SetFont(font)
        hbox.Add(txt, 0, wx.ALIGN_CENTER)
        self.skipcompl = wx.CheckBox(mainPanel, -1)
        self.skipcompl.SetValue(0)
        hbox.Add(self.skipcompl, 0, wx.LEFT, 5)
        vbox.Add(hbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        # run button; status bar; cancel
        vbox.Add((-1, 10))
        txt = wx.StaticText(mainPanel, -1, 'Progress:')
        txt.SetFont(font)
        vbox.Add(txt, 0, wx.LEFT, 5)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.gauge = wx.Gauge(mainPanel, -1)
        hbox.Add(self.gauge, 1, wx.EXPAND)
        vbox.Add(hbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_start = wx.Button(mainPanel, wx.ID_OK, 'Start', size=(100, -1))
        self.btn_cancel = wx.Button(mainPanel, wx.ID_CANCEL, 'Close', size=(100, -1))
        self.Bind(wx.EVT_BUTTON, self.on_start, id=self.btn_start.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_cancel, id=self.btn_cancel.GetId())
        hbox.Add(self.btn_start, 0, wx.RIGHT, 5)
        hbox.Add(self.btn_cancel)
        vbox.Add(hbox, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.Bind(EVT_COUNT, self.on_count_update)
        self.Bind(EVT_STAGE, self.on_stage_update)

        self.status = wx.StatusBar(mainPanel, -1)
        vbox.Add(self.status, 0, wx.EXPAND)

        mainPanel.SetSizer(vbox)

    def on_pick_storage(self, event):
        # this will need to be more sophisticated for non-filesystem
        # storage
        fdlg = wx.FileDialog(self, "Select storage location",
                             wildcard="All files (*.*)|*.*",
                             style=wx.FD_SAVE)
        val = fdlg.ShowModal()
        if val == wx.ID_OK:
            base, ext = os.path.splitext(fdlg.GetFilename())
            if ext == '':
                storage_class = plugins.storage.load(self.storage.GetStringSelection())
                ext = storage_class._preferred_extension
            self.storageloc.SetValue(os.path.join(fdlg.GetDirectory(), base + ext))

    def on_start(self, event):
        # load data from controls. I wind up duplicating a lot
        # # of stuff in ccompare.main, unfortunately
        filedir = self.filedir.GetPath()
        if len(filedir) == 0:
            self.status.SetStatusText("No analyis directory selected")
            return
        store_loc = self.storageloc.GetValue()
        if len(store_loc) == 0:
            self.status.SetStatusText("No storage location selected")
            return

        config = configoptions()
        cfg   = self.config.GetPath()
        if len(cfg) > 0:
            config.read(cfg)
        store_options = dict()
        store_options['restrict']  = self.restrict.GetValue()
        store_options['skip']  = self.skipcompl.GetValue()
        nw    = self.nworkers.GetValue()

        # load classes
        compare_class = plugins.methods.load(self.method.GetStringSelection())
        storage_class = plugins.storage.load(self.storage.GetStringSelection())

        comparator = compare_class(configfile=config)
        storager = storage_class(comparator, location=store_loc, signals=filedir, **store_options)
        storager.write_metadata(comparator.options_str())
        storager.write_metadata(storager.options_str())

        # load the signals
        self._disable_interface()

        try:
            self.batch_thread = CompareThread(self, storager, comparator, nw)
            self.batch_thread.daemon = True
            self.batch_thread.start()
        except Exception, e:
            self._enable_interface()
            self.status.SetStatusText("Error: %s" % e)

    def on_count_update(self, event):
        value = event.GetValue()
        if value is not None:
            self.gauge.SetValue(value + 1)

    def on_stage_update(self, event):
        njobs, status = event.GetValue()
        self.status.SetStatusText(status)
        if njobs is not None:
            self.gauge.SetRange(njobs)
            self.gauge.SetValue(0)
        else:
            self.gauge.SetValue(self.gauge.GetRange())
            self._enable_interface()

    def on_cancel(self, event):
        if self.batch_thread is None or not self.batch_thread.is_alive():
            self.Destroy()
        else:
            # need to double-check
            dlg = wx.MessageDialog(self, """Are you sure you want to cancel?
Depending on the storage system, you may not
be able to resume progress""",
                                   "Confirm cancel", style=wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT)
            val = dlg.ShowModal()
            if val == wx.ID_YES:
                self.status.SetStatusText("Canceling batch after current jobs finish...")
                self.batch_thread.stop()
                wx.BeginBusyCursor()

    def _disable_interface(self):
        for ctrl in self._inactive_controls:
            getattr(self, ctrl).Disable()
        self.btn_cancel.SetLabel("Cancel")

    def _enable_interface(self):
        self.btn_cancel.SetLabel("Close")
        self.btn_cancel.Enable()
        wx.EndBusyCursor()
        for ctrl in self._inactive_controls:
            getattr(self, ctrl).Enable()


def test():

    app = wx.PySimpleApp()
    app.frame = BatchCompare()
    app.frame.Show()

# Variables:
# End:
