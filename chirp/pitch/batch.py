# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Run pitch calculations as a batch job

Copyright (C) 2012 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2012-02-14
"""

import os, multiprocessing
from . import tracker

_scriptdoc = """\

Usage: cbatchpitch [-c <config.cfg>] [-m] [-s] [-w N] FILES

Calculates pitch of FILES.

-c specify configuration file
-m use masks if they exist
-s skip files that have already been analyzed
-w use N workers
"""

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
            if skip and os.path.exists(tname):
                tgt_mtime = os.stat(tname).st_mtime
                if tgt_mtime > os.stat(fname).st_mtime and \
                        (not os.path.exists(mname) or tgt_mtime > os.stat(mname).st_mtime):
                    dq.put((fname,1))
                    continue
            argv = []
            if config is not None:
                argv.extend(('-c',config))
            if mask and os.path.exists(mname):
                argv.extend(('-m',mname))
            argv.append(fname)

            ofp = open(tname,'wt')
            rv = tracker.cpitch(argv=argv, cout=ofp)
            dq.put((fname,rv))
            

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

def main(argv=None):
    import sys, getopt
    from ..version import version
    if argv is None:
        argv = sys.argv[1:]

    configfile = None
    mask = False
    skip = False
    workers = 1

    opts,args = getopt.getopt(argv, 'hvc:mw:s')
    if len(args) < 1:
        print _scriptdoc
        return -1
    
    for o,a in opts:
        if o == '-h':
            print _scriptdoc
            return -1
        elif o == '-v':
            print "cpitch version %s" % version
            return -1
        elif o == '-c':
            configfile = a
        elif o == '-m':
            mask = True
        elif o == '-s':
            skip = True
        elif o == '-w':
            workers = int(a)

    for f,rv in run(args, configfile, workers, mask, skip):
        if rv==1:
            print "Skipped %s (plg file is newer)" % f
        elif rv==0:
            print "Done analyzing %s" % f
        else:
            print "Error analyzing %s (error code %d)" % (f,rv)
        
        
# Variables:
# End:
