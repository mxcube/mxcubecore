import logging
import time
import gevent
import numpy as np
import logging

from mx3core.hardware_objects.ExporterMotor import ExporterMotor
from mx3core.hardware_objects.abstract.AbstractMotor import MotorStates


class MicrodiffKappaMotor(ExporterMotor):
    lock = gevent.lock.Semaphore()
    motors = dict()
    conf = dict()

    def __init__(self, name):
        ExporterMotor.__init__(self, name)

    def init(self):
        ExporterMotor.init(self)
        if not self.actuator_name in ("Kappa", "Phi"):
            raise RuntimeError("MicrodiffKappaMotor class is only for kappa motors")
        MicrodiffKappaMotor.motors[self.actuator_name] = self
        if self.actuator_name == "Kappa":
            MicrodiffKappaMotor.conf["KappaTrans"] = self.stringToList(self.kappaTrans)
            MicrodiffKappaMotor.conf["KappaTransD"] = self.stringToList(
                self.kappaTransD
            )
        elif self.actuator_name == "Phi":
            MicrodiffKappaMotor.conf["PhiTrans"] = self.stringToList(self.phiTrans)
            MicrodiffKappaMotor.conf["PhiTransD"] = self.stringToList(self.phiTransD)
        self.sampx = self.get_object_by_role("sampx")
        self.sampy = self.get_object_by_role("sampy")
        self.phiy = self.get_object_by_role("phiy")

    def stringToList(self, commaSeparatedString):
        return [float(x) for x in commaSeparatedString.split(",")]

    def move(self, absolutePosition):
        kappa_start_pos = MicrodiffKappaMotor.motors["Kappa"].get_value()
        kappa_phi_start_pos = MicrodiffKappaMotor.motors["Phi"].get_value()
        if self.actuator_name == "Kappa":
            kappa_end_pos = absolutePosition
            kappa_phi_end_pos = kappa_phi_start_pos
        else:
            kappa_end_pos = kappa_start_pos
            kappa_phi_end_pos = absolutePosition
        sampx_start_pos = self.sampx.get_value()
        sampy_start_pos = self.sampy.get_value()
        phiy_start_pos = self.phiy.get_value()
        """
        with MicrodiffKappaMotor.lock:
            if self.get_state() != MotorStates.UNKNOWN:
                self.position_attr.set_value(
                    absolutePosition
                )  # absolutePosition-self.offset)
                self.update_state(MotorStates.MOVING)

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
            self.sampx.set_value(newSamplePositions["sampx"])
            self.sampy.set_value(newSamplePositions["sampy"])
            self.phiy.set_value(newSamplePositions["phiy"])
        """

    def waitEndOfMove(self, timeout=None):
        with gevent.Timeout(timeout):
            time.sleep(0.1)
            while self.motorState == MotorStates.MOVING:
                time.sleep(0.1)
            self.sampx.waitEndOfMove()
            self.sampy.waitEndOfMove()
            self.phiy.waitEndOfMove()

    def stop(self):
        if self.get_state() != MotorStates.NOTINITIALIZED:
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
