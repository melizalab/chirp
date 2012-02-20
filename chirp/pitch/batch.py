# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Run pitch calculations as a batch job

Copyright (C) 2012 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2012-02-14
"""

import os, multiprocessing
from . import tracker

def run(files, consumer, config=None, workers=1, mask=True, skip=True):
    """
    Run a batch of files. Communication with the running jobs is
    accomplished via the consumer argument.
    """
    from ctypes import c_bool

    if config is not None and not os.path.exists(config):
        raise ValueError, "Configuration file doesn't exist"

    task_queue  = multiprocessing.Queue()
    done_queue  = multiprocessing.Queue()
    stop_signal = multiprocessing.Value(c_bool,False)

    def _job():
        for fname in iter(task_queue.get,None):
            if stop_signal.value: break
            basename = os.path.splitext(fname)[0]
            tname = basename + ".plg"
            mname = basename + ".ebl"
            if skip and os.path.exists(tname):
                tgt_mtime = os.stat(tname).st_mtime
                if tgt_mtime > os.stat(fname).st_mtime and \
                        (not os.path.exists(mname) or tgt_mtime > os.stat(mname).st_mtime):
                    done_queue.put(fname)
                    continue
            argv = []
            if config is not None:
                argv.extend(('-c',config))
            if mask and os.path.exists(mname):
                argv.extend(('-m',mname))
            argv.append(fname)
            ofp = open(tname,'wt')
            rv = tracker.cpitch(argv=argv,cout=ofp)
            done_queue.put(fname)
        done_queue.put(None)

    for f in files:
        if os.path.exists(f): task_queue.put(f)
    for i in xrange(workers):
        task_queue.put(None)

    for i in xrange(workers):
        p = multiprocessing.Process(target=_job)
        p.daemon = True
        p.start()

    consumer.start(done_queue, workers, stop_signal, njobs=len(files))


# Variables:
# End:
