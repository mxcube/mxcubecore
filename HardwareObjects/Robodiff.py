from HardwareRepository.TaskUtils import *
import MiniDiff
import sample_centring
import os
import sys
import logging
import time
import queue_model_objects_v1 as qmo
import copy
import gevent


class Robodiff(MiniDiff.MiniDiff):
    def __init__(self, name):
        MiniDiff.MiniDiff.__init__(self, name)
        qmo.CentredPosition.set_diffractometer_motor_names(
            "phi",
            "focus",
            "phiz",
            "phiy",
            "zoom",
            "sampx",
            "sampy",
            "kappa",
            "kappa_phi",
            "chi",
            "y",
            "z",
        )

    def init(self):
        self.controller = self.getObjectByRole("controller")
        MiniDiff.MiniDiff.init(self)
        self.chiMotor = self.getDeviceByRole("chi")
        self.zMotor = self.getDeviceByRole("z")
        self.yMotor = self.getDeviceByRole("y")
        self.centringPhiz = sample_centring.CentringMotor(
            self.zMotor
        )  # , reference_position=phiz_ref)
        self.centringPhiy = sample_centring.CentringMotor(self.yMotor)

        self.connect(self.zMotor, "stateChanged", self.phizMotorStateChanged)
        self.connect(self.zMotor, "positionChanged", self.phizMotorMoved)
        self.connect(self.zMotor, "positionChanged", self.emitDiffractometerMoved)
        self.connect(self.yMotor, "stateChanged", self.phiyMotorStateChanged)
        self.connect(self.yMotor, "positionChanged", self.phiyMotorMoved)
        self.connect(self.yMotor, "positionChanged", self.emitDiffractometerMoved)

    def oscil(self, *args, **kwargs):
        self.controller.oscil(*args, **kwargs)

    def helical_oscil(self, *args, **kwargs):
        self.controller.helical_oscil(*args, **kwargs)

    def getPositions(self, *args, **kwargs):
        res = MiniDiff.MiniDiff.getPositions(self, *args, **kwargs)
        res["chi"] = self.chiMotor.getPosition()
        res["y"] = self.yMotor.getPosition()
        res["z"] = self.zMotor.getPosition()
        return res

    def start3ClickCentring(self, sample_info=None):
        self.currentCentringProcedure = sample_centring.start(
            {
                "phi": self.centringPhi,
                "phiy": self.centringPhiy,
                "sampx": self.centringSamplex,
                "sampy": self.centringSampley,
                "phiz": self.centringPhiz,
            },
            self.pixelsPerMmY,
            self.pixelsPerMmZ,
            self.getBeamPosX(),
            self.getBeamPosY(),
            chi_angle=-self.chiMotor.getPosition(),
        )
        self.currentCentringProcedure.link(self.manualCentringDone)

    def startAutoCentring(self, sample_info=None, loop_only=False):
        self.lightWago.wagoIn()

        self.currentCentringProcedure = sample_centring.start_auto(
            self.camera,
            {
                "phi": self.centringPhi,
                "phiy": self.centringPhiy,
                "sampx": self.centringSamplex,
                "sampy": self.centringSampley,
                "phiz": self.centringPhiz,
            },
            self.pixelsPerMmY,
            self.pixelsPerMmZ,
            self.getBeamPosX(),
            self.getBeamPosY(),
            chi_angle=-self.chiMotor.getPosition(),
            msg_cb=self.emitProgressMessage,
            new_point_cb=lambda point: self.emit("newAutomaticCentringPoint", point),
        )

        self.currentCentringProcedure.link(self.autoCentringDone)

        self.emitProgressMessage("Starting automatic centring procedure...")

    def motor_positions_to_screen(self, centred_positions_dict):
        centred_pos_dict = copy.deepcopy(centred_positions_dict)
        centred_pos_dict["phiy"] = centred_positions_dict["y"]
        centred_pos_dict["phiz"] = centred_positions_dict["z"]
        return MiniDiff.MiniDiff.motor_positions_to_screen(self, centred_pos_dict)

    def moveMotors(self, roles_positions_dict):
        motor = {
            "phi": self.phiMotor,
            "focus": self.focusMotor,
            "phiy": self.phiyMotor,
            "phiz": self.phizMotor,
            "sampx": self.sampleXMotor,
            "sampy": self.sampleYMotor,
            "kappa": self.kappaMotor,
            "kappa_phi": self.kappaPhiMotor,
            "chi": self.chiMotor,
            "y": self.yMotor,
            "z": self.zMotor,
            "zoom": self.zoomMotor,
        }

        _aperture_move = gevent.spawn(self.controller.move_to_last_known_aperture)

        for role, pos in roles_positions_dict.iteritems():
            logging.info("moving motor %s to %f", role, pos)
            motor[role].move(pos)

        # TODO: remove this sleep, the motors states should
        # be MOVING since the beginning (or READY if move is
        # already finished)
        time.sleep(1)

        while any([m.getState() == m.MOVING for m in motor.itervalues()]):
            time.sleep(0.1)

        _aperture_move.get()

        if any([m.getState() == m.ONLIMIT for m in motor.itervalues()]):
            raise RuntimeError("Motor %s on limit" % m.username)
