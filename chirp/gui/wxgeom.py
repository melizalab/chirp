# -*- coding: iso-8859-1 -*-
# -*- mode: python -*-
"""
functions to convert between shapely geoms and matplotlib ones

Copyright (C) 2011 Daniel Meliza <dan // meliza.org>
Created 2011-08-31
"""
from matplotlib.patches import Rectangle, Polygon, PathPatch
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from numpy import asarray
from ..common import geom

# defines the type(s) of a polygon patch
polypatch = PathPatch

def interval_to_rect(x0, x1, y0, y1, **kwargs):
    """ Generate a mpl Rectangle patch, making sure coordinates are proprly ordered """
    x0,x1 = min(x0,x1),max(x0,x1)
    y0,y1 = min(y0,y1),max(y0,y1)
    return Rectangle((x0, y0), x1-x0, y1-y0, **kwargs)

def poly_to_patch(poly, **kwargs):
    """ Convert exterior of shapely polygon to an mpl patch """
    return Polygon(asarray(poly.exterior.coords), closed=True, **kwargs)

# this code is from http://sgillies.net/blog/1013/painting-punctured-polygons-with-matplotlib/
def ring_coding(ob):
    # The codes will be all "LINETO" commands, except for "MOVETO"s at the
    # beginning of each subpath
    from numpy import ones
    n = len(ob.coords)
    codes = ones(n, dtype=Path.code_type) * Path.LINETO
    codes[0] = Path.MOVETO
    return codes

def poly_to_path(poly, **kwargs):
    """ Convert shapely polygon to a set of paths. Supports holes. """
    from numpy import concatenate
    vertices = concatenate(
                    [asarray(poly.exterior)]
                    + [asarray(r) for r in poly.interiors])
    codes = concatenate(
                [ring_coding(poly.exterior)]
                + [ring_coding(r) for r in poly.interiors])
    pth = Path(vertices, codes)
    return PathPatch(pth, **kwargs)

def patch_to_poly(patch):
    """ Convert simple polygon patch to geometry """
    trans = patch.get_data_transform().inverted()
    v = patch.get_verts()
    return geometry.Polygon([(x,y) for x,y in trans.transform(v)])

def path_to_poly(pathpatch):
    """ Convert a pathpatch to a shapely polygon. """
    from numpy import nonzero, split
    path = pathpatch.get_path()
    # path.vertices are already in data coordinates
    ringstarts = nonzero(path.codes == Path.MOVETO)[0][1:]
    if len(ringstarts)==0:
        return geom.Polygon(path.vertices)
    else:
        rings = split(path.vertices, ringstarts, axis=0)
        return geom.Polygon(rings[0],rings[1:])


def patches_to_elist(elements):
    elist = geom.elementlist()
    for patch in elements:
        trans = patch.get_data_transform().inverted()
        v = patch.get_verts()
        if isinstance(patch, Rectangle):
            q = [x[0] for x in trans.transform(v[:2])]
            elist.append(q)
        elif isinstance(patch, Polygon):
            q = [(x,y) for x,y in trans.transform(v)]
            elist.append(geom.Polygon(q))
        elif isinstance(patch, PathPatch):
            elist.append(path_to_poly(patch))
    return elist


# Variables:
# End:
