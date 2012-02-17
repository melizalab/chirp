# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
front end for performing pairwise comparisons.

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-08-30
"""

from . import methods, storage
from ..common.config import _configurable
from ..common.progressbar import progressbar
import multiprocessing


_scriptdoc = \
"""
ccompare.py [-c <config.cfg>] [-j workers] [-m METHOD]
            [--skip-completed] [--restrict]
            [-s STORAGE:LOCATION] [SIGNAL_PATH]

Perform pairwise comparisons between all signals in the directory
SIGNAL_PATH

-c   specify configuration file (see documentation for format)
-j   number of worker processes (default 1)
-m   specify method for comparing signals
-s   specify storage (format and location)

--skip-completed   skip completed calculations (database storage only)
--restrict         restrict to signals stored in database table 'signals'
"""

def load_data(storager, comparator, shm_manager, nworkers=1, cout=None, *args, **kwargs):
    """
    Load data into <shm_manager> using the iterate_signals() and
    load_signal() methods on <comparator>.

    Additional arguments (e.g. base location) are passed to
    iterate_signals()

    Returns a dictionary proxy keyed by id, and a list of id, locator tuples
    """
    from ctypes import c_bool

    tq = shm_manager.Queue()
    dq = shm_manager.Queue()
    d = shm_manager.dict()
    stop_signal = shm_manager.Value(c_bool,False)  # this is only used by the GUI

    def _load():
        for id,loc in iter(tq.get,None):
            if stop_signal.value: break
            try:
                d[id] = comparator.load_signal(loc)
                dq.put(id)
            except Exception, e:
                cout.write("** Error loading data from %s: %s" % (loc,e))

    for i in xrange(nworkers):
        p = multiprocessing.Process(target=_load)
        p.daemon = True
        p.start()

    for id,loc in storager.signals:
        tq.put((id,loc))

    for i in xrange(nworkers):
        tq.put(None)

    progress = progressbar('Loading signals: ')
    for i in progress(xrange(len(storager.signals)), stop_signal):
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
    from ctypes import c_bool
    task_queue = shm_manager.Queue()
    done_queue = shm_manager.Queue()
    stop_signal = shm_manager.Value(c_bool,False)  # this is only used by the GUI

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
    for ref,tgt in storager.pairs():
        task_queue.put((ref,tgt))
        nq +=1
    print >> cout, "** Number of comparisons: %d " % nq
    for i in xrange(nworkers):
        task_queue.put(None)

    if nq == 0:
        print >> cout, "** Task done; exiting"
    else:
        progress = progressbar('Comparing: ')
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

    opts,args = getopt.getopt(argv, 'hvc:m:s:j:',['skip-completed','restrict'])

    method = None
    store_descr = None
    store_options = dict()

    nworkers = 1
    for o,a in opts:
        if o == '-h':
            print _scriptdoc + '\n' + methods.make_scriptdoc() + '\n\n' + storage.make_scriptdoc()
            return -1
        elif o == '-v':
            print "cpitch version %s" % version
            return -1
        elif o == '-c':
            config.read(a)
        elif o == '-m':
            method = a
        elif o == '-s':
            store_descr = a
        elif o == '-j':
            nworkers = max(1,int(a))
        elif o == '--skip-completed':
            store_options['skip'] = True
        elif o == '--restrict':
            store_options['restrict'] = True

    if len(args)==0:
        signal_dir = os.getcwd()
    else:
        signal_dir = args[0]

    print >> cout, "* Program: ccompare"
    print >> cout, "** Version: %s" % version
    print >> cout, "* Input directory: %s" % signal_dir
    print >> cout, "* Number of workers: %d" % nworkers

    if method is None:
        print >> cout, "* Comparison method: None; aborting"
        print >> sys.stderr, "Please specify a comparison method. Options are %s" % ','.join(methods.names())
        return -1
    try:
        compare_class = methods.load(method)
        print >> cout, "* Comparison method: %s %s" % (method, compare_class)
    except ImportError, e:
        print >> cout, "* ERROR: %s" % e
        return -1

    comparator = compare_class(configfile=config)
    print >> cout, comparator.options_str()

    try:
        if store_descr is None or store_descr.startswith('file'):
            store_name, store_loc = 'file', cout
        else:
            store_name, store_loc = store_descr.split(':')
        storage_class = storage.load(store_name)
        print >> cout, "* Storage system: %s %s " % (store_name, storage_class)
        storager = storage_class(comparator, location=store_loc, signals=signal_dir, **store_options)
    except ImportError, e:
        print >> cout, "* ERROR: %s" % e
        return -1
    except ValueError:
        print >> cout, "* ERROR: Bad storage descriptor syntax (use STORAGE:LOCATION)"
        return -1

    print >> cout, storager.options_str()

    if storager.nsignals == 0:
        print >> cout, "** ERROR: No signals were specified (check restrict flag?)"
        return -1

    print >> cout, "* Loading signals:"
    mgr = multiprocessing.Manager()
    data = load_data(storager, comparator, mgr, nworkers=nworkers, cout=cout)
    storager.output_signals()
    if storager.nsignals == 0:
        print >> cout, "* ERROR: No signals loaded; aborting"
        return -2
    print >> cout, "* Running comparisons:"
    run_comparisons(storager, comparator, data, mgr, nworkers=nworkers)
    return 0

# Variables:
# End:
