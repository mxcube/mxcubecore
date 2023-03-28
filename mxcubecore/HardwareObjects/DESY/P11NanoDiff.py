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

import sys
if sys.version_info[0] >= 3:
    unicode = str

import time
import math
import random
import warnings
import sample_centring
import gevent

from mxcubecore.HardwareObjects.GenericDiffractometer import (
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
                'phiy': self.centring_phiy.motor.get_value(),
                'phiz': self.centring_phiz.motor.get_value(),
                'sampx': self.centring_sampx.motor.get_value(),
                'sampy': self.centring_sampy.motor.get_value(),
                'phi': self.centring_phi.motor.get_value(),
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

        #phi_mot.set_value(phi_start_pos)
        #gevent.sleep(2)
        #phi_mot.wait_ready()

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

    def set_phase(self, phase, timeout=None):
        self.set_phase_task = gevent.spawn(self.goto_phase, phase)

    def get_phase(self):
        return self.current_phase

    def motor_state_changed(self, state=None):

        new_state = DiffractometerState.Ready

        if self.phase_state == self.PHASE_STATES.MOVING:
            new_state = DiffractometerState.Moving
        else:
            for motname, motor in self.motor_hwobj_dict.items(): 
                mot_state = motor.get_state()
                if mot_state == HardwareObjectState.UNKNOWN:
                   new_state = DiffractometerState.Unknown
                   break
                elif mot_state == HardwareObjectState.FAULT:
                   new_state = DiffractometerState.Fault
                   break
                elif motor.is_moving():
                   new_state = DiffractometerState.Moving
                   break

        if new_state != self.diffractometer_state:        
            self._update_state(new_state)

    def _update_state(self, new_state):
        self.emit("minidiffStateChanged", (new_state,))
        self.diffractometer_state = new_state

    @task
    def goto_phase(self,phase):
        self.log.debug("Starting phase change  - setting phase to %s\n" % phase)

        self.phase_state = self.PHASE_STATES.MOVING
        self.motor_state_changed()

        self.emit("minidiffPhaseStateChanged", (self.PHASE_STATES.MOVING,))

        if phase.lower() == "centring":
            self.goto_centring_phase(wait=True)
        elif phase.lower() == "transfer":
            self.goto_transfer_phase(wait=True)
        elif phase.lower() == "datacollection":
            self.goto_collect_phase(wait=True)
        elif phase.lower() == "beamlocation":
            self.goto_beam_phase(wait=True)
        else:
            self.user_log.debug("Unknown diffractometer phase: %s\n", phase)

        self.waiting_phase = True
        self.wait_phase()

    def wait_phase(self, timeout=140):
        start_wait = time.time()

        self.log.debug(" WAITING PHASE STARTED")
        while (time.time() - start_wait < timeout):
            time.sleep(0.1)

            moving = False
            for ho in [self.detcover_hwobj,
                       self.backlight_hwobj,
                       self.beamstop_hwobj,
                       self.collimator_hwobj,
                       self.yag_hwobj,
                       self.pinhole_hwobj]:

                if ho.is_moving():
                    moving = True

            if moving:
                continue

            break

        self.log.debug(" PHASE REACHED. NOW WAITING FOR OMEGA")
        self.wait_omega()
       
        gevent.sleep(0.6) # allow for position events to arrive
        self.update_phase()
        self.motor_state_changed()


        # Extra waiting loop for the pinhole did not reached the top position because it is blocked.
        pinhole_states=["200","100", "50", "20", "Down"]
        timeout=140
        start_wait = time.time()
        self.log.debug("================= Wait whiile pinholes are not blocked whille going up. Pinhole now in the position "+str(self.pinhole_hwobj.get_position()))
        while (time.time() - start_wait < timeout):
            time.sleep(0.1)

            for st in pinhole_states:
                if self.pinhole_hwobj.get_position() == st and not self.pinhole_hwobj.is_moving():
                    self.log.debug("Pinhole has reached position "+str(self.pinhole_hwobj.get_position()))
                    break
                else:
                    self.log.debug("Still waiting for the pinhole")
                    continue
            break

        self.log.debug(" PHASE CHANGED COMPLETED")
        self.waiting_phase = False





        

    def is_centring_phase(self):
        return self.get_phase() == GenericDiffractometer.PHASE_CENTRING

    def goto_centring_phase(self, wait=True):
        self.log.debug(" SETTING CENTRING PHASE ")

        self.phase_goingto = GenericDiffractometer.PHASE_CENTRING

        self.log.debug("  - close detector cover")
        self.detcover_hwobj.close()
        
        self.log.debug("  - setting backlight in")
        self.backlight_hwobj.set_in() 

        self.log.debug("  - putting collimator down")
        self.collimator_hwobj.set_position("Down")

        self.log.debug("  - setting beamstop out")
        self.beamstop_hwobj.set_position("Out")

        self.log.debug("  - moving yag down")
        self.yag_hwobj.set_position("Out")

        self.log.debug("  - moving pinhole down")
        if not self.ignore_pinhole:
            self.pinhole_hwobj.set_position("Down")

        if wait:
            self.wait_phase()

    def is_transfer_phase(self):
        return self.get_phase() == GenericDiffractometer.PHASE_TRANSFER

    def goto_transfer_phase(self,wait=True):

        self.log.debug(" SETTING TRANSFER PHASE ")
        self.phase_goingto = GenericDiffractometer.PHASE_TRANSFER
        self.moving_motors = True

        try:
            self.log.debug("  - close detector cover")
            self.detcover_hwobj.close()
    
            self.log.debug("  - setting backlight out")
            self.backlight_hwobj.set_out() 
    
            self.log.debug("  - putting collimator down")
            self.collimator_hwobj.set_position("Down")
    
            self.log.debug("  - setting beamstop out")
            self.beamstop_hwobj.set_position("Out")
    
            self.log.debug("  - moving yag down")
            self.yag_hwobj.set_position("Out")
    
            self.log.debug("  - moving pinhole down")
            if not self.ignore_pinhole:
                self.pinhole_hwobj.set_position("Down")
    
            self.log.debug("  - moving omega to 0")
    
            self.move_omega(0)
            self.restore_position("transfer")
    
            self.log.debug("  - moving gonio tower to 0")
        finally:
            self.moving_motors = False
            self.update_phase()

        if wait:
            self.wait_phase()

        # sampx to 0
        # sampy to 0
        # microx, microy to 0


    def detector_cover_open(self, wait=True):
        self.detcover_hwobj.open()
        if wait:
            self.wait_detcover(state="close")

    def detector_cover_close(self, wait=True):
        self.detcover_hwobj.close()
        if wait:
            self.wait_detcover(state="close")

    def wait_detcover(self, state, timeout=60):
        start_time = time.time()
        while time.time() - start_time > timeout:
            if state == "open" and self.detcover_hwobj.is_open():
                break
            elif state == "close" and self.detcover_hwobj.is_closed():
                break
            gevent.sleep(0.5)

    def is_collect_phase(self):
        return self.get_phase() == GenericDiffractometer.PHASE_COLLECTION

    def goto_collect_phase(self,wait=True):
        self.phase_goingto = GenericDiffractometer.PHASE_COLLECTION

        self.log.debug(" SETTING DATA COLLECTION PHASE ")
        # self.log.debug("  - open detector cover")
        self.log.debug("  - setting backlight out")
        self.log.debug("  - putting collimator up")
        self.log.debug("  - setting beamstop in")
        self.log.debug("  - moving yag down")

        # self.detcover_hwobj.open()
        self.backlight_hwobj.set_out() 
        self.collimator_hwobj.set_position("Up")
        self.beamstop_hwobj.set_position("In")
        self.yag_hwobj.set_position("Out")

        self.log.debug("=========  - checking pinhole ===============")

        # If the pinhole is Down set pinhole to 200
        if self.pinhole_hwobj.get_position() == "Down":
            print("Pinhole is down. Setting pinhole to 200.")
            self.pinhole_hwobj.set_position("200")
        
        
        # restore pinhole position is the role of save / restore at mounting
        # time. not of the collect phase
        # self.pinhole_hwobj.set_position("In")

        self.log.debug("  - checking gonio tower position ")

        if wait:
            self.wait_phase()

        
            

        # sampx to 0

    def goto_beam_phase(self, wait=True):
        self.phase_goingto = GenericDiffractometer.PHASE_BEAMLOCATION

        self.log.debug(" SETTING BEAM LOCATION PHASE ")

        self.log.debug("  - open detector cover")
        self.detcover_hwobj.open()
        self.log.debug("  - setting backlight out")
        self.backlight_hwobj.set_out() # out

        self.log.debug("  - putting collimator up")
        self.log.debug("  - setting beamstop in")
        self.log.debug("  - moving scintillator down")
        self.log.debug("  - checking pinhole ")
        self.log.debug("  - checking gonio tower position ")
        if wait:
            self.wait_phase()

    def update_phase(self, value=None):

        omega_pos = self.get_omega_position()

        cover_open = self.detcover_hwobj.is_open()
        cover_closed = self.detcover_hwobj.is_closed()
        blight_in = self.backlight_hwobj.is_in()
        blight_out = self.backlight_hwobj.is_out()
        collim = self.collimator_hwobj.get_position()
        bstop = self.beamstop_hwobj.get_position()
        pinh = self.pinhole_hwobj.get_position()
        yag = self.yag_hwobj.get_position()

        omega_moving = self.omega_hwobj.is_moving()
        cover_moving = self.detcover_hwobj.is_moving()
        light_moving = self.backlight_hwobj.is_moving()

        current_phase = GenericDiffractometer.PHASE_UNKNOWN
        missing = []

        if self.phase_goingto is GenericDiffractometer.PHASE_CENTRING:
            if not blight_in:
                missing.append("lightin")
            if not cover_closed:
                missing.append("cover_closed")
            if not collim == "Down":
                missing.append("collim_down")
            if not yag == "Out":
                missing.append("yag_out")
            if not bstop == "Out":
                missing.append("bstop_out")
            if not pinh == "Down" and not self.ignore_pinhole:
                missing.append("pinh_down")

            if not missing:
                current_phase = GenericDiffractometer.PHASE_CENTRING

        elif self.phase_goingto is GenericDiffractometer.PHASE_TRANSFER:
            if not blight_out:
                missing.append("lightout")
            if not cover_closed:
                missing.append("cover_closed")
            if not collim == "Down":
                missing.append("collim_down")
            if not bstop == "Out":
                missing.append("bstop_out")
            if not yag == "Out":
                missing.append("yag_out")
            if not pinh == "Down" and not self.ignore_pinhole:
                missing.append("pinh_down")
            if abs(omega_pos) >= 0.01:
                missing.append("omega_zero")

            if self.moving_motors:
                missing.append("motors_done")

            if not missing:
                self.log.debug("going to transfer done")
                current_phase = GenericDiffractometer.PHASE_TRANSFER
            else:
                self.log.debug("going to transfer. missing %s" % str(missing))

        elif self.phase_goingto is GenericDiffractometer.PHASE_COLLECTION:
            if not blight_out:
                missing.append("lightout")
            #if not cover_open:
            #    missing.append("cover_opened")
            if not collim == "Up":
                missing.append("collim_up")
            if not bstop == "In":
                missing.append("bstop_in")
            if not yag == "Out":
                missing.append("yag_out")

            if not missing:
                current_phase = GenericDiffractometer.PHASE_COLLECTION
        else:
            current_phase = GenericDiffractometer.PHASE_UNKNOWN

        # if blight_in and cover_closed and \
            # collim == "Down" and bstop == "Out" and \
            # yag == "Out" and pinh == "Down":
                # current_phase = GenericDiffractometer.PHASE_CENTRING
        # elif blight_out and cover_closed and \
             # collim == "Down" and bstop == "Out" and \
             # yag == "Out" and pinh == "Down" and \
             # abs(omega_pos) < 0.01:
                # current_phase = GenericDiffractometer.PHASE_TRANSFER
        # elif blight_out and cover_open and \
             # collim == "Up" and bstop == "In" and \
             # yag == "Out":
                # current_phase = GenericDiffractometer.PHASE_COLLECTION

        if self.phase_goingto == current_phase:
            self.log.debug("PHASE REACHED - %s" % self.phase_goingto)
            
            self.phase_goingto = None
       
        if current_phase == GenericDiffractometer.PHASE_UNKNOWN:
            if self.phase_goingto is not None:
                self.log.debug("PHASE (%s) NOT REACHED YET" % str(self.phase_goingto))
                self.log.debug("  waiting for: " + ",".join(missing))
        else:
            if self.current_phase != current_phase:
                self.log.debug("PHASE changed to %s" % current_phase)
                self.current_phase = current_phase
                self.emit("minidiffPhaseChanged", (self.current_phase,))

         
        # if omega_moving or cover_moving or light_moving:
         #    phase_state = self.PHASE_STATES.MOVING
        #else:
            #phase_state = self.PHASE_STATES.READY

        if self.phase_goingto:
            phase_state = self.PHASE_STATES.MOVING
        else:
            phase_state = self.PHASE_STATES.READY

        if phase_state != self.phase_state:
            self.emit("minidiffPhaseStateChanged", (phase_state,))
            self.phase_state = phase_state
            self.motor_state_changed()

    def save_position(self, position_name):
        saved_position = {}
        for motname in self.save_motor_list:
            saved_position[motname] = self.motor_hwobj_dict[motname].get_value()
        saved_position["pinhole"] = self.pinhole_hwobj.get_position()
        saved_position["backlight"] = self.backlight_hwobj.get_value()
        self._saved_position[position_name]= saved_position
        self.log.debug("P11NanoDiff - saving positions for %s" % position_name)
        for name,value in saved_position.items():
            self.log.debug("     %s - %s  " % (name, value))

    def wait_position_ready(self, timeout=70):
        t0 = time.time()

        while (time.time() - t0) < timeout:
            busy = False
            for motname in self.save_motor_list:
                if not self.motor_hwobj_dict[motname].is_ready():
                    busy = True
                    state = self.motor_hwobj_dict[motname].get_state()
                    self.log.debug("  - motor %s is not ready. it is %s" % (motname, str(state)))

            time.sleep(0.2)

            if not busy:
                break

        self.log.debug("P11NanoDiff -  motors ready ")

        while (time.time() - t0) < timeout:
            busy = False
            if not self.pinhole_hwobj.is_ready():
                busy = True
                self.log.debug(" - pinhole is not ready")
            if self.backlight_hwobj.is_moving():
                busy = True
                self.log.debug(" - backlight is not ready")

            if not busy:
                break
            time.sleep(0.2)

        if busy:
            self.log.error("Timeout waiting for motors to finish movement")

    def restore_position(self, position_name):
        self.log.debug("Restoring position for %s" % position_name)
        self.log.debug(" (available are: %s)" % self._saved_position.keys())
        positions =  self._saved_position.get(position_name, None)

        if positions: 
            for motname,position in positions.items():
                if motname not in ["pinhole", "backlight"]:
                    self.motor_hwobj_dict[motname].set_value(position)
                
            if 'pinhole' in self._saved_position[position_name]:
                pinh_pos = self._saved_position[position_name]["pinhole"]
                if not self.ignore_pinhole:
                    self.pinhole_hwobj.set_position(pinh_pos)
            if 'backlight' in self._saved_position[position_name]:
                light_value = self._saved_position[position_name]["backlight"]
                self.backlight_hwobj.set_value(light_value)

            self.wait_position_ready()
        else:
            self.log.error("No transfer positions saved for %s" % position_name)

        self.update_phase()


    def move_motors(self, motor_positions, timeout=15):
        """
        Moves diffractometer motors to the requested positions

        :param motors_dict: dictionary with motor names or hwobj
                            and target values.
        :type motors_dict: dict
        """
        if not isinstance(motor_positions, dict):
            motor_positions = motor_positions.as_dict()

        self.wait_device_ready(timeout)

        for motor in ['phiy', 'phiz']:
            if motor not in motor_positions:
                continue
            position = motor_positions[motor]
            self.log.debug(f"first moving translation motor '{motor}' to position {position}")

            motor_hwobj = self.motor_hwobj_dict.get(motor)
            if None in (motor_hwobj, position):
                continue
            motor_hwobj.set_value(position)
        gevent.sleep(0.1)
        self.wait_device_ready(timeout)
        self.log.debug(f"  translation movements DONE")

        for motor in ['sampx', 'sampy']:
            if motor not in motor_positions:
                continue
            position = motor_positions[motor]
            self.log.debug(f"then moving alignment motor '{motor}' to position {position}")

            motor_hwobj = self.motor_hwobj_dict.get(motor)
            if None in (motor_hwobj, position):
                continue
            motor_hwobj.set_value(position)
        gevent.sleep(0.1)
        self.wait_device_ready(timeout)
        self.log.debug(f"  alignment movements DONE")
        
        if 'phi' in motor_positions:
            self.log.debug(f"finally moving motor 'phi' to position {position}")
            position = motor_positions['phi']
            motor_hwobj = self.motor_hwobj_dict.get('phi')
            if None not in (motor_hwobj, position):
                motor_hwobj.set_value(position)
                gevent.sleep(0.1)
                self.wait_device_ready(timeout)
            self.log.debug('   phi move DONE')

        # is there anything left?
        for motor in motor_positions.keys():
            if motor in ['phiy', 'phiz', 'phi', 'sampx', 'sampy']:
                continue
            position = motor_positions[motor]
            self.log.debug(f"moving remaining motor {motor} to position {position}")
            """
            if isinstance(motor, (str, unicode)):
                logging.getLogger("HWR").debug(" Moving %s to %s" % (motor, position))
            else:
                logging.getLogger("HWR").debug(
                    " Moving %s to %s" % (str(motor.name()), position)
                )
            """
            if isinstance(motor, (str, unicode)):
                motor_role = motor
                motor = self.motor_hwobj_dict.get(motor_role)
                # del motor_positions[motor_role]
                if None in (motor, position):
                    continue
                # motor_positions[motor] = position
            motor.set_value(position)
        self.wait_device_ready(timeout)

        if self.delay_state_polling is not None and self.delay_state_polling > 0:
            # delay polling for state in the
            # case of controller not reporting MOVING inmediately after cmd
            gevent.sleep(self.delay_state_polling)

        self.wait_device_ready(timeout)

