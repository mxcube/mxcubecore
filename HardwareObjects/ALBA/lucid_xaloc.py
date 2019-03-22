from __future__ import print_function

import lucid2
import Image
import numpy as np


# TODO: Get rid of this module
def find_loop(filename, *args, **kwargs):
    im = Image.open(filename)
    out = im.transpose(Image.FLIP_LEFT_RIGHT)
    data = np.array(out)
    coords = lucid2.find_loop(data, *args, **kwargs)
    print(coords)
    x, y = coords[1:]
    if x > 0 and y > 0:
        x = 900 - x
        coords = ("Coord", x, y)
    return coords


if __name__ == '__main__':
    import sys
    print(find_loop(sys.argv[1]))
