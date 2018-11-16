import sys


class GetStaticParameters:
    def __init__(self, element, edge):
        self.element = element
        self.edge = edge
        config_file = "/users/blissadm/local/spec/userconf/EdgeScan.dat"
        # config_file = "EdgeScan.dat"
        self.STATICPARS_DICT = {}
        self.STATICPARS_DICT = self._readParamsFromFile(config_file)

    def _readParamsFromFile(self, config_file):
        try:
            f = open(config_file)
            array = []
            for line in f:
                if not line.startswith("#"):
                    array.append(line.split())
                else:
                    pass
        except:
            return []
        else:
            larr = []
            for k in range(len(array)):
                if self.element == array[k][1] and self.edge[0] == array[k][2]:
                    larr = map(float, array[k][3:13])
                    larr.append(float(array[k][17]))
            if self.edge == "K":
                to_delete = [1, 2, 3, 4, 5, 6, 7]
            else:
                try:
                    if int(self.edge[1]) == 1:
                        to_delete = [0, 1, 2, 4, 5, 6, 7]
                    elif int(self.edge[1]) == 2:
                        to_delete = [0, 1, 2, 3, 5, 6, 7]
                    else:
                        to_delete = [0, 1, 2, 3, 4, 6, 7]
                except:
                    to_delete = [0, 1, 2, 3, 4, 6, 7]
            for ii in sorted(to_delete, reverse=True):
                del larr[ii]

            static_pars = {}
            larr[0] /= 1000
            static_pars["edgeEnergy"] = larr[0]
            static_pars["startEnergy"] = larr[0] - 0.05
            static_pars["endEnergy"] = larr[0] + 0.05
            static_pars["findattEnergy"] = larr[0] + 0.03
            static_pars["remoteEnergy"] = larr[0] + 1
            static_pars["eroi_min"] = larr[1]
            static_pars["eroi_max"] = larr[2]

            return static_pars


if __name__ == "__main__":

    if len(sys.argv) != 3:
        print "Usage: element edge"
        sys.exit(0)

    cg = GetStaticParameters(sys.argv[1], sys.argv[2])
    print cg.STATICPARS_DICT
    bb = cg.STATICPARS_DICT
    bb["element"] = sys.argv[1]
    bb["edge"] = sys.argv[2]
    print bb
