from HardwareRepository.BaseHardwareObjects import Equipment
import logging


class MicrodiffApertureAlign(Equipment):
    def init(self):
        self.apertureAlignPosition = self.addChannel({"type":"tango", "name":"bs_pos", "tangoname":self.tangoname, "polling":"events" }, "AperturePredefinedPosition")
        self.apertureAlignPosition.connectSignal("update", self.checkPosition)
        self.apertureAlignSetInPosition = self.addCommand({"type":"tango", "name":"bs_set_in", "tangoname":self.tangoname},"ApertureSaveInPosition")

        self.motors = self["motors"]
        self.roles = self.motors.getRoles()
        self.amplitude = 0 #just to make the beamstop brick happy
        self.positions = { "in": 1, "out": 2 }
        #self.positionsIndex = ["in", "out" ]
   
        self.connect("equipmentReady", self.equipmentReady)
        self.connect("equipmentNotReady", self.equipmentNotReady)
 
  
    def moveToPosition(self, name):
        if name == "in":
            self.apertureAlignPosition.setValue(1)
        elif name == "out":
            self.apertureAlignPosition.setValue(2)

    def connectNotify(self, signal):
        self.checkPosition()   
 
    def equipmentReady(self, *args):
        self.checkPosition()
        return Equipment.equipmentReady(self, *args)


    def equipmentNotReady(self, *args):
        self.checkPosition()
        return Equipment.equipmentNotReady(self, *args)

  
    def isReady(self):
        return True
 
    def getState(self):
        return "READY"

    def getPosition(self):
        return self.checkPosition(noEmit=True)


    def checkPosition(self, pos=None, noEmit=False):
        if pos is None:
            pos = self.apertureAlignPosition.getValue()

        if pos == 1:
            # in
            if not noEmit: self.emit("positionReached", ("in", ))
            return "in"
        elif pos == 2:
            if not noEmit: self.emit("positionReached", ("out", ))
            return "out"
        else:
            if not noEmit: self.emit("noPosition", ())
            return None

            
    def setNewPositions(self, name, newPositions):
        if name == "in":
            self.apertureAlignSetInPosition()
            
        
    def getRoles(self):
        return self.roles
        
