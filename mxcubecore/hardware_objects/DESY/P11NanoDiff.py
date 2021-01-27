#
#  Project: MXCuBE
#  https://github.com/mxcube.
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
#   You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import time
import math
import random
import warnings
import sample_centring
import gevent

from mxcubecore.hardware_objects.GenericDiffractometer import (
    GenericDiffractometer,
)
from mxcubecore import HardwareRepository as HWR
from gevent.event import AsyncResult


class P11NanoDiff(GenericDiffractometer):
    """
    Descript. :
    """

    def __init__(self, *args):
        """
        Descript. :
        """
        self.beam_position = [680, 512]
        GenericDiffractometer.__init__(self, *args)

    def init(self):
        """
        Descript. :
        """
        GenericDiffractometer.init(self)

        self.current_phase = GenericDiffractometer.PHASE_CENTRING

        self.cancel_centring_methods = {}

        self.current_state_dict = {}
        self.centring_status = {"valid": False}
        self.centring_time = 0

        #using sample_centring module
        self.centring_phi = sample_centring.CentringMotor(
            self.motor_hwobj_dict["phi"], direction=-1, 
        )
        self.centring_phiz = sample_centring.CentringMotor(
            self.motor_hwobj_dict["phiz"], direction=1, units='microns'
        )
        self.centring_phiy = sample_centring.CentringMotor(
            self.motor_hwobj_dict["phiy"], direction=1, units='microns',
        )
        self.centring_sampx = sample_centring.CentringMotor(
            self.motor_hwobj_dict["sampx"], units='microns',
        )
        self.centring_sampy = sample_centring.CentringMotor(
            self.motor_hwobj_dict["sampy"], units='microns',
        )

        self.update_zoom_calibration()

    def update_zoom_calibration(self):
        zoom_hwobj = self.motor_hwobj_dict['zoom'] 
        self.pixels_per_mm_x, self.pixels_per_mm_y = zoom_hwobj.get_pixels_per_mm()
        self.log.debug("P11NanoDiff - pixels per mm are: %s x %s " % (self.pixels_per_mm_x, self.pixels_per_mm_y))
        self.emit("pixelsPerMmChanged", ((self.pixels_per_mm_x, self.pixels_per_mm_y),))

    def execute_server_task(self, method, timeout=30, *args):
        return

    def is_reversing_rotation(self):
        return True

    def get_grid_direction(self):
        """
        Descript. :
        """
        return self.grid_direction

    def automatic_centring(self):
        """Automatic centring procedure"""
        return

    def is_ready(self):
        """
        Descript. :
        """
        return True

    def is_valid(self):
        """
        Descript. :
        """
        return True

    def invalidate_centring(self):
        """
        Descript. :
        """
        if self.current_centring_procedure is None and self.centring_status["valid"]:
            self.centring_status = {"valid": False}
            # self.emitProgressMessage("")
            self.emit("centringInvalid", ())

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        """
        Descript. :
        """
        return
        centred_pos_dir = self._get_random_centring_position()
        return centred_pos_dir

    def refresh_omega_reference_position(self):
        """
        Descript. :
        """
        return

    def get_omega_axis_position(self):
        """
        Descript. :
        """
        return self.motor_hwobj_dict["phi"].get_value()

    def beam_position_changed(self, value):
        """
        Descript. :
        """
        self.beam_position = value

    def get_current_centring_method(self):
        """
        Descript. :
        """
        return self.current_centring_method

    def motor_positions_to_screen(self, centred_positions_dict):
        """
        Descript. :
        """
        self.update_zoom_calibration()

        beam_xc, beam_yc = self.beam_position
        phi_pos = self.motor_hwobj_dict['phi'].get_value()

        sampx_c = centred_positions_dict['sampx']
        sampy_c = centred_positions_dict['sampy']
        phiz_c = centred_positions_dict['phiz']

        sampx_pos = self.centring_sampx.motor.get_value()
        sampy_pos = self.centring_sampy.motor.get_value()
        phiz_pos = self.centring_phiz.motor.get_value()

        sampx_d = sampx_c - sampx_pos
        sampy_d = sampy_c - sampy_pos
        phiz_d = phiz_c - phiz_pos

        # convert to mms
        sampx_d = self.centring_sampx.units_to_mm(sampx_d)
        sampy_d = self.centring_sampy.units_to_mm(sampy_d)
        phiz_d = self.centring_phiz.units_to_mm(phiz_d)

        cphi = math.cos(math.radians(phi_pos))
        sphi = math.sin(math.radians(phi_pos))

        dx = sampx_d * cphi - sampy_d * sphi
        dy = sampx_d * sphi + sampy_d * cphi

        xdist = phiz_d * self.pixels_per_mm_x
        ydist = dy * self.pixels_per_mm_y

        x = beam_xc  + xdist
        y = beam_yc  + ydist

        return x,y

    #def moveToCentredPosition(self, centred_position, wait=False):
    #    REMOVED. test pending at beamline
    #    """
    #    Descript. :
    #    """
    #    try:
    #        return self.move_to_centred_position(centred_position)
    #    except Exception:
    #        self.log.exception("Could not move to centred position")

    def start_auto_focus(self):
        """
        Descript. :
        """
        return

    def start_manual_centring(self, sample_info=None, wait_result=None):
        """
        """
        self.log.debug("Manual 3 click centring. using sample centring module: %s" % self.use_sample_centring)
        self.emit_progress_message("Manual 3 click centring...")

        self.current_centring_procedure = gevent.spawn(self.manual_centring)
        self.current_centring_procedure.link(self.centring_done)


    def manual_centring(self, phi_range=120, n_points=3):
        """
        Descript. :
        """
        X = []
        Y = []
        PHI = []

        beam_xc, beam_yc = self.beam_position
        self.log.debug("STARTING Manual Centring")

        motor_positions = {
                'phi': self.centring_phi.motor.get_value(),
                'sampx': self.centring_sampx.motor.get_value(),
                'sampy': self.centring_sampy.motor.get_value(),
                'phiy': self.centring_phiy.motor.get_value(),
                'phiz': self.centring_phiz.motor.get_value(),
                }

        phi_mot = self.centring_phi.motor
        phi_start_pos = phi_mot.get_value()

        for click in range(n_points):
            self.user_clicked_event = AsyncResult()
            x, y = self.user_clicked_event.get()
            if click < 2:
                phi_mot.set_value_relative(phi_range)

            X.append(x)
            Y.append(y)
            PHI.append(phi_mot.get_value())

        phi_mot.set_value(phi_start_pos)
        gevent.sleep(2)
        phi_mot.wait_ready()

        DX = []
        DY = []
        ANG = []

        P = []
        Q = []

        for i in range(n_points):
            dx = X[i] - beam_xc
            dy = Y[i] - beam_yc
            ang = math.radians( PHI[i])

            DX.append(dx)
            DY.append(dy)
            ANG.append(ang)
            
        for i in range(n_points):
            y0 = DY[i]
            ang0 = ANG[i]
            if i < (n_points-1):
                y1 = DY[i+1]
                ang1 = ANG[i+1]
            else:
                y1 = DY[0]
                ang1 = ANG[0]

            p = ( y0*math.sin(ang1) - y1*math.sin(ang0) ) / math.sin(ang1-ang0)
            q = ( y0*math.cos(ang1) - y1*math.cos(ang0) ) / math.sin(ang1-ang0)

            P.append(p)
            Q.append(q)

        x_s = -sum(Q)/n_points
        y_s = sum(P)/n_points
        z_s = sum(DX)/n_points

        x_d_mm = x_s / self.pixels_per_mm_y
        y_d_mm = y_s / self.pixels_per_mm_y
        z_d_mm = z_s / self.pixels_per_mm_x

        x_d = self.centring_sampx.mm_to_units(x_d_mm)
        y_d = self.centring_sampy.mm_to_units(y_d_mm)
        z_d = self.centring_phiz.mm_to_units(z_d_mm)

        sampx_mot = self.centring_sampx.motor
        sampy_mot = self.centring_sampy.motor
        phiz_mot = self.centring_phiz.motor

        x_pos = sampx_mot.get_value() + x_d
        y_pos = sampy_mot.get_value() + y_d
        z_pos = phiz_mot.get_value() + z_d

        motor_positions['sampx'] = x_pos
        motor_positions['sampy'] = y_pos
        motor_positions['phiz'] = z_pos
        return motor_positions

    def get_positions(self):
        sampx_pos = self.motor_hwobj_dict["sampx"].get_value()
        sampy_pos = self.motor_hwobj_dict["sampy"].get_value()
        phiy_pos = self.motor_hwobj_dict["phiy"].get_value()
        phiz_pos = self.motor_hwobj_dict["phiz"].get_value()
        phi_pos = self.motor_hwobj_dict["phi"].get_value()

        return {
                'phi': phi_pos,
                'phiy': phiy_pos,
                'phiz': phiz_pos,
                'sampx': sampx_pos,
                'sampy': sampy_pos,
                }

    def move_to_beam(self, x, y, omega=None):
        """
        Descript. : function to create a centring point based on all motors
                    positions.
        """

        # calculate distance from clicked position to center in mm
        dx = (x - self.beam_position[0]) / self.pixels_per_mm_x
        dy = (y - self.beam_position[1]) / self.pixels_per_mm_y
        
        phi = self.centring_phi.get_value()

        cphi = math.cos(math.radians(phi))
        sphi = math.sin(math.radians(phi))

        samp_y = dy * cphi 
        samp_x = dy * sphi

        # convert to microns if necessary
        samp_x = self.centring_sampx.mm_to_units(samp_x)
        samp_y = self.centring_sampy.mm_to_units(samp_y)
        x_dist = self.centring_phiz.mm_to_units(dx)

        samp_x_pos = self.centring_sampx.motor.get_value() + samp_x
        samp_y_pos = self.centring_sampy.motor.get_value() + samp_y
        phiz = self.centring_phiz.motor.get_value() + x_dist

        self.centring_sampx.motor.set_value(samp_x_pos)
        self.centring_sampy.motor.set_value(samp_y_pos)
        self.centring_phiz.motor.set_value(phiz)

    def start_move_to_beam(self, coord_x=None, coord_y=None, omega=None):
        """
        Descript. :
        """
        self.centring_time = time.time()
        curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.centring_status = {
            "valid": True,
            "startTime": curr_time,
            "endTime": curr_time,
        }
        motors = self.get_positions()
        motors["beam_x"] = 0.1
        motors["beam_y"] = 0.1
        self.centring_status["motors"] = motors
        self.centring_status["valid"] = True
        self.centring_status["angleLimit"] = False
        self.emit_progress_message("")
        self.accept_centring()
        self.current_centring_method = None
        self.current_centring_procedure = None

    def re_emit_values(self):
        self.emit("zoomMotorPredefinedPositionChanged", None, None)
        omega_ref = [0, 238]
        self.emit("omegaReferenceChanged", omega_ref)

    def move_kappa_and_phi(self, kappa, kappa_phi):
        return

    def get_osc_max_speed(self):
        return 66

    def get_osc_limits(self):
        if self.in_plate_mode:
            return (170, 190)
        else:
            return (-360, 360)

    def get_scan_limits(self, speed=None, num_images=None, exp_time=None):
        if self.in_plate_mode:
            return (170, 190)
        else:
            return (-360, 360)

    def get_osc_dynamic_limits(self):
        """Returns dynamic limits of oscillation axis"""
        return (0, 20)

    def get_scan_dynamic_limits(self, speed=None):
        return (-360, 360)

    def move_omega_relative(self, relative_angle):
        self.motor_hwobj_dict["phi"].set_value_relative(relative_angle, 5)

    def set_phase(self, phase, timeout=None):
        self.current_phase = str(phase)
        self.emit("minidiffPhaseChanged", (self.current_phase,))

    def get_point_from_line(self, point_one, point_two, index, images_num):
        return point_one.as_dict()
