import logging
import math
import sys


class CalculateGaps:
    def __init__(self, energy):
        self.GAPS = {}

    def _calc_gaps(self, energy, undulator=None):
        config_file = "/users/blissadm/local/spec/userconf/undulators.dat"
        # config_file = "/tmp/undulators.dat"

        try:
            f = open(config_file)
            array = []
            nb_line = 0
            for line in f:
                if not line.startswith("#"):
                    array.append(line.split())
                    nb_line += 1
                else:
                    pass
        except IOError:
            logging.exception("Cannot read undulators file")

        if nb_line == 1:
            larr = map(float, array[2:])
            gg = self._calc_gap(energy, larr)
            if gg == 0:
                gg = array[1]
            self.GAPS[array[0]] = gg
        elif nb_line > 1:
            gap = {}
            p_gap = {}

            for i in array:
                larr = map(float, i[2:])
                gg = self._calc_gap(energy, larr)
                if gg == 0:
                    gg = int(i[1].strip("."))
                p_gap[i[0]] = gg
                if undulator is not None:
                    if i[0] == undulator:
                        gmax = int(i[1].strip("."))
                        if gg != 0:
                            gap[i[0]] = gg
                    else:
                        gap[i[0]] = int(i[1].strip("."))
                else:
                    gap[i[0]] = gg
            if undulator is not None:
                for i in array:
                    if i[0] != undulator and gap[undulator] == gmax:
                        larr = map(float, i[2:])
                        gg = self._calc_gap(energy, larr)
                        gap[i[0]] = gg
            gaps = gap.values()
            labels = gap.keys()
            if undulator is not None:
                for i in gaps:
                    if i == gmax and gaps.index(i) != 0:
                        gaps.reverse()
                        labels.reverse()
            self.GAPS = dict(zip(labels, gaps))
        else:
            logging.exception("Undulators file format error")
        print(p_gap)
        return self.GAPS

    def _calc_gap(self, energy, arr):
        gamma = 0.511 / 6040
        contst_en = 6.04
        dist = 31  # Calculate beam size at 31 m from source
        sigma_x = 0.000088
        sigma_y = 0.0000038
        sigma_h = 0.1334
        sigma_v = 0.0242
        const = 13.056 * arr[1] * 100 / pow(contst_en, 2)
        k2 = (math.pi / arr[1]) / 1000
        # Transform energy in wavelength
        h_over_e = 12.3984
        energy = h_over_e / energy
        target = energy / const
        nsols = 0

        k = [0] * 19
        g = [0] * 19
        pis = [0] * 19
        kout = [0] * 19
        iharm = [0] * 19
        hsiz = [0] * 19
        vsiz = [0] * 19
        # calculate gap now ...
        for i in range(1, 19, 2):
            targ = target * i
            targ = (targ - 1) * 2
            if targ > 0:
                k[i] = math.sqrt(targ)
                bo = k[i] / (arr[1] * 93.4)
                g[i] = -1 * math.log(bo / arr[2]) / k2
                # gap is not quite right - correction factors
                g[i] += arr[5]
                # Power [GeV] at 200 mA
                pis[i] = (
                    0.633 * (pow(contst_en, 2)) * (pow(bo, 2)) * 0.2 * arr[1] * arr[0]
                )
                if g[i] > arr[4]:
                    nsols += 1
                    g[nsols] = g[i]
                    pis[nsols] = pis[i]
                    kout[nsols] = k[i]
                    iharm[nsols] = i
                    consta = 1 + pow(k[i], 2) / 2
                    constb = consta / (2 * i * arr[0])
                    sigmarp = math.sqrt(constb) * gamma
                    # Answer is in rad, we want mrad
                    sigma_pv = (
                        2.35 * 1000 * math.sqrt(pow(sigmarp, 2) + pow(sigma_y, 2))
                    )
                    sigma_ph = (
                        2.35 * 1000 * math.sqrt(pow(sigmarp, 2) + pow(sigma_x, 2))
                    )
                    # Calculate beam sizes - these are in mcrions
                    hsiz[nsols] = math.sqrt(pow(sigma_h, 2) + pow(sigma_ph * dist, 2))
                    vsiz[nsols] = math.sqrt(pow(sigma_v, 2) + pow(sigma_pv * dist, 2))
        if nsols == 0:
            logging.info("Cannot CALCULATE GAPS")
            return 0
        return g[1]


if __name__ == "__main__":

    cg = CalculateGaps(float(sys.argv[1]))
    gg = cg._calc_gaps(float(sys.argv[1]), "u21d")
    print(gg)
