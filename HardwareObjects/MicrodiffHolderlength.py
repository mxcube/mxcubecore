import MicrodiffMotor
import math
import logging
import time

class MicrodiffHolderlength(MicrodiffMotor.MicrodiffMotor):     
    def __init__(self, *args):
        MicrodiffMotor.MicrodiffMotor.__init__(self, *args)
 
    def init(self): 
        self.offset_chan = self.addChannel({"type":"exporter", "name":"offset" }, "SampleHolderLength")
        #self.offset_chan.connectSignal("update", self.offsetChanged)
        self.offset = self.offset_chan.getValue()

        MicrodiffMotor.MicrodiffMotor.init(self)

    def offsetChanged(self, new_offset):
        self.offset = new_offset

    def motorPositionChanged(self, absolutePosition, private={}):
        if math.fabs(absolutePosition - private.get("old_pos", 1E12))<=1E-3:
          return 
        private["old_pos"]=absolutePosition 

        self.emit('positionChanged', (self.offset-absolutePosition, ))

    def getPosition(self):
        return self.offset-self.position_attr.getValue()

    def move(self, absolutePosition):
        self.position_attr.setValue(self.offset-absolutePosition) #absolutePosition-self.offset)
