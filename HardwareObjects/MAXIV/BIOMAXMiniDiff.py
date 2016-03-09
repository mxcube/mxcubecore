import math, os, time
import logging

import MiniDiff

class BIOMAXMiniDiff(MiniDiff.MiniDiff):

    def init(self):
       
        # initialization channels and command 
        self.x_calib = self.getChannelObject('CoaxCamScaleX')
        self.y_calib = self.getChannelObject('CoaxCamScaleY')
        self.startSetPhase = self.getCommandObject('startSetPhase')

        MiniDiff.MiniDiff.init(self)

        self.flightMotor = self.getDeviceByRole('frontlight')
        self.flightWago = self.getDeviceByRole('wagofrontlight')
        self.lightWago = self.getDeviceByRole('wagobacklight')
   	self.centringPhiy.direction = -1

        

    def getCalibrationData(self, offset):
        return (1.0/self.x_calib.getValue(), 1.0/self.y_calib.getValue())
