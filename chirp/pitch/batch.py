# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Run pitch calculations as a batch job

Copyright (C) 2012 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2012-02-14
"""

import os, multiprocessing
from . import tracker

def max_workers():
    return multiprocessing.cpu_count()


def run(files, config=None, workers=1, mask=True, skip=True):
    """ Run the jobs, yielding completed filenames as jobs finish """
    if config is not None and not os.path.exists(config):
        raise ValueError, "Configuration file doesn't exist"

    def _job(tq,dq):
        for fname in iter(tq.get,None):
            basename = os.path.splitext(fname)[0]
            tname = basename + ".plg"
            mname = basename + ".ebl"

    task_queue = multiprocessing.Queue()
    done_queue = multiprocessing.Queue()
    for f in files:
        if os.path.exists(f):
            task_queue.put(f)
    for i in xrange(workers):
        task_queue.put(None)

    for i in xrange(workers):
        p = multiprocessing.Process(target=_job, args=(task_queue,done_queue))
        p.daemon = True
        p.start()

    for i in xrange(len(files)):
        yield done_queue.get()

# Variables:
# End:
