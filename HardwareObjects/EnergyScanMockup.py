from qt import *
from HardwareRepository.BaseHardwareObjects import Equipment
import logging
import gevent

class EnergyScanMockup(Equipment):
    def init(self):
        self.ready_event = gevent.event.Event()
        self.scanInfo = {}


    def startEnergyScan(self, element, edge, directory, prefix,
                        session_id = None, blsample_id= None):
        self.emit('energyScanFinished', (self.scanInfo,))
        self.ready_event.set()


    def doChooch(self, scanObject, elt, edge, scanArchiveFilePrefix,
                 scanFilePrefix):
        return 13, 'fppPeak', 'fpPeak', 14, 'fppInfl', 'fpInfl', 15,\
               'chooch_graph_x', 'chooch_graph_y1', 'chooch_graph_y2', 'title'


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
