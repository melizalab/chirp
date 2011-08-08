# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
geometry manipulation and input/output

elementlist:           a collection of intervals and/or polygons
discretize():          convert a polygon to a binary array on a grid

Copyright (C) 2010 Daniel Meliza <dmeliza@dylan.uchicago.edu>
Created 2010-02-02
"""
import numpy as nx
from shapely import geometry,wkt
from shapely.geometry import Polygon  # for convenience

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
        with open(filename, 'rt') as fp:
            # check version number
            line = fp.readline()
            if line.startswith('#'):
                try:
                    version = float(line.split()[-1])
                    if version == 1.1: return cls.read_11(fp)
                except ValueError, e:
                    raise ValueError, "Unable to parse version number of %s" % filename
            out = cls()
            out.version = cls.__version__
            for line in fp:
                if line.startswith('INTERVAL'):
                    out.append(eval(line[8:]))
                elif line.startswith('POLYGON'):
                    poly = wkt.loads(line)
                    out.append(poly)
            return out


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

def convert_patch(patch):
    trans = patch.get_data_transform().inverted()
    v = patch.get_verts()
    return geometry.Polygon([(x,y) for x,y in trans.transform(v)])

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

def subtract_polygons(patches):
    polys = [convert_patch(p) for p in patches]
    largest = nx.argmax([p.area for p in polys])
    plargest = polys[largest]
    for i,p in enumerate(polys):
        if i==largest: continue
        plargest = plargest.difference(p)
    return largest,plargest # might be multipolygon

def poly_in_interval(interval, poly):
    y = poly.centroid.y
    line = geometry.LineString(((interval[0],y),(interval[1],y)))
    return poly.intersects(line)


# Variables:
# End:
