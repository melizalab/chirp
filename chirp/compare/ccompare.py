# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
front end for performing pairwise comparisons.

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-08-30
"""

from . import methods, storage
from ..common.config import _configurable
import multiprocessing

try:
    from progressbar import ProgressBar,Percentage,Bar
    def progbar(title=''): return ProgressBar(widgets=[title,Percentage(),Bar()])
except ImportError:
    class progbar(object):
        def __init__(self,title=''):
            self.title = title
        def __call__(self,iterable):
            import sys
            sys.stderr.write("[ %s: completed 0 ]" % self.title)
            i = None
            for i,v in enumerate(iterable):
                if i % 10 == 0: sys.stderr.write("\r[ %s: completed %d ]" % (self.title,i+1))
                yield v
            if i:
                sys.stderr.write("\r[ %s: completed %d ]\n" % (self.title,i+1))

_scriptdoc = \
"""
ccompare.py [-c <config.cfg>] [-j workers] [-m METHOD]
            [-s STORAGE] [-l LOCATION] 

Perform pairwise comparisons using METHOD (%s).
Signals are loaded using STORAGE (%s) from LOCATION. Default is to
load all signals from current directory.

""" % (",".join(methods.names()), ",".join(storage.names()))

def pairs(items, symmetric):
    from itertools import product
    if symmetric:
        for i,v1 in enumerate(items):
            for v2 in items[i:]: yield v1,v2
    else:
        for v1,v2 in product(items,items): yield v1,v2

def load_data(storager, comparator, shm_manager, nworkers=1, cout=None, *args, **kwargs):
    """
    Load data into <shm_manager> using the iterate_signals() and
    load_signal() methods on <comparator>.

    Additional arguments (e.g. base location) are passed to
    iterate_signals()

    Returns a dictionary proxy keyed by id, and a list of id, locator tuples
    """
    tq = shm_manager.Queue()
    dq = shm_manager.Queue()
    d = shm_manager.dict()

    def _load(tq,dq):
        for id,loc in iter(tq.get,None):
            d[id] = comparator.load_signal(loc)
            dq.put(id)

    for i in xrange(nworkers):
        p = multiprocessing.Process(target=_load, args=(tq,dq))
        p.daemon = True
        p.start()

    for id,loc in storager.signals:
        tq.put((id,loc))

    for i in xrange(nworkers):
        tq.put(None)

    progress = progbar('Loading signals: ')
    for i in progress(xrange(len(storager.signals))):
        dq.get()

    return d


def run_comparisons(storager, comparator, shm_dict, shm_manager, nworkers=1, cout=None):
    """
    Calculate comparisons between each pair of signals.

    comparator:  comparison object, needs to have compare()
    shm_dict:    a shared dictionary, keyed by signal id
    nworkers:    number of jobs to run in parallel

    If cout is None, returns a list of tuples (ref, tgt, *stats) where
    stats is whatever gets returned by comparator.compare().  If not,
    outputs results to cout as a table.
    """
    task_queue = shm_manager.Queue()
    done_queue = shm_manager.Queue()

    def _compare(tq,dq):
        for ref,tgt in iter(tq.get,None):
            refdata = shm_dict[ref]
            tgtdata = shm_dict[tgt]
            results = comparator.compare(refdata, tgtdata)
            dq.put((ref,tgt) + results)

    for i in xrange(nworkers):
        p = multiprocessing.Process(target=_compare, args=(task_queue, done_queue))
        p.daemon = True
        p.start()

    print >> cout, "** Comparison is symmetric: %s" % comparator.symmetric
    nq = 0
    for ref,tgt in pairs(shm_dict.keys(), comparator.symmetric):
        task_queue.put((ref,tgt))
        nq +=1
    print >> cout, "** Number of comparisons: %d " % nq
    for i in xrange(nworkers):
        task_queue.put(None)

    progress = progbar('Comparing: ')
    storager.store_results(done_queue.get() for i in progress(range(nq)))


def main(argv=None, cout=None):
    import sys,os
    from ..version import version
    if argv is None:
        argv = sys.argv[1:]
    if cout is None:
        cout = sys.stdout

    import getopt
    from ..common.config import configoptions
    config = configoptions()

    opts,args = getopt.getopt(argv, 'hvc:m:s:j:l:')

    method = None
    store_name = 'file'
    store_loc = None

    nworkers = 1
    for o,a in opts:
        if o == '-h':
            print _scriptdoc
            return -1
        elif o == '-v':
            print "cpitch version %s" % version
            return -1
        elif o == '-c':
            config.read(a)
        elif o == '-m':
            method = a
        elif o == '-s':
            store_name = a
        elif o == '-j':
            nworkers = max(1,int(a))
        elif o == '-l':
            store_loc = a

    print >> cout, "* Program: ccompare"
    print >> cout, "** Version: %s" % version
    print >> cout, "* Input directory: %s" % os.getcwd()
    print >> cout, "* Number of workers: %d" % nworkers
    
    if method is None:
        print >> cout, "* Comparison method: None; aborting"
        print >> sys.stderr, "Please specify a comparison method. Options are %s" % ','.join(methods.names())
        return -1
    try:
        compare_class = methods.load(method)
        print >> cout, "* Comparison method: %s %s" % (method, compare_class)
    except ImportError, e:
        print >> cout, "* %s" % e
        return -1

    comparator = compare_class(configfile=config)
    print >> cout, comparator.options_str()

    try:
        storage_class = storage.load(store_name)
        print >> cout, "* Storage system: %s %s " % (store_name, storage_class)
    except ImportError, e:
        print >> cout, "* %s" % e
        return -1

    storager = storage_class(comparator, location=store_loc)
    print >> cout, storager.options_str()
    
    print >> cout, "* Loading signals:"
    mgr = multiprocessing.Manager()
    data = load_data(storager, comparator, mgr, nworkers=nworkers, cout=cout)
    storager.output_signals(cout)
    if storager.nsignals == 0:
        print >> cout, "* No signals loaded; aborting"
        return -2
    print >> cout, "* Running comparisons:"
    run_comparisons(storager, comparator, data, mgr,
                    nworkers=nworkers, cout=cout)
    return 0

# Variables:
# End:
