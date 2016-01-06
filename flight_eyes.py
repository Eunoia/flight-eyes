""" Generates image over an area. """
import math
import os
import sys
import time

import requests
from PIL import Image
from shapely import geometry
from tiletanic.tilecover import cover_geometry
from tiletanic.tileschemes import WebMercator


def to_web_mercator(x_lon, y_lat):
    """ Converts lat, long into web mercator. Needed for tiletanic. """
    if abs(x_lon) >= 180 and abs(y_lat) > 90:
        print 'Invalid coordinate values for conversion'
        return None

    num = x_lon * 0.017453292519943295
    x = 6378137.0 * num
    a = y_lat * 0.017453292519943295
    x_mercator = x
    y_mercator = 3189068.5 * math.log((1.0 + math.sin(a)) / (1.0 - math.sin(a)))
    return (x_mercator, y_mercator)

def to_grid(tiles):
    """ Organizes a list of tiles into a matrix that can be iterated over. """
    tiles = sorted(tiles, key=lambda elem: elem.x)
    pivot = 1
    for idx, element in enumerate(tiles):
        if idx == 0:
            continue
        prior_element = tiles[idx-1]
        if element.x != prior_element.x:
            pivot = idx
            break

    return [tiles[i:i+pivot] for i in range(0, len(tiles), pivot)]

def zoom_from_altitude(altitude):
    """ converts altitude to zoom, really simplistic """
    return round(math.log(35200000 / abs(altitude)) / math.log(2))

def url(quad):
    """ creates the url for a given quadkey. """
    key = 'AuZ2rzQL4BFpZbThyMutLjCSwreiFEPg66lx4ZTsbWIP2fvhEupamMwphvkb82sb'
    root = 'http://ecn.t3.tiles.virtualearth.net/tiles'
    return '{}/a{}.jpeg?g=195&mkt=en-US&key={}'.format(root, quad, key)

def load_image_from_url(quad):
    """ Downloads image, and handles caching. """
    date = time.strftime("%Y-%m-%d").split('-')
    file_name = "quads/{}-{}-{}-{}.jpeg".format(quad, *date)
    if os.path.exists(file_name):
        image = Image.open(file_name)
    else:
        content = requests.get(url(quad)).content
        open(file_name, 'w').write(content)
        image = Image.open(file_name)

    return image

def tiles_over(coordinates, altitude=0):
    """ Finds all the tiles for an area """
    quads = []
    x_web_m, y_web_m = to_web_mercator(*coordinates)
    zoom = zoom_from_altitude(altitude)
    print zoom
    tiler = WebMercator()
    center_tile = tiler.tile(x_web_m, y_web_m, zoom)
    bounding_box = tiler.bbox(center_tile)
    tiles = cover_geometry(tiler, geometry.box(*bounding_box), zoom+2)

    for row in to_grid(tiles):
        quads.append([])
        for cell in row:
            quads[-1].append(tiler.quadkey(cell))

    print '\n'.join(['|'.join([str(q) for q in quads])])

    return quads

def download_tiles(quads, file_name):
    """ Generates larger image from tiles.  """
    width, height = (len(quads[0]), len(quads))
    full_size = Image.new('RGB', (width*256, height*256))
    print "QUAD SHAPE x: %d y: %d" % (width, height)

    for x_range in range(0, height):
        for y_range in range(0, width):
            print x_range, y_range
            safety_i = min(x_range, len(quads))
            safety_j = min(y_range, len(quads[0]))
            quad = quads[safety_i][safety_j]
            image = load_image_from_url(quad)
            full_size.paste(image, (x_range*256, y_range*256))

    full_size.save(file_name)

if __name__ == "__main__":
    # print len(sys.argv)
    if len(sys.argv) == 4:
        location = [float(i) for s in sys.argv]
    if len(sys.argv) == 3:
        location = (float(sys.argv[1]), float(sys.argv[2]), 30000)
    else:
        print "python flight_eyes.py lon lat altitude(defaults to 30,000 ft)"
        print "ex: python flight_eyes.py -122.39599 37.78858"
        sys.exit()

    lon, lat, alt = location
    tiles = tiles_over((lon, lat), alt)
    new_file_name = "background.jpg"
    download_tiles(tiles, new_file_name)
    wp = os.path.realpath(new_file_name)
    os.system(
        ('osascript -e \'tell application "Finder" to set '
         'desktop picture to POSIX file "{}"\'').format(wp, sep=2*'\n'))
