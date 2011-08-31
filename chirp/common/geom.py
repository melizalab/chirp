# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
Geometry manipulation and input/output.

elementlist:          a collection of intervals and/or polygons
masker:               uses an elementlist to generate masks and split up a spectrogram
rasterize():          convert a polygon to a binary array on a grid

Copyright (C) 2010 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2010-02-02
"""
import numpy as nx
from shapely import geometry,wkt
from shapely.ops import cascaded_union
from shapely.geometry import Polygon  # for convenience
from .config import _configurable

class elementlist(list):
    """
    An elementlist is a collection of elements, which can be either
    intervals or polygons. Intervals are defined by a start and stop
    time point, whereas polygons are defined by a set of
    time-frequency vertices.  This class derives from list and defines
    some methods for storing and retrieval from files (which are
    basically collections of WKT strings)
    """
    __version__ = "1.2"
    default_extension = '.ebl'

    def write(self, filename):
        with open(filename, 'wt') as fp:
            fp.write("# element list version %s\n" % self.__version__)
            fp.write(str(self))


    def __str__(self):
        out = []
        for element in self:
            etype = self.element_type(element)
            if etype=='interval':
                out.append("INTERVAL (%s, %s)" % (str(element[0]), str(element[1])))
            elif etype=='poly':
                out.append("%s" % element.wkt)
        return "\n".join(out)


    def __repr__(self):
        return "<%s : %d element%s>" % (self.__class__.__name__, self.__len__(),
                                        "" if self.__len__()==1 else "s")

    @property
    def polys(self):
        """ Return a list of the polygons in the elementlist """
        return [p for p in self if self.element_type(p)=='poly']

    @property
    def multipolygon(self):
        """ Return a multipolygon with all the component polygons """
        return cascaded_union(self.polys)

    @property
    def intervals(self):
        """ Return a list of all the intervals in the elementlist """
        return [p for p in self if self.element_type(p)=='interval']
    
    @staticmethod
    def element_type(el):
        """ Return type of the element (currently poly or interval) """
        if isinstance(el,(tuple,list)):
            return 'interval'
        elif isinstance(el, geometry.Polygon):
            return 'poly'
        else:
            return None


    @classmethod
    def read(cls, filename):
        """ Read a file containing geometric elements """
        from distutils.version import StrictVersion
        with open(filename, 'rt') as fp:
            # check version number
            line = fp.readline()
            if line.startswith('#'):
                try:
                    fileversion = line.split()[-1]
                except ValueError, e:
                    raise ValueError, "Unable to parse version number of %s" % filename
            else:
                raise ValueError, "Unable to parse version number of %s" % filename
            if fileversion is None or StrictVersion(cls.__version__) != StrictVersion(fileversion):
                raise ValueError, \
                    "File version (%s) doesn't match class version (%s) " % (cls.__version__, fileversion)

            out = cls()
            for line in fp:
                if line.startswith('INTERVAL'):
                    out.append(eval(line[8:]))
                elif line.startswith('POLYGON'):
                    poly = wkt.loads(line)
                    out.append(poly)
            return out


class masker(_configurable):
    """
    Use a mask file to split a spectrogram into components. Each
    component is returned as a spectrogram with all the parts outside
    the mask set to zero, and the spectrogram trimmed so that no
    columns are all zeros.
    """
    options = dict(boxmask = False)

    def __init__(self, configfile=None, **kwargs):
        """
        Initialize the splitter, setting options:

        boxmask:  treat polygons as intervals and cut out all frequencies
        """
        self.readconfig(configfile, ('masker',))
        self.options.update(kwargs)

    def mask(self, elems, tgrid, fgrid):
        """
        Construct a mask composed of all the elements in an
        elementlist.
        """
        intervals = elems.intervals
        if self.options['boxmask']:
            imask = nx.zeros((fgrid.size,tgrid.size,),dtype='bool')
            intervals.extend((elem.bounds[0],elem.bounds[2]) for elem in elems.polys)
        else:
            imask = rasterize(elems.multipolygon, fgrid, tgrid)

        cols = nx.zeros(tgrid.size,dtype='bool')
        for i0,i1 in intervals:
            cols |= (tgrid >= i0) & (tgrid <= i1)
        imask[:,cols] = True
        return imask

    def split(self, spec, elems, tgrid, fgrid, cout=None):
        """
        For each element in elems, mask out the appropriate part of
        the spectrogram, yielding (starting column, spectrogram)

        spec:   any 2D array to be masked
        elems:  a list of elements understood by geom.elementlist.element_type()
        tgrid,fgrid:  the time/frequency grid of the spectrogram
        cout:   outputs diagnostic to this stream (default is stdout)
        """
        enum = 0
        for elem in elems:
            etype = elementlist.element_type(elem)
            mspec = spec
            if etype == 'interval':
                bounds = elem[:]
                print >> cout, "** Element %d, interval bounds (%.2f, %.2f)" % (enum, bounds[0], bounds[1])
                cols = nx.nonzero((tgrid >= bounds[0]) & (tgrid <= bounds[1]))[0]
            else:
                bounds = elem.bounds
                if self.options['boxmask']:
                    print >> cout, "** Element %d, polygon interval (%.2f, %.2f)" % (enum, bounds[0], bounds[2])
                    cols = nx.nonzero((tgrid >= bounds[0]) & (tgrid <= bounds[2]))[0]
                else:
                    print >> cout, "** Element %d, polygon mask with bounds %s" % (enum, bounds)
                    mask = rasterize(elem, fgrid, tgrid)
                    print >> cout, "*** Mask size: %d/%d points" % (mask.sum(),mask.size)
                    cols = nx.nonzero(mask.sum(0))[0]
                    mspec = (spec * mask)
            if cols.size < 3:
                print >> cout, "*** Element is too short; skipping"
            else:
                print >> cout, "*** Using spectrogram frames from %d to %d" % (cols[0], cols[-1])
                yield cols[0], mspec[:,cols]
            enum += 1


def rasterize(poly,F,T):
    """
    Create binary array on an arbitrary grid that's True only for
    points inside poly.  Uses a scanline algorithm.

    poly    a shapely Polygon
    F       an array of scalars defining the grid for frequency (row) coordinates
    T       an array of scalars defining the grid for time (column) coordinates

    Returns a boolean len(F) by len(T) array
    """
    imask = nx.zeros((F.size,T.size,),dtype='bool')
    # use a single numpy array for the scanline to avoid creating a lot of objects
    scanline = nx.array([[T[0],0.0],[T[-1],0.0]])
    sl = geometry.asLineString(scanline)
    for i,f in enumerate(F):
        scanline[:,1] = f
        ml = poly.intersection(sl)
        # several different types of objects may be returned from this
        if ml.geom_type == 'LineString': ml = [ml]
        for el in ml:
            # single points are tangents, drop them
            if el.geom_type != 'LineString': continue
            idx = slice(*T.searchsorted(el.xy[0]))
            imask[i,idx] = True
    return imask


def rescale(points, bounds=None):
    """
    Rescale or move a collection of points.  If bounds is None,
    calculates boundaries of existing polygon, rescales to a unit
    square, and returns rescaled points.  If bounds is not None, it
    does the same thing except that it rescales the points to the new
    bounds.

    Returns scaled points, old bounds
    """
    X = nx.asarray(points)
    x1,y1 = X.min(0)
    x2,y2 = X.max(0)
    X -= (x1,y1)
    X /= ((x2-x1,y2-y1))
    if bounds:
        x3,y3,x4,y4 = bounds
        X *= ((x4-x3), (y4-y3))
        X += (x3,y3)
    return X,(x1,y1,x2,y2)

_tol_values = nx.arange(0.01,1,0.01)

def vertices_to_polygon(vertices):
    """ Convert a a list of vertices to a (valid) shapely Polygon """
    # need to scale so that the tolerance values are matched across dimensions
    X,bounds = rescale(vertices)
    poly = geometry.Polygon(X)
    if poly.is_valid:
        return geometry.Polygon(vertices)
    print "Trying to simplify polygon"
    for tol in _tol_values:
        poly2 = poly.buffer(tol)
        if poly2.geom_type=='Polygon' and poly2.is_valid:
            return geometry.Polygon(rescale(poly2.exterior.coords,bounds)[0])
    raise Exception, "Couldn't simplify polygon"


def polygon_components(*polys):
    """
    Generator to split a heterogeneous list of Polygons and
    MultiPolygons into their component Polygons.
    """
    for poly in polys:
        if poly.geom_type=='Polygon':
            yield poly
        elif poly.geom_type=='MultiPolygon':
            for geom in poly.geoms:
                yield geom
        else:
            raise ValueError, "Object %s is not a polygon or multipolygon", poly

def split_polygons(p1, p2):
    return p1.difference(p2), p2.difference(p1), p1.intersection(p2)

def subtract_polygons(polys):
    largest = nx.argmax([p.area for p in polys])
    plargest = polys[largest]
    for i,p in enumerate(polys):
        if i==largest: continue
        plargest = plargest.difference(p)
    return largest,plargest # might be multipolygon

def merge_polygons(polys):
    return cascaded_union(polys)

def poly_in_interval(interval, poly):
    y = poly.centroid.y
    line = geometry.LineString(((interval[0],y),(interval[1],y)))
    return poly.intersects(line)


# Variables:
# End:
