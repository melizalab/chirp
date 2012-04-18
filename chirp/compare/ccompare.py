# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
front end for performing pairwise comparisons.

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-08-30
"""

from .plugins import methods, storage
from ..common.progress import progressbar
import multiprocessing


_scriptdoc = \
"""
ccompare.py [-c <config.cfg>] [-j workers] [-m METHOD]
            [--skip-completed] [--restrict]
            [-s STORAGE::LOCATION] [SIGNAL_PATH]

Perform pairwise comparisons between all signals in the directory
SIGNAL_PATH

-c   specify configuration file (see documentation for format)
-j   number of worker processes (default 1)
-m   specify method for comparing signals
-s   specify storage (format and location)

--skip-completed   skip completed calculations (database storage only)
--restrict         restrict to signals stored in database table 'signals'
"""

def load_data(storager, comparator, shm_manager, consumer, nworkers=1, cout=None):
    """
    Load data into the shared memory manager.

    @param storager     uses the .signals property as a list of signals to load
    @param comparator   uses load_signal() method to read the data
    @param shm_manager  the shared memory manager
    @param consumer     an object that will pull done tasks off the done queue

    @returns a dictionary proxy keyed by id, and a list of id, locator tuples
    """
    from ctypes import c_bool

    task_queue = shm_manager.Queue()
    done_queue = shm_manager.Queue()
    data = shm_manager.dict()
    stop_signal = shm_manager.Value(c_bool,False)

    def _load(tq,dq,d):
        for id,loc in iter(tq.get,None):
            if stop_signal.value: break
            try:
                d[id] = comparator.load_signal(loc)
                dq.put(id)
            except Exception, e:
                cout.write("** Error loading data from %s: %s\n" % (loc,e))
        dq.put(None)

    for i in xrange(nworkers):
        p = multiprocessing.Process(target=_load, args=(task_queue, done_queue, data))
        p.daemon = True
        p.start()

    for id,loc in storager.signals:
        task_queue.put((id,loc))

    for i in xrange(nworkers):
        task_queue.put(None)

    consumer.start(done_queue, nworkers, stop_signal, njobs=len(storager.signals))

    return data


def run_comparisons(storager, comparator, shm_dict, shm_manager, consumer,
                    nworkers=1, cout=None):
    """
    Calculate comparisons between each pair of signals.

    @param storager    call store_results() to store results, pairs() to get pairs to run
    @param comparator  comparison object, needs to have compare()
    @param shm_dict    a shared dictionary, keyed by signal id
    @param nworkers    number of jobs to run in parallel

    """
    from ctypes import c_bool
    task_queue = shm_manager.Queue()
    done_queue = shm_manager.Queue()
    stop_signal = shm_manager.Value(c_bool,False)

    def _compare(tq,dq,d):
        for ref,tgt in iter(tq.get,None):
            if stop_signal.value: break
            refdata = d[ref]
            tgtdata = d[tgt]
            results = comparator.compare(refdata, tgtdata)
            dq.put((ref,tgt) + results)
        dq.put(None)

    for i in xrange(nworkers):
        p = multiprocessing.Process(target=_compare, args=(task_queue, done_queue, shm_dict))
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
        sgen = storager.store_results()
        consumer.start(done_queue, nworkers, stop_signal, njobs=nq, gen=sgen)
    return nq


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
        print >> cout, "* ERROR: bad method descriptor: %s" % e
        return -1

    comparator = compare_class(configfile=config)
    print >> cout, comparator.options_str()

    try:
        if store_descr is None:
            sparts = ('file', cout)
        else:
            sparts = store_descr.split('::')
        storage_class = storage.load(sparts[0])
        print >> cout, "* Storage system: %s %s " % (sparts[0], storage_class)
        storager = storage_class(comparator,
                                 location=sparts[1] if len(sparts)>1 else None,
                                 signals=signal_dir, **store_options)
    except ImportError, e:
        print >> cout, "* ERROR: bad storage descriptor: %s " % e
        return -1
    except ValueError, e:
        print >> cout, "* ERROR: bad storage descriptor: %s" % e
        return -1

    print >> cout, storager.options_str()

    if storager.nsignals == 0:
        print >> cout, "** ERROR: No signals were specified (check restrict flag?)"
        return -1

    print >> cout, "* Loading signals:"
    mgr = multiprocessing.Manager()
    progbar = progressbar(title='Loading signals:')
    data = load_data(storager, comparator, mgr, progbar, nworkers=nworkers, cout=cout)
    storager.output_signals()
    if storager.nsignals == 0:
        print >> cout, "* ERROR: No signals loaded; aborting"
        return -2
    print >> cout, "* Running comparisons:"
    progbar = progressbar(title='Comparing:')
    run_comparisons(storager, comparator, data, mgr, progbar, nworkers=nworkers)
    return 0

# Variables:
# End:
