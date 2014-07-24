from HardwareRepository.TaskUtils import *
import MiniDiff
import sample_centring
import os
import sys
import logging
import time
import queue_model_objects_v1 as qmo

class Robodiff(MiniDiff.MiniDiff):      
    def __init__(self, name):
        MiniDiff.MiniDiff.__init__(self, name)
        qmo.CentredPosition.set_diffractometer_motor_names("phi",
                                                           "focus",
                                                           "phiz",
                                                           "phiy",
                                                           "zoom",
                                                           "sampx",
                                                           "sampy",
                                                           "kappa",
                                                           "kappa_phi",
                                                           "chi",
                                                           "roby",
                                                           "robz")



    def init(self): 
        self.controller = self.getObjectByRole("controller")
        MiniDiff.MiniDiff.init(self)
        self.chiMotor = self.getDeviceByRole('chi')
        self.robzMotor = self.getDeviceByRole('robz')
        self.robyMotor = self.getDeviceByRole('roby')

    def oscil(self, *args, **kwargs):
        self.controller.oscil(*args, **kwargs)

    def helical_oscil(self, *args, **kwargs):
        self.controller.helical_oscil(*args, **kwargs)

    def getPositions(self, *args, **kwargs):
        res=MiniDiff.MiniDiff.getPositions(self,*args, **kwargs)
        res["chi"]=self.chiMotor.getPosition()
        res["roby"]=self.robyMotor.getPosition()
        res["robz"]=self.robzMotor.getPosition()
        return res

    def start3ClickCentring(self, sample_info=None):
        self.currentCentringProcedure = sample_centring.start({"phi":self.centringPhi,
                                                               "phiy":self.centringPhiy,
                                                               "sampx": self.centringSamplex,
                                                               "sampy": self.centringSampley,
                                                               "phiz": self.centringPhiz },
                                                              self.pixelsPerMmY, self.pixelsPerMmZ,
                                                              self.getBeamPosX(), self.getBeamPosY(),
                                                              chi_angle=-self.chiMotor.getPosition())

        self.currentCentringProcedure.link(self.manualCentringDone)


    def startAutoCentring(self, sample_info=None, loop_only=False):
        self.currentCentringProcedure = sample_centring.start_auto(self.camera,
                                                                   {"phi":self.centringPhi,
                                                                    "phiy":self.centringPhiy,
                                                                    "sampx": self.centringSamplex,
                                                                    "sampy": self.centringSampley,
                                                                    "phiz": self.centringPhiz },
                                                                   self.pixelsPerMmY, self.pixelsPerMmZ,
                                                                   self.getBeamPosX(), self.getBeamPosY(),
                                                                   chi_angle=-self.chiMotor.getPosition(),
                                                                   msg_cb=self.emitProgressMessage,
                                                                   new_point_cb=lambda point: self.emit("newAutomaticCentringPoint", point))

        self.currentCentringProcedure.link(self.autoCentringDone)

        self.emitProgressMessage("Starting automatic centring procedure...")


    def moveMotors(self, roles_positions_dict):
        motor = { "phi": self.phiMotor,
                  "focus": self.focusMotor,
                  "phiy": self.phiyMotor,
                  "phiz": self.phizMotor,
                  "sampx": self.sampleXMotor,
                  "sampy": self.sampleYMotor,
                  "kappa": self.kappaMotor,
                  "kappa_phi": self.kappaPhiMotor,
                  "chi": self.chiMotor,
                  "roby": self.robyMotor,
                  "robz": self.robzMotor,
                  "zoom": self.zoomMotor }


        for role, pos in roles_positions_dict.iteritems():
           motor[role].move(pos)

        # TODO: remove this sleep, the motors states should
        # be MOVING since the beginning (or READY if move is
        # already finished) 
        time.sleep(1)

        while any([m.getState() == m.MOVING for m in motor.itervalues()]):
           time.sleep(0.1)

        if any([m.getState() == m.ONLIMIT for m in motor.itervalues()]):
           raise RuntimeError("Motor %s on limit" % m.username)

