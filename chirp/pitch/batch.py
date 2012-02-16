# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Run pitch calculations as a batch job

Copyright (C) 2012 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2012-02-14
"""

import os, multiprocessing
from . import tracker

def run(files, config=None, workers=1, mask=True, skip=True):
    """
    Run a batch of files. Communication with the running jobs is
    accomplished via a shared stop signal and a queue, which is
    wrapped in a generator.

    @return stop_signal: set to True to cause all running processes to stop
            done_iter:   yields the name of jobs as they complete. Stops when
                         all jobs are done or all processes are terminated.
    """
    from ctypes import c_bool

    if config is not None and not os.path.exists(config):
        raise ValueError, "Configuration file doesn't exist"

    task_queue  = multiprocessing.Queue()
    done_queue  = multiprocessing.Queue()
    stop_signal = multiprocessing.Value(c_bool,False)
    #counter     = multiprocessing.Value(c_int,0)

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
                    #counter.value += 1
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
            #counter.value +=1
            done_queue.put(fname)
        done_queue.put(None)

    for f in files:
        if os.path.exists(f): task_queue.put(f)
    for i in xrange(workers):
        task_queue.put(None)

    procs = []
    for i in xrange(workers):
        p = multiprocessing.Process(target=_job)
        p.daemon = True
        p.start()
        procs.append(p)

    def _consumer():
        for v in iter(done_queue.get,None):
            yield v
        # once we get a None, it means the queue is empty or the user
        # stopped the batch; in the latter case we have to join on the
        # child processes to make sure any remaining jobs are cleared
        for p in procs:
            p.join()
        try:
            while 1:
                v = done_queue.get_nowait()
                if v is not None: yield v
        except:
            pass

    return stop_signal, _consumer()


# Variables:
# End:
