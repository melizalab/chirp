# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Provides a system for monitoring the progress of a multiprocess batch
job through a queue.  As worker processes or threads complete jobs,
they place objects into the queue. When they exit, they place None on
the queue.  The consumer thread removes objects from the queue,
optionally updating a progress indicator as it does so.  When it has
received a number of Nones equal to the number of workers, the job is
complete.  One advantage of this method is that the batch can be
prematurely terminated (typically through a shared variable) and the
consumer won't block indefinitely.

Copyright (C) 2012 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2012-02-17
"""
from __future__ import absolute_import

class consumer(object):
    """
    Base class for consuming objects from a queue. Subclasses should
    override __init__() to provide initialization (for instance,
    setting the number of jobs expected to be run), and progress() to
    provide status updates to the user.
    """
    
    def __call__(self,queue,nworkers,stop_signal):
        """
        Consume data from the queue. Workers should indicate when they
        terminate by placing None on the queue; this function will
        exit when it has received None from each of the
        processes.

        @param queue       the queue to poll
        @param nworkers    the number of workers adding values to the queue
        @param stop_signal a variable used to terminate the job (for consumers
                           linked to GUIs, for example)
        
        @yields values from the queue as they are retrieved.
        """
        while nworkers > 0:
            v = queue.get()
            if v is None:
                nworkers -= 1
            else:
                yield v
                self.progress()

    def progress(self):
        """ Called when a value is retrieved from the queue """
        pass
    
try:
    from progressbar import ProgressBar,Percentage,Bar
    class progressbar(consumer):
        """ Provides a text-based progress bar """
        def __init__(self,title=''):
            self.pbar = ProgressBar(widgets=[title,Percentage(),Bar()])
        def progress(self):
            return self.pbar(iterable)

except ImportError:
    import sys
    class progressbar(consumer):
        """ Provides a text-based progress bar """
        def __init__(self,title=''):
            self.title = title
        
        def progress(self):
            sys.stderr.write("[ %s completed 0 ]" % self.title)
            i = None
            for i,v in enumerate(iterable):
                if i % 10 == 0: sys.stderr.write("\r[ %s completed %d ]" % (self.title,i+1))
                yield v
            if i:
                sys.stderr.write("\r[ %s completed %d ]\n" % (self.title,i+1))



# Variables:
# End:
