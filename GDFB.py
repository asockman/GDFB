''' GDFB.py - Geographic Data, For Breakfast????
geographic data serialization tools



code by agrippa kellum : june 2013
'''
__all__ = ['GeoGrid']

import numpy as np


class GeoGrid(dict):
    ''' A geographical grid (or 2d histogram) of coordinates

    self.rect, a latitude/longitude rectangle, is broken up into a grid
    of self.gridsize dimensions.

    When a lat/lon coordinate in the rectangle is searched for, the

    coordinates of the grid tile which contains it is found.

    All points are stored as [lat, lon] which can be seen as [y, x]
    however, gridsize is stored as x, y... unsure if thats for the best
    '''

    def __init__(self, rect, gridsize, default=0.0):

        bottomleft = (min(rect[0][0], rect[1][0]), min(rect[0][1], rect[1][1]))
        topright = (max(rect[0][0], rect[1][0]), max(rect[0][1], rect[1][1]))
        self.rect = (bottomleft, topright)
        self.default = default
        self.gridsize = (gridsize[0], gridsize[-1])
        self.tilesize = tuple(abs(rect[0][d] - rect[1][d]) / self.gridsize[d-1]
                              for d in (0, 1))

    @classmethod
    def from_img(cls, rect, file, divisor=255, f=float):
        ''' Creates a GeoGrid from a heatmap image and a latlon rect.
        (Only reads red value in pixel.)

        By default, will divide the red in each pixel by 255.
        Can divide by different values by changing the "divisor" keyword.
        '''
        from PIL import Image

        img = Image.open(file)
        mapimg = img.load()
        geogrid = cls(rect, img.size)

        for x in range(img.size[0]):
            for y in range(img.size[1]):
                # a different y value for the map is created, because the vertical
                # coordinate of an image increases from top to bottom, where
                # latitude increases from bottom to top
                mapy = img.size[1] - (y+1)
                geogrid.set_from_grid((y, x), mapimg[x, mapy][0]/divisor)

        return geogrid

    def get_tile_of_coord(self, coord):
        ''' Returns the tile that a coordinate is within '''
        tile = tuple(coord[d] - coord[d] % self.tilesize[d] +
                     self.rect[0][d] % self.tilesize[d] for d in (0, 1))
        return tile

    def __setitem__(self, coord, value):
        ''' Places coordinate in a tile before calling super().__setitem__ '''
        if value != self.default:
            key = self.get_tile_of_coord(coord)
            super().__setitem__(key, value)

    def __getitem__(self, coord):
        ''' Places coordinate in a tile before calling super().__getitem__ '''
        key = self.get_tile_of_coord(coord)
        return super().__getitem__(key)

    def __missing__(self, coord):
        return self.default

    def __grid_operation(operation):
        ''' decorator for performing an operation on all values in a GeoGrid '''
        def method(self, other):
            from copy import copy
            if self.rect != other.rect:
                raise ValueError("incompatible rectangles")
            geogrid = copy(self)

            for coord in other:
                operation(self, other, coord, geogrid)
            return geogrid
        return method

    @__grid_operation
    def __truediv__(self, other, coord, geogrid): geogrid[coord] /= other[coord]
    @__grid_operation
    def __add__(self, other, coord, geogrid): geogrid[coord] += other[coord]
    @__grid_operation
    def __sub__(self, other, coord, geogrid): geogrid[coord] -= other[coord]
    @__grid_operation
    def __mul__(self, other, coord, geogrid): geogrid[coord] *= other[coord]
    @__grid_operation
    def __pow__(self, other, coord, geogrid): geogrid[coord] **= other[coord]

    def set_from_grid(self, tile, value):
        ''' Sets the value of a tile using the GeoGrid's internal grid rather
        than a lat/lon coordinate.
        '''
        key = tuple((tile[d] * self.tilesize[d]) + self.rect[0][d]
                    for d in (0, 1))
        self[key] = value

    def yield_grid(self):
        ''' Convert GeoGrid back into a normal grid of points.

        Note: I'm pretty sure this is somewhat broken. Good luck!
        '''
        for tile in self:
            pos = tuple(int((tile[d] - self.rect[0][d]) / self.tilesize[d])
                        for d in (0, 1))
            yield pos, self[tile]

    def yield_values(self, coords=None):
        ''' Yields values of each point for analysis

        Optional:
            coords: specify the coordinates for which values are returned
            (default is simply all coords in the GeoGrid in no particular order)

        Example:
            >>> # creates a regression equation from the data of two maps,
            >>> # using curve fitting
            >>> import numpy
            >>> y = numpy.array(my_geo_grid_y.yield_values())
            >>> x = numpy.array(my_geo_grid_x.yield_values(my_geo_grid_y.keys()))
            >>> z = numpy.polyfit(x, y, 1)
            >>> p = numpy.poly1d(z)

            >>> # alternatively, the arrays could be used to make a thiel slope
            >>> import scipy
            >>> medslope = scipy.stats.mstats.theilslopes(y, x)
        '''
        if coords == None: coords = self.keys()
        for coord in coords:
            yield self[coord]


