import logging
import sys


class CalculateFlux:
    def __init__(self, fname=None):
        self.FLUX = {}

    def init(
        self,
        fname="/users/blissadm/local/beamline_control/configuration/calibrated_diodes.dat",
    ):
        self.calib_array = self._load_flux_calibration(fname)

    def _load_flux_calibration(self, fname):
        try:
            f = open(fname)
            array = []
            nb_line = 0
            for line in f:
                if not line.startswith("#") and line.strip():
                    array.append(map(float, line.split()))
                    nb_line += 1
                else:
                    if line.startswith("#"):
                        # line = line[1:]
                        ll = line[1:].split()
                        self.labels = []
                        idx = []
                        for i in ll:
                            self.labels.append(i.lower())
                            idx.append(0)
            f.close()
        except IOError:
            logging.exception("Cannot read calibrated diodes file")
        self.FLUX = dict(zip(self.labels, idx))
        return array

    def calc_flux_coef(self, en):
        if en < 4:
            logging.exception("Cannot calculate flux - unknown energy")
            raise ValueError
        # calculations are made in eV, input might be in KeV
        if en < 1000:
            en *= 1000

        self.FLUX[self.labels[0]] = int(en)

        if en >= self.calib_array[0][0]:
            calib = self.calib_array[0][1:]
        elif en <= self.calib_array[-1][0]:
            calib = self.calib_array[-1][1:]
        else:
            calib = self._interpol(self.calib_array, int(en))

        for i in calib:
            self.FLUX[self.labels[calib.index(i) + 1]] = i

        return calib

    def _interpol(self, arr, val, debug=0):
        larr = []
        for i, vals in enumerate(arr):
            if abs(vals[0] - val) < 10:
                return vals[1:]

            larr.append(abs(vals[0] - val))
        min_index = larr.index(min(larr))
        x1 = arr[min_index][0]
        y1 = arr[min_index][1]
        try:
            z1 = arr[min_index][2]
        except Exception:
            pass
        if debug:
            print(arr[min_index])
        if x1 < val and min_index > 0:
            min_index -= 1
        elif x1 > val and min_index < len(arr) - 1:
            min_index += 1
        else:
            return None
        if debug:
            print(arr[min_index])
        x2 = arr[min_index][0]
        y2 = arr[min_index][1]
        try:
            z2 = arr[min_index][2]
        except Exception:
            pass
        bb = (y2 - y1) / (x2 - x1)
        aa = y1 - bb * x1
        try:
            dd = (z2 - z1) / (x2 - x1)
            cc = z1 - dd * x1
            return [aa + bb * val, cc + dd * val]
        except Exception:
            return aa + bb * val


if __name__ == "__main__":
    fl = CalculateFlux()
    fname = sys.argv[1]
    fl.init(fname)
    en = float(sys.argv[2]) * 1000
    ab = fl.calc_flux_coef(en)
    print(ab)
