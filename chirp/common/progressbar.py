# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Provides a text-based progress indicator that's based on consumption
from a queue.


Copyright (C) 2012 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2012-02-17
"""
from __future__ import absolute_import

class consumer(object):
    def __call__(self,queue,pool,stop_signal):
        """
        Consume data from the queue. If another thread changes stop_signal to True
        """
        for v in iter(queue.get,None):
            yield self.progress(v)
        # once we get a None, it means the queue is empty or the user
        # stopped the batch; in the latter case we have to join on the
        # child processes to make sure any remaining jobs finish, then clear
        # anything left in the queue
        for p in procs:
            p.join()
        try:
            while 1:
                v = queue.get_nowait()
                if v is not None: yield self.progress(v)
        except:
            pass

    def progress(self, value)
        import sys
        sys.stderr.write("[ %s completed 0 ]" % self.title)
        i = None
        for i,v in enumerate(iterable):
            if i % 10 == 0: sys.stderr.write("\r[ %s completed %d ]" % (self.title,i+1))
            yield v
        if i:
            sys.stderr.write("\r[ %s completed %d ]\n" % (self.title,i+1))

try:
    from progressbar import ProgressBar,Percentage,Bar
    class progressbar(object):
        def __init__(self,title=''):
            self.pbar = ProgressBar(widgets=[title,Percentage(),Bar()])
        def __call__(self,queue,pool,stop_signal)
            return self.pbar(iterable)

except ImportError:





# Variables:
# End:
