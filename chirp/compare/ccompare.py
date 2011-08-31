# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Front end for performing pairwise comparisons.

Copyright (C) 2011 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2011-08-30
"""

from . import methods
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
            for i,v in enumerate(iterable):
                if i % 10 == 0: sys.stderr.write("\r[ %s: completed %d ]" % (self.title,i+1))
                yield v
            sys.stderr.write("\r[ %s: completed %d ]\n" % (self.title,i+1))

_scriptdoc = \
"""
ccompare.py [-c <config.cfg>] [-j workers] [-m METHOD]

For each signal in the current directory, perform all pairwise
comparisons using METHOD. Supported methods include:

""" + "\n".join(methods.names())

def pairs(items, symmetric):
    from itertools import product
    if symmetric:
        for i,v1 in enumerate(items):
            for v2 in items[i:]: yield v1,v2
    else:
        for v1,v2 in product(items,items): yield v1,v2

def load_data(comparator, shm_manager, nworkers=1, cout=None, *args, **kwargs):
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
            d[id] = comparator.load_signal(id,loc)
            dq.put(id)

    for i in xrange(nworkers):
        p = multiprocessing.Process(target=_load, args=(tq,dq))
        p.daemon = True
        p.start()

    signals = comparator.list_signals(*args, **kwargs)
    for id,loc in signals:
        tq.put((id,loc))

    for i in xrange(nworkers):
        tq.put(None)

    progress = progbar('Loading signals: ')
    for i in progress(xrange(len(signals))):
        dq.get()

    return d, signals


def run_comparisons(comparator, shm_dict, shm_manager, nworkers=1, cout=None):
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
    if cout is None:
        return [done_queue.get() for i in progress(range(nq))]
    else:
        print >> cout, "** Results:"
        print >> cout, "ref\ttgt\t" + "\t".join(comparator.compare_stat_fields)
        for i in progress(range(nq)):
            print >> cout, "\t".join(("%s" % x) for x in done_queue.get())


def signal_table(signals):
    """ Generate a table of the id/locator assignments """
    out = "id\tlocation"
    for id,loc in signals:
        out += "\n%s\t%s" % (id,loc)
    return out


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
    
    opts,args = getopt.getopt(argv, 'hvc:m:j:')

    method = None
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
        elif o == '-j':
            nworkers = max(1,int(a))
            
    print >> cout, "* Program: cpitch"
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

    print >> cout, "* Loading signals:"
    mgr = multiprocessing.Manager()
    data,signals = load_data(comparator, mgr, nworkers=nworkers, cout=cout)
    print >> cout, signal_table(signals)
    print >> cout, "* Running comparisons:"
    run_comparisons(comparator,data,mgr,nworkers=nworkers, cout=cout)
    
# Variables:
# End:
