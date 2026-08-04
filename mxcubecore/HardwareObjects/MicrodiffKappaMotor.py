# encoding: utf-8
#
#  Project name: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Calculate the translation correction for inversed kappa goniostats.
For more info see Acta Cryst.(2011). A67, 219-228,
Sandor Brockhauser et al., formula (3).
"""

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"

import numpy as np
from gevent import lock

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractMotor import MotorStates
from mxcubecore.HardwareObjects.ExporterMotor import ExporterMotor


class MicrodiffKappaMotor(ExporterMotor):
    lock = lock.Semaphore()
    motors = {}
    conf = {}

    def init(self):
        super().init()
        if self.actuator_name not in ("Kappa", "Phi"):
            raise RuntimeError("MicrodiffKappaMotor class is only for kappa motors")
        MicrodiffKappaMotor.motors[self.actuator_name] = self

        for nam in ("Trans", "TransD"):
            _trans = self.get_property(nam)
        if isinstance(_trans, str):
            _trans = self.str_to_list(_trans)
        MicrodiffKappaMotor.conf[f"{self.actuator_name}{nam}"] = _trans

    def str_to_list(self, comma_separated_str: str) -> list:
        """Transform comma separated string to list of floats"""
        return [float(x) for x in comma_separated_str.split(",")]

    def _set_value(self, value: float):
        """Move motor to absolute value.
        Args:
            value: target value
        """
        _kappa_pos = MicrodiffKappaMotor.motors["Kappa"].get_value()
        _kappa_phi_pos = MicrodiffKappaMotor.motors["Phi"].get_value()
        if self.actuator_name == "Kappa":
            kappa_end_pos = value
            kappa_phi_end_pos = _kappa_phi_pos
        else:
            kappa_end_pos = _kappa_pos
            kappa_phi_end_pos = value

        """
        diffr = HWR.beamline.diffractometer
        with MicrodiffKappaMotor.lock:
            super().set_value(value)

            # calculations
            motor_pos_dict = self.calc_sample_position(
                kappa_start_pos,
                kappa_phi_start_pos,
                kappa_end_pos,
                kappa_phi_end_pos,
                diffr.sampx.get_value(),
                diffr.sampy.get_value(),
                diffr.phiy.get_value(),
            )
            diffr.set_value_motors(motor_pos_dict)
        """

    def stop(self):
        if self.get_state() != MotorStates.NOTINITIALIZED:
            self._motor_abort()
        for m in (self.sampx, self.sampy, self.phiy):
            m.stop()

    def calc_sample_position(
        self,
        kappa_start: float,
        phi_start: float,
        kappa_end: float,
        phi_end: float,
        sampx: float,
        sampy: float,
        phiy: float,
    ) -> dict:
        """Calculate the translation correction for inversed kappa goniostats.
            For more info see Acta Cryst.(2011). A67, 219-228,
            Sandor Brockhauser et al., formula (3).
        Args:
            motor positions
        Returns:
            Calculated sampx, sampy and phiy positions.
        """
        t_kappa_zero = np.array(MicrodiffKappaMotor.conf["KappaTrans"])
        t_phi_zero = np.array(MicrodiffKappaMotor.conf["PhiTrans"])
        t_start = np.array([-sampx, -sampy, -phiy])
        _kappa_rot = np.array(MicrodiffKappaMotor.conf["KappaTransD"])
        _phi_rot = np.array(MicrodiffKappaMotor.conf["PhiTransD"])
        kappa_rm1 = self.rotation_matrix(_kappa_rot, -kappa_start * np.pi / 180.0)
        kappa_rm2 = self.rotation_matrix(_kappa_rot, kappa_end * np.pi / 180.0)
        phi_rm = self.rotation_matrix(_phi_rot, (phi_end - phi_start) * np.pi / 180.0)
        t_step1 = t_kappa_zero - t_start
        t_step2 = t_kappa_zero - np.dot(kappa_rm1, t_step1)
        t_step3 = t_phi_zero - t_step2
        t_step4 = t_phi_zero - np.dot(phi_rm, t_step3)
        t_step5 = t_kappa_zero - t_step4
        t_end = t_kappa_zero - np.dot(kappa_rm2, t_step5)
        new_motor_pos = {}
        new_motor_pos["sampx"] = float(-t_end[0])
        new_motor_pos["sampy"] = float(-t_end[1])
        new_motor_pos["phiy"] = float(-t_end[2])
        self.log.info("New motor positions: %r" % new_motor_pos)
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
