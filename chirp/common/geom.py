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
            fp.write(repr(self))


    def load_patches(self, elements):
        """ Fill object with matplotlib objects """
        for patch in elements:
            trans = patch.get_data_transform().inverted()
            v = patch.get_verts()
            if isinstance(patch, patches.Rectangle):
                q = [x[0] for x in trans.transform(v[:2])]
                self.append(q)
            elif isinstance(patch, patches.Polygon):
                q = [(x,y) for x,y in trans.transform(v)]
                self.append(q)

    def __repr__(self):
        out = []
        for element in self:
            etype = self.element_type(element)
            if etype=='interval':
                out.append("INTERVAL (%s, %s)" % (str(element[0]), str(element[1])))
            elif etype=='poly':
                element = geometry.Polygon(element)
                out.append("%s" % element.wkt)
        return "\n".join(out)

    def __str__(self):
        return "<%s : %d element%s>" % (self.__class__.__name__, self.__len__(),
                                        "" if self.__len__()==1 else "s")

    @staticmethod
    def element_type(el):
        """ Return type of the element (currently poly or interval) """
        if isinstance(el,(tuple,list)):
            if isinstance(el[0],tuple):
                return 'poly'
            else:
                return 'interval'
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
                    out.append(tuple(poly.exterior.coords))
            return out


def discretize(poly,F,T):
    """
    Create binary array on an arbitrary grid that's True only for
    points inside poly.  This is slow; consider Cython.

    poly    a shapely Polygon
    F       an array of scalars defining the grid for frequency (row) coordinates
    T       an array of scalars defining the grid for time (column) coordinates

    Returns a boolean len(F) by len(T) array
    """
    from shapely import prepared
    from itertools import product
    polyprep = prepared.prep(poly)

    imask = nx.zeros((F.size,T.size,),dtype='bool')
    for (i,t),(j,f) in product(enumerate(T),enumerate(F)):
        p = geometry.Point(t,f)
        if polyprep.contains(p): imask[j,i] = True
    return imask


def rescale(points, bounds=None):
    """
    Rescale or move a geometry """
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

def fix_polygon(vertices):
    """ Fix an invalid (i.e. intersecting) polygon """
    # need to scale so that the tolerance values are matched across dimensions
    X,bounds = rescale(vertices)
    poly = geometry.Polygon(X)
    if poly.is_valid:
        return vertices
    print "Trying to simplify polygon"
    for tol in _tol_values:
        poly2 = poly.buffer(tol)
        if poly2.geom_type=='Polygon' and poly2.is_valid:
            return rescale(poly2.exterior.coords,bounds)[0]
    raise Exception, "Couldn't simplify polygon"

def convert_patch(patch):
    trans = patch.get_data_transform().inverted()
    v = patch.get_verts()
    return geometry.Polygon([(x,y) for x,y in trans.transform(v)])

def convert_polygon(*polys):
    """
    Generator yields exterior coordinates of poly; if poly is a
    MultiPolygon, yields exteriors of component polygons.
    """
    for poly in polys:
        if poly.geom_type=='Polygon':
            yield list(poly.exterior.coords)
        elif poly.geom_type=='MultiPolygon':
            for geom in poly.geoms:
                yield list(geom.exterior.coords)
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
