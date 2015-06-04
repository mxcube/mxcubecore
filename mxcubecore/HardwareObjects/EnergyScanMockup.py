import logging
import gevent
import time

from qt import *
from HardwareRepository.BaseHardwareObjects import Equipment

class EnergyScanMockup(Equipment):
    def init(self):
        self.ready_event = gevent.event.Event()

        self.scanData = [[8914.0, 165.3], [8914.9, 195.6], [8916, 205.941], 
                         [8917, 207.843], [8918, 199.605], [8919, 234.653],
                         [8920, 218.75],  [8921, 260.8], [8922.0, 274.704],
                         [8923.0, 297.0], [8924, 288.5], [8925, 306.931],
                         [8926.1, 318.8], [8927.01, 352.4], [8928.01, 367.589],
                         [8929.01, 422.772], [8930.01, 431.818]]
        self.scanInfo = {}
        self.scanInfo["startEnergy"] = self.scanData[0][1]
        self.scanInfo["endEnergy"] = self.scanData[-1][1] 
        self.scanInfo['endTime'] = time.strftime("%Y-%m-%d %H:%M:%S") 
        self.scanInfo["peakEnergy"] = 10
        self.scanInfo["inflectionEnergy"] = 10
        self.scanInfo["remoteEnergy"] = 10
        self.scanInfo["peakFPrime"] = 10
        self.scanInfo["peakFDoublePrime"] = 10
        self.scanInfo["inflectionFPrime"] = 10
        self.scanInfo["inflectionFDoublePrime"] = 10
        self.scanInfo["comments"] = "Simulation scan from EnergyScanMockup"

    def startEnergyScan(self, element, edge, directory, prefix,
                        session_id = None, blsample_id= None):
        self.emit('energyScanFinished', (self.scanInfo,))
        self.ready_event.set()


    def doChooch(self, elt, edge, scanArchiveFilePrefix, scanFilePrefix):
        chooch_graph_x = None
        chooch_graph_y1 = None
        chooch_graph_y2 = None

        return self.scanInfo["peakEnergy"], self.scanInfo["peakFDoublePrime"], \
               self.scanInfo["peakFPrime"], self.scanInfo["inflectionEnergy"], \
               self.scanInfo["inflectionFDoublePrime"], self.scanInfo["inflectionFPrime"], \
               self.scanInfo["remoteEnergy"], chooch_graph_x, \
               chooch_graph_y1, chooch_graph_y2, self.scanInfo["comments"] \

    def getCurrentEnergy(self):
        return 12


    def getCurrentWavelength(self):
        return 12


    # Elements commands
    def getElements(self):
        elements=[]
        try:
            for el in self["elements"]:
                elements.append({"symbol":el.symbol, "energy":el.energy})
        except IndexError:
            pass
        return elements


    # Mad energies commands
    def getDefaultMadEnergies(self):
        energies=[]
        try:
            for el in self["mad"]:
                energies.append([float(el.energy), el.directory])
        except IndexError:
            pass
        return energies


    def canMoveEnergy(self):
        return False
    

    def isConnected(self):
        return True

    def get_scan_data(self):
        """
        Descript. :
        """
        return self.scanData
