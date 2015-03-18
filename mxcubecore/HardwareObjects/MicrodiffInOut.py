import logging
from HardwareRepository.BaseHardwareObjects import Device
import time

class MicrodiffInOut(Device):

    def __init__(self, name):
        Device.__init__(self, name)
        self.actuatorState = "unknown"
        #default timeout - 3 sec
        self.timeout = 3


    def init(self):
        self.cmdname =  self.getProperty("cmd_name")
        self.cmd_attr =  self.addChannel({"type":"exporter", "name":"move" }, self.cmdname)
        self.cmd_attr.connectSignal("update", self.valueChanged)

        self.statecmdname = self.getProperty("statecmd_name")
        if self.statecmdname is None:
            self.statecmdname = self.cmdname

        self.state_attr = self.addChannel({"type":"exporter", "name":"state" }, self.statecmdname)
        self.state_attr.connectSignal("update", self.valueChanged)

        self.states = {"true":"in", "false":"out"}
        self.offset = self.getProperty("offset")
        if self.offset > 0:
            self.states = {self.offset:"out", self.offset-1:"in",}

        states = self.getProperty("private_state")
        if states:
            import ast
            self.states = ast.literal_eval(states)
        try:
            tt = float(self.getProperty("timeout"))
            self.timeout = tt
        except:
            pass
        self.hwstate_attr = self.addChannel({"type":"exporter", "name":"hwstate" }, "HardwareState")

        self.moves =  dict((self.states[k], k) for k in self.states)

    def connectNotify(self, signal):
        if signal=='actuatorStateChanged':
            self.valueChanged(self.state_attr.getValue())


    def valueChanged(self, value):
        self.actuatorState = self.states.get(value, "unknown")
        self.emit('actuatorStateChanged', (self.actuatorState, ))
        
    
    def getActuatorState(self):
        if self.actuatorState == "unknown":
            self.connectNotify("actuatorStateChanged")
        return self.actuatorState 

    def actuatorIn(self, wait=True):
        if self.hwstate_attr.getValue() == "Ready":
            self.cmd_attr.setValue(self.moves["in"])
            self.valueChanged(self.state_attr.getValue())
            if wait:
                tt1 = time.time()
                while time.time() - tt1 < self.timeout:
                    if self.state_attr.getValue() != self.moves["in"]:
                        time.sleep(0.2)
                    else:
                        break
        self.valueChanged(self.state_attr.getValue())
 
    def actuatorOut(self, wait=True):
        if self.hwstate_attr.getValue() == "Ready":
            self.cmd_attr.setValue(self.moves["out"])
            self.valueChanged(self.state_attr.getValue())
            if wait:
                tt1 = time.time()
                while time.time() - tt1 < self.timeout:
                    if self.state_attr.getValue() != self.moves["out"]:
                        time.sleep(0.2)
                    else:
                        break
        self.valueChanged(self.state_attr.getValue())      

