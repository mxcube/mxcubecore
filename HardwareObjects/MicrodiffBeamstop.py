from HardwareRepository.BaseHardwareObjects import Equipment
import logging


class MicrodiffBeamstop(Equipment):
    def init(self):
        self.beamstopPosition = self.addChannel({"type":"tango", "name":"bs_pos", "tangoname":self.tangoname, "polling":500 }, "CapillaryPosition")
        self.beamstopPosition.connectSignal("update", self.checkPosition)
        self.beamstopSetInPosition = self.addCommand({"type":"tango", "name":"bs_set_in", "tangoname":self.tangoname},"saveCapillaryBeamPosition")

        self.motors = self["motors"]
        self.roles = self.motors.getRoles()
        self.amplitude = 0 #just to make the beamstop brick happy
        self.positions = { "in": "BEAM", "out": "OFF" }
        self.md2_to_mxcube = { "BEAM": "in", "OFF": "out" }  
 
        #self.connect("equipmentReady", self.equipmentReady)
        #self.connect("equipmentNotReady", self.equipmentNotReady)
 
  
    def moveToPosition(self, name):
        if name == "in":
            self.beamstopPosition.setValue("BEAM")
        elif name == "out":
            self.beamstopPosition.setValue("OFF")

  
    def connectNotify(self, signal):
        self.checkPosition()
   
    """ 
    def equipmentReady(self, *args):
        self.checkPosition()

    def equipmentNotReady(self, *args):
        self.checkPosition()
    """

    def isReady(self):
        return True
 
    def getState(self):
        return "READY"

    def getPosition(self):
        return self.checkPosition(noEmit=True)

    def checkPosition(self, pos=None, noEmit=False):
        if pos is None:
            pos = self.beamstopPosition.getValue()
           
        pos = self.md2_to_mxcube.get(pos)

        if not noEmit:
          if pos:
            self.emit("positionReached", pos)
          else:
            self.emit("noPosition", ())
        return pos

            
    def setNewPositions(self, name, newPositions):
        if name == "in":
            self.beamstopSetInPosition()
            
        
    def getRoles(self):
        return self.roles
        
