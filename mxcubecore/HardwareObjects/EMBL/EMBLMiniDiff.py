#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import time
import logging
import gevent

try:
    import lucid2 as lucid
except ImportError:
    try:
        import lucid
    except ImportError:
        logging.warning("Could not find autocentring library, " + \
                        "automatic centring is disabled")

from GenericDiffractometer import GenericDiffractometer
from HardwareRepository.TaskUtils import *


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


class EMBLMiniDiff(GenericDiffractometer):
    """
    Description:
    """	

    AUTOMATIC_CENTRING_IMAGES = 6

    def __init__(self, *args):
        """
        Description:
        """ 
        GenericDiffractometer.__init__(self, *args)

        # Hardware objects ---------------------------------------------------- 
        self.zoom_motor_hwobj = None
        self.camera_hwobj = None
        self.omega_reference_motor = None
        self.centring_hwobj = None
        self.minikappa_correction_hwobj = None

        # Channels and commands -----------------------------------------------
        self.chan_calib_x = None
        self.chan_calib_y = None
        self.chan_current_phase = None
        self.chan_head_type = None
        self.chan_fast_shutter_is_open = None
        self.chan_state = None
        self.chan_sync_move_motors = None
        self.chan_scintillator_position = None
        self.chan_capillary_position = None
        self.cmd_start_set_phase = None
        self.cmd_start_auto_focus = None   
        self.cmd_get_omega_scan_limits = None
        self.cmd_save_centring_positions = None

        # Internal values -----------------------------------------------------
        self.use_sc = False
        self.omega_reference_pos  = [0, 0]
       
    def init(self):
        """
        Description:
        """
        GenericDiffractometer.init(self)
        self.centring_status = {"valid": False}

        self.chan_state = self.getChannelObject('State')
        self.current_state = self.chan_state.getValue()
        self.chan_state.connectSignal("update", self.state_changed)

        self.chan_calib_x = self.getChannelObject('CoaxCamScaleX')
        self.chan_calib_y = self.getChannelObject('CoaxCamScaleY')
        self.update_pixels_per_mm()

        self.chan_head_type = self.getChannelObject('HeadType')
        self.head_type = self.chan_head_type.getValue()

        self.chan_current_phase = self.getChannelObject('CurrentPhase')
        self.connect(self.chan_current_phase, "update", self.current_phase_changed)

        self.chan_fast_shutter_is_open = self.getChannelObject('FastShutterIsOpen')
        self.chan_fast_shutter_is_open.connectSignal("update", self.fast_shutter_state_changed)
       
        self.chan_scintillator_position = self.getChannelObject('ScintillatorPosition')
        self.chan_capillary_position = self.getChannelObject('CapillaryPosition')

        self.cmd_start_set_phase = self.getCommandObject('startSetPhase')
        self.cmd_start_auto_focus = self.getCommandObject('startAutoFocus')
        self.cmd_get_omega_scan_limits = self.getCommandObject('getOmegaMotorDynamicScanLimits')
        self.cmd_save_centring_positions = self.getCommandObject('saveCentringPositions')

        self.centring_hwobj = self.getObjectByRole('centring')
        self.minikappa_correction_hwobj = self.getObjectByRole('minikappa_correction')

        self.zoom_motor_hwobj = self.getObjectByRole('zoom')
        self.connect(self.zoom_motor_hwobj,
                     'positionChanged',
                     self.zoom_position_changed)
        self.connect(self.zoom_motor_hwobj,
                    'predefinedPositionChanged',
                    self.zoom_motor_predefined_position_changed)

        self.connect(self.motor_hwobj_dict['phi'],
                     "positionChanged",
                     self.phi_motor_moved) 
        self.connect(self.motor_hwobj_dict['phiy'],
                     "positionChanged",
                     self.phiy_motor_moved)
        self.connect(self.motor_hwobj_dict['phiz'],
                     "positionChanged",
                     self.phiz_motor_moved)
        self.connect(self.motor_hwobj_dict['kappa'],
                     "positionChanged",
                     self.kappa_motor_moved)
        self.connect(self.motor_hwobj_dict['kappa_phi'],
                     "positionChanged",
                     self.kappa_phi_motor_moved)
        self.connect(self.motor_hwobj_dict['sampx'],
                     "positionChanged",
                     self.sampx_motor_moved)
        self.connect(self.motor_hwobj_dict['sampy'],
                     "positionChanged",
                     self.sampy_motor_moved)

        self.omega_reference_par = eval(self.getProperty("omega_reference"))
        self.omega_reference_motor = self.getObjectByRole(self.omega_reference_par["motor_name"])
        self.connect(self.omega_reference_motor,
                     'positionChanged',
                     self.omega_reference_motor_moved)

        self.use_sc = self.getProperty("use_sample_changer")
  
    def use_sample_changer(self):
        """
        Description:
        """
        return self.use_sc

    def state_changed(self, state):
        self.current_state = state
        self.emit("minidiffStateChanged", (self.current_state))
        self.emit("minidiffStatusChanged", (self.current_state))

    def zoom_position_changed(self, value):
        self.update_pixels_per_mm()
        self.current_motor_positions["zoom"] = value
        self.refresh_omega_reference_position()

    def zoom_motor_predefined_position_changed(self, position_name, offset):
        self.update_pixels_per_mm()
        self.emit('zoomMotorPredefinedPositionChanged',
               (position_name, offset, ))

    def omega_reference_add_constraint(self):
        """
        Descript. :
        """
        if self.omega_reference_par is None or self.beam_position is None: 
            return
        if self.omega_reference_par["camera_axis"].lower() == "x":
            on_beam = (self.beam_position[0] -  self.zoom_centre['x']) * \
                      self.omega_reference_par["direction"] / self.pixels_per_mm_x + \
                      self.omega_reference_par["position"]
        else:
            on_beam = (self.beam_position[1] -  self.zoom_centre['y']) * \
                      self.omega_reference_par["direction"] / self.pixels_per_mm_y + \
                      self.omega_reference_par["position"]
        self.centring_hwobj.appendMotorConstraint(self.omega_reference_motor, on_beam)

    def omega_reference_motor_moved(self, pos):
        """
        Descript. :
        """
        if self.omega_reference_par["camera_axis"].lower() == "x":
            pos = self.omega_reference_par["direction"] * \
                  (pos - self.omega_reference_par["position"]) * \
                  self.pixels_per_mm_x + self.zoom_centre['x']
            self.reference_pos = (pos, -10)
        else:
            pos = self.omega_reference_par["direction"] * \
                  (pos - self.omega_reference_par["position"]) * \
                  self.pixels_per_mm_y + self.zoom_centre['y']
            self.reference_pos = (-10, pos)
        self.emit('omegaReferenceChanged', (self.reference_pos,))

    def fast_shutter_state_changed(self, is_open):
        """
        Description:
        """
        self.fast_shutter_is_open = is_open
        if is_open:
            msg = "Opened"
        else:
            msg = "Closed"
        self.emit('minidiffShutterStateChanged', (self.fast_shutter_is_open, msg))

    def phi_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["phi"] = pos
        self.emit("phiMotorMoved", pos)

    def phiy_motor_moved(self, pos):
        self.current_motor_positions["phiy"] = pos

    def phiz_motor_moved(self, pos):
        self.current_motor_positions["phiz"] = pos

    def sampx_motor_moved(self, pos):
        self.current_motor_positions["sampx"] = pos

    def sampy_motor_moved(self, pos):
        self.current_motor_positions["sampy"] = pos

    def kappa_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["kappa"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()
        self.emit("kappaMotorMoved", pos)

    def kappa_phi_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["kappa_phi"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()
        self.emit("kappaPhiMotorMoved", pos)

    def refresh_omega_reference_position(self):
        """
        Descript. :
        """
        if self.omega_reference_motor is not None:
            reference_pos = self.omega_reference_motor.getPosition()
            self.omega_reference_motor_moved(reference_pos)

    def update_pixels_per_mm(self, *args):
        """
        Descript. :
        """
        if self.chan_calib_x:
            self.pixels_per_mm_x = 1.0 / self.chan_calib_x.getValue()
            self.pixels_per_mm_y = 1.0 / self.chan_calib_y.getValue() 
            self.emit('pixelsPerMmChanged', ((self.pixels_per_mm_x, 
                                              self.pixels_per_mm_y),))

    def set_phase(self, phase, timeout=None):
        """
        Description:
        """
        if timeout:
            self.ready_event.clear()
            set_phase_task = gevent.spawn(self.execute_server_task,
                                          self.cmd_start_set_phase,
                                          timeout,
                                          phase)
            self.ready_event.wait()
            self.ready_event.clear()
        else:
            self.cmd_start_set_phase(phase)

    def start_auto_focus(self, timeout=None):
        """
        Descript. :
        """
        if timeout:
            self.ready_event.clear()
            set_phase_task = gevent.spawn(self.execute_server_task,
                                          self.cmd_start_auto_focus(),
                                          timeout)
            self.ready_event.wait()
            self.ready_event.clear()
        else:
            self.cmd_start_auto_focus() 

    def emit_diffractometer_moved(self, *args):
        """
        Descript. :
        """
        self.emit("diffractometerMoved", ())

    def invalidate_centring(self):
        """
        Descript. :
        """   
        if self.current_centring_procedure is None \
         and self.centring_status["valid"]:
            self.centring_status = {"valid": False}
            self.emit_progress_message("")
            self.emit('centringInvalid', ())

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        """
        Descript. :
        """
        self.centring_hwobj.initCentringProcedure()
        self.centring_hwobj.appendCentringDataPoint({
                   "X" : (x - self.beam_position[0]) / self.pixels_per_mm_x,
                   "Y" : (y - self.beam_position[1]) / self.pixels_per_mm_y})
        self.omega_reference_add_constraint()
        pos = self.centring_hwobj.centeredPosition()  
        if return_by_names:
            pos = self.convert_from_obj_to_name(pos)
        return pos

    def move_to_beam(self, x, y, omega=None):
        """
        Descript. : function to create a centring point based on all motors
                    positions.
        """  
        if self.current_phase != "BeamLocation":
            GenericDiffractometer.move_to_beam(self, x, y, omega) 
        else:
            logging.getLogger("HWR").debug("Diffractometer: Move to screen" +\
               " position disabled in BeamLocation phase.")

    def manual_centring(self):
        """
        Descript. :
        """
        if not self.in_plate_mode():
            self.motor_hwobj_dict['phi'].move(40)

        self.centring_hwobj.initCentringProcedure()
        #self.head_type = self.chan_head_type.getValue()
        for click in range(3):
            self.user_clicked_event = gevent.event.AsyncResult()
            x, y = self.user_clicked_event.get()
            self.centring_hwobj.appendCentringDataPoint(
                 {"X": (x - self.beam_position[0])/ self.pixels_per_mm_x,
                  "Y": (y - self.beam_position[1])/ self.pixels_per_mm_y})
            if self.in_plate_mode():
                #dynamic_limits = self.phi_motor_hwobj.getDynamicLimits()
                dynamic_limits = self.get_osc_dynamic_limits()
                if click == 0:
                    self.motor_hwobj_dict['phi'].move(dynamic_limits[0] + 0.5)
                elif click == 1:
                    self.motor_hwobj_dict['phi'].move(dynamic_limits[1] - 0.5)
            else:
                if click < 2:
                    self.motor_hwobj_dict['phi'].moveRelative(90)
        self.omega_reference_add_constraint()
        return self.centring_hwobj.centeredPosition(return_by_name=False)

    def automatic_centring(self):
        """Automatic centring procedure. Rotates n times and executes
           centring algorithm. Optimal scan position is detected.
        """
    
        surface_score_list = []
        self.zoom_motor_hwobj.moveToPosition("Zoom 3")
        self.centring_hwobj.initCentringProcedure()
        for image in range(EMBLMiniDiff.AUTOMATIC_CENTRING_IMAGES):
            x, y, score = self.find_loop()
            if x > -1 and y > -1:
                self.centring_hwobj.appendCentringDataPoint(
                    {"X": (x - self.beam_position[0])/ self.pixels_per_mm_x,
                     "Y": (y - self.beam_position[1])/ self.pixels_per_mm_y})
            surface_score_list.append(score)
            self.motor_hwobj_dict['phi'].moveRelative(\
                 360.0 / EMBLMiniDiff.AUTOMATIC_CENTRING_IMAGES)
            self.wait_device_ready(5)
        self.omega_reference_add_constraint()
        return self.centring_hwobj.centeredPosition(return_by_name=False)

    def motor_positions_to_screen(self, centred_positions_dict):
        """
        Descript. :
        """
        c = centred_positions_dict

        #kappa = self.current_motor_positions["kappa"] 
        #phi = self.current_motor_positions["kappa_phi"] 

        kappa = self.motor_hwobj_dict['kappa'].getPosition()
        phi = self.motor_hwobj_dict['kappa_phi'].getPosition()
        #IK TODO remove this director call

        if (c['kappa'], c['kappa_phi']) != (kappa, phi) \
         and self.minikappa_correction_hwobj is not None:
            #c['sampx'], c['sampy'], c['phiy']
            c['sampx'], c['sampy'], c['phiy'] = self.minikappa_correction_hwobj.shift(
            c['kappa'], c['kappa_phi'], [c['sampx'], c['sampy'], c['phiy']], kappa, phi)
        xy = self.centring_hwobj.centringToScreen(c)
        if xy:
            x = (xy['X'] + c['beam_x']) * self.pixels_per_mm_x + \
                 self.zoom_centre['x']
            y = (xy['Y'] + c['beam_y']) * self.pixels_per_mm_y + \
                 self.zoom_centre['y']
            return x, y
 
    def move_to_centred_position(self, centred_position):
        """
        Descript. :
        """
        if self.current_phase != "BeamLocation":
            try:
                x, y = centred_position.beam_x, centred_position.beam_y
                dx = (self.beam_position[0] - self.zoom_centre['x']) / \
                      self.pixels_per_mm_x - x
                dy = (self.beam_position[1] - self.zoom_centre['y']) / \
                      self.pixels_per_mm_y - y
                motor_pos = {self.motor_hwobj_dict['sampx']: centred_position.sampx,
                             self.motor_hwobj_dict['sampy']: centred_position.sampy,
                             self.motor_hwobj_dict['phi']: centred_position.phi,
                             self.motor_hwobj_dict['phiy']: centred_position.phiy + \
                                  self.centring_hwobj.camera2alignmentMotor(\
                                       self.motor_hwobj_dict['phiy'], \
                                       {"X" : dx, "Y" : dy}), 
                             self.motor_hwobj_dict['phiz']: centred_position.phiz + \
                                  self.centring_hwobj.camera2alignmentMotor(\
                                       self.motor_hwobj_dict['phiz'], \
                                       {"X" : dx, "Y" : dy}),
                             self.motor_hwobj_dict['kappa']: centred_position.kappa,
                             self.motor_hwobj_dict['kappa_phi']: centred_position.kappa_phi}
                self.move_to_motors_positions(motor_pos)
            except:
                logging.exception("Could not move to centred position")
        else:
            logging.getLogger("HWR").debug("Move to centred position disabled in BeamLocation phase.")

    def move_kappa_and_phi(self, kappa, kappa_phi, wait=False):
        """
        Descript. :
        """
        try:
            return self.move_kappa_and_phi_procedure(kappa, kappa_phi, wait = wait)
        except:
            logging.exception("Could not move kappa and kappa_phi")
    
    @task
    def move_kappa_and_phi_procedure(self, new_kappa, new_kappa_phi):
        """
        Descript. :
        """ 
        kappa = self.motor_hwobj_dict['kappa'].getPosition()
        kappa_phi = self.motor_hwobj_dict['kappa_phi'].getPosition()
        motor_pos_dict = {}

        if (kappa, kappa_phi ) != (new_kappa, new_kappa_phi) \
         and self.minikappa_correction_hwobj is not None:
            sampx = self.motor_hwobj_dict['sampx'].getPosition()
            sampy = self.motor_hwobj_dict['sampy'].getPosition()
            phiy = self.motor_hwobj_dict['phiy'].getPosition()
            new_sampx, new_sampy, new_phiy = self.minikappa_correction_hwobj.shift( 
                 kappa, kappa_phi, [sampx, sampy, phiy] , new_kappa, new_kappa_phi)
            
            motor_pos_dict[self.motor_hwobj_dict['kappa']] = new_kappa
            motor_pos_dict[self.motor_hwobj_dict['kappa_phi']] = new_kappa_phi
            motor_pos_dict[self.motor_hwobj_dict['sampx']] = new_sampx
            motor_pos_dict[self.motor_hwobj_dict['sampy']] = new_sampy
            motor_pos_dict[self.motor_hwobj_dict['phiy']] = new_phiy

            self.move_motors(motor_pos_dict, timeout=30)
 
    def convert_from_obj_to_name(self, motor_pos):
        motors = {}
        for motor_role in ('phiy', 'phiz', 'sampx', 'sampy', 'zoom',
                           'phi', 'focus', 'kappa', 'kappa_phi'):
            mot_obj = self.getObjectByRole(motor_role)
            try:
                motors[motor_role] = motor_pos[mot_obj]
            except KeyError:
                motors[motor_role] = mot_obj.getPosition()
        motors["beam_x"] = (self.beam_position[0] - \
                            self.zoom_centre['x'] )/self.pixels_per_mm_y
        motors["beam_y"] = (self.beam_position[1] - \
                            self.zoom_centre['y'] )/self.pixels_per_mm_x
        return motors
 

    def visual_align(self, point_1, point_2):
        """
        Descript. :
        """
        if self.in_plate_mode():
            logging.getLogger("HWR").info("EMBLMiniDiff: Visual align not available in Plate mode") 
        else:
            t1 = [point_1.sampx, point_1.sampy, point_1.phiy]
            t2 = [point_2.sampx, point_2.sampy, point_2.phiy]
            kappa = self.motor_hwobj_dict['kappa'].getPosition()
            phi = self.motor_hwobj_dict['kappa_phi'].getPosition()
            new_kappa, new_phi, (new_sampx, new_sampy, new_phiy) = \
                 self.minikappa_correction_hwobj.alignVector(t1,t2,kappa,phi)
            self.move_to_motors_positions({self.motor_hwobj_dict['kappa'] : new_kappa, 
                                           self.motor_hwobj_dict['kappa_phi'] : new_phi, 
                                           self.motor_hwobj_dict['sampx'] : new_sampx,
                                           self.motor_hwobj_dict['sampy'] : new_sampy, 
                                           self.motor_hwobj_dict['phiy'] : new_phiy})

    def update_values(self):
        """
        Description:
        """
        self.emit('minidiffPhaseChanged', (self.current_phase, ))            
        self.emit('omegaReferenceChanged', (self.reference_pos,))
        self.emit('minidiffShutterStateChanged', (self.fast_shutter_is_open, ))

    def toggle_fast_shutter(self):
        """
        Description:
        """
        if self.chan_fast_shutter_is_open is not None:
            self.chan_fast_shutter_is_open.setValue(not self.fast_shutter_is_open) 

    def find_loop(self):
        """
        Description:
        """
        image_array = self.camera_hwobj.get_snapshot(return_as_array=True)
        (info, x, y) = lucid.find_loop(image_array)
        surface_score = 10
        return x, y, surface_score

    def move_omega_relative(self, relative_angle):
        """
        Description:
        """
        self.motor_hwobj_dict['phi'].syncMoveRelative(relative_angle, 5)

    def get_scan_limits(self, speed=None):
        """
        Gets scan limits. Necessary for example in the plate mode
        where osc range is limited
        """
        if speed == None:
            speed = 0
        return self.cmd_get_omega_scan_limits(speed)

    def close_kappa(self):
        """
        Descript. :
        """
        gevent.spawn(self.close_kappa_task) 

    def close_kappa_task(self):
        """Close kappa task
        """
        self.move_kappa_and_phi_procedure(0, 0)
        self.motor_hwobj_dict['kappa'].homeMotor()
        self.wait_device_ready(30)
        #self.kappa_phi_motor_hwobj.homeMotor()

    def set_zoom(self, position): 
        """
        """
        self.zoom_motor_hwobj.moveToPosition(position)

    def get_point_from_line(self, point_one, point_two, frame_num, frame_total):
        """
        Descript. : method used to get a new motor position based on a position
                    between two positions. As arguments both motor positions are
                    given. frame_num and frame_total is used estimate new point position
                    Helical line goes from point_one to point_two.
                    In this direction also new position is estimated
        """
        new_point = {}
        point_one = point_one.as_dict()
        point_two = point_two.as_dict()
        for motor in point_one.keys():
            new_motor_pos = point_one[motor] + (point_two[motor] - point_one[motor]) * \
                     frame_num / float(frame_total)
            new_point[motor] = new_motor_pos
        return new_point

    def get_osc_dynamic_limits(self):
        return self.motor_hwobj_dict['phi'].getDynamicLimits()

    def get_osc_range_limits(self, num_images, exp_time):
        motor_acc_const = 5
        motor_acc_time = num_images / exp_time / motor_acc_const
        min_acc_time = 0.0015
        acc_time = min(motor_acc_time, min_acc_time)

        shutter_time = 3.7 / 1000.
        max_limit = num_images / exp_time * (acc_time+2*shutter_time + 0.2) / 2

        return [0, max_limit]

    def get_scintillator_position(self):
        return self.chan_scintillator_position.getValue()

    def set_scintillator_position(self, position):
        self.chan_scintillator_position.setValue(position)
        with gevent.Timeout(5, Exception("Timeout waiting for scintillator position")):
            while position != self.get_scintillator_position():
                gevent.sleep(0.01)

    def get_capillary_position(self):
        return self.chan_capillary_position.getValue()

    def set_capillary_position(self, position):
        self.chan_capillary_position.setValue(position)
        with gevent.Timeout(5, Exception("Timeout waiting for capillary position")):
            while position != self.get_capillary_position():
                gevent.sleep(0.01)

    def zoom_in(self):
        self.zoom_motor_hwobj.zoom_in()

    def zoom_out(self):
        self.zoom_motor_hwobj.zoom_out()
