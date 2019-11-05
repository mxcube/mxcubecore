import logging
import time
import gevent
import numpy as np
import logging

from HardwareRepository.HardwareObjects.MD2Motor import MD2Motor
from HardwareRepository.HardwareObjects.abstract.AbstractMotor import MotorStates

class MicrodiffKappaMotor(MD2Motor):
    lock = gevent.lock.Semaphore()
    motors = dict()
    conf = dict()

    def __init__(self, name):
        MD2Motor.__init__(self, name)

    def init(self):
        self.motor_name = self.getProperty("motor_name")
        if not self.getMotorMnemonic() in ("Kappa", "Phi"):
            raise RuntimeError("MicrodiffKappaMotor class is only for kappa motors")
        MicrodiffKappaMotor.motors[self.getMotorMnemonic()] = self
        if self.getMotorMnemonic() == "Kappa":
            MicrodiffKappaMotor.conf["KappaTrans"] = self.stringToList(self.kappaTrans)
            MicrodiffKappaMotor.conf["KappaTransD"] = self.stringToList(
                self.kappaTransD
            )
        elif self.getMotorMnemonic() == "Phi":
            MicrodiffKappaMotor.conf["PhiTrans"] = self.stringToList(self.phiTrans)
            MicrodiffKappaMotor.conf["PhiTransD"] = self.stringToList(self.phiTransD)
        MD2Motor.init(self)
        self.sampx = self.getObjectByRole("sampx")
        self.sampy = self.getObjectByRole("sampy")
        self.phiy = self.getObjectByRole("phiy")

    def stringToList(self, commaSeparatedString):
        return [float(x) for x in commaSeparatedString.split(",")]

    def move(self, absolutePosition):
        kappa_start_pos = MicrodiffKappaMotor.motors["Kappa"].getPosition()
        kappa_phi_start_pos = MicrodiffKappaMotor.motors["Phi"].getPosition()
        if self.getMotorMnemonic() == "Kappa":
            kappa_end_pos = absolutePosition
            kappa_phi_end_pos = kappa_phi_start_pos
        else:
            kappa_end_pos = kappa_start_pos
            kappa_phi_end_pos = absolutePosition
        sampx_start_pos = self.sampx.getPosition()
        sampy_start_pos = self.sampy.getPosition()
        phiy_start_pos = self.phiy.getPosition()

        with MicrodiffKappaMotor.lock:
            if self.getState() != MotorStates.NOTINITIALIZED:
                self.position_attr.setValue(
                    absolutePosition
                )  # absolutePosition-self.offset)
                self.motorStateChanged(MotorStates.MOVING)

            # calculations
            newSamplePositions = self.getNewSamplePosition(
                kappa_start_pos,
                kappa_phi_start_pos,
                sampx_start_pos,
                sampy_start_pos,
                phiy_start_pos,
                kappa_end_pos,
                kappa_phi_end_pos,
            )
            self.sampx.move(newSamplePositions["sampx"])
            self.sampy.move(newSamplePositions["sampy"])
            self.phiy.move(newSamplePositions["phiy"])

    def waitEndOfMove(self, timeout=None):
        with gevent.Timeout(timeout):
            time.sleep(0.1)
            while self.motorState == MotorStates.MOVING:
                time.sleep(0.1)
            self.sampx.waitEndOfMove()
            self.sampy.waitEndOfMove()
            self.phiy.waitEndOfMove()

    def stop(self):
        if self.getState() != MotorStates.NOTINITIALIZED:
            self._motor_abort()
        for m in (self.sampx, self.sampy, self.phiy):
            m.stop()

    def getNewSamplePosition(
        self, kappaAngle1, phiAngle1, sampx, sampy, phiy, kappaAngle2, phiAngle2
    ):
        """
        This method calculates the translation correction for inversed kappa goniostats.
        For more info see Acta Cryst.(2011). A67, 219-228, Sandor Brockhauser et al., formula (3).
        See also MXSUP-1823.
        """
        logging.getLogger("HWR").info("In MicrodiffKappaMotor.getNewSamplePosition")
        logging.getLogger("HWR").info(
            "Input arguments: Kappa %.2f Phi %.2f sampx %.3f sampy %.3f phiy %.3f Kappa2 %.2f Phi2 %.2f"
            % (kappaAngle1, phiAngle1, sampx, sampy, phiy, kappaAngle2, phiAngle2)
        )
        kappaRot = np.array(MicrodiffKappaMotor.conf["KappaTransD"])
        phiRot = np.array(MicrodiffKappaMotor.conf["PhiTransD"])
        t_kappa_zero = np.array(MicrodiffKappaMotor.conf["KappaTrans"])
        t_phi_zero = np.array(MicrodiffKappaMotor.conf["PhiTrans"])
        t_start = np.array([-sampx, -sampy, -phiy])
        # if beamline in ["id29", "id30b"]:
        #    t_start = np.array([-sampx, -sampy, -phiy])
        # else:
        #    t_start = np.array([sampx, sampy, -phiy])
        kappaRotMat1 = self.rotation_matrix(kappaRot, -kappaAngle1 * np.pi / 180.0)
        kappaRotMat2 = self.rotation_matrix(kappaRot, kappaAngle2 * np.pi / 180.0)
        phiRotMat = self.rotation_matrix(
            phiRot, (phiAngle2 - phiAngle1) * np.pi / 180.0
        )
        t_step1 = t_kappa_zero - t_start
        t_step2 = t_kappa_zero - np.dot(kappaRotMat1, t_step1)
        t_step3 = t_phi_zero - t_step2
        t_step4 = t_phi_zero - np.dot(phiRotMat, t_step3)
        t_step5 = t_kappa_zero - t_step4
        t_end = t_kappa_zero - np.dot(kappaRotMat2, t_step5)
        new_motor_pos = {}
        new_motor_pos["sampx"] = float(-t_end[0])
        new_motor_pos["sampy"] = float(-t_end[1])
        new_motor_pos["phiy"] = float(-t_end[2])
        logging.getLogger("HWR").info("New motor positions: %r" % new_motor_pos)
        return new_motor_pos

    def rotation_invariant(self, v):
        return np.outer(v, v)

    def skew_symmetric(self, v):
        l, m, n = v
        return np.array([[0, -n, m], [n, 0, -l], [-m, l, 0]])

    def inverse_skew_symmetric(self, v):
        l, m, n = v
        return np.array([[0, n, -m], [-n, 0, l], [m, -l, 0]])

    def rotation_symmetric(self, v):
        return np.identity(3) - np.outer(v, v)

    def rotation_matrix(self, axis, theta):
        return (
            self.rotation_invariant(axis)
            + self.skew_symmetric(axis) * np.sin(theta)
            + self.rotation_symmetric(axis) * np.cos(theta)
        )
