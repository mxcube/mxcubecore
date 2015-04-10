from HardwareRepository.BaseHardwareObjects import Equipment
import logging


class MicrodiffBeamstop(Equipment):
    def init(self):
        self.beamstop = self.getObjectByRole('beamstop')
        self.beamstop.state_attr.connectSignal("update", self.checkPosition)

        self.motors = self["motors"]
        self.roles = self.motors.getRoles()

        save_cmd_name = self.getProperty("save_cmd_name")
        self.beamstopSetInPosition = self.beamstop.addCommand({"type":"exporter", "name":"bs_set_in", "address":self.beamstop.getProperty('exporter_address')},save_cmd_name)

        #next two lines - just to make the beamstop brick happy
        self.amplitude = 0 
        self.positions = self.beamstop.moves 

    def moveToPosition(self, name):
        if name == "in":
            self.beamstop.actuatorIn(wait=True)
        elif name == "out":
            self.beamstop.actuatorOut(wait=True)
        self.checkPosition()

  
    def connectNotify(self, signal):
        self.checkPosition()
   
    def isReady(self):
        return True
 
    def getState(self):
        return "READY"

    def getPosition(self):
        return self.checkPosition(noEmit=True)

    def checkPosition(self, pos=None, noEmit=False):
        if pos is None:
            pos = self.beamstop.getActuatorState()
        try:
            pos = self.beamstop.states[pos]
        except:
            pass
            
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
        
