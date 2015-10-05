"""
EMBLMinidiff Class
"""
import os
import copy
import time
import logging
import tempfile
import gevent
from gevent.event import AsyncResult
from Qub.Tools import QubImageSave

import queue_model_objects_v1 as queue_model_objects

from HardwareRepository import HardwareRepository
from HardwareRepository.TaskUtils import *
from HardwareRepository.BaseHardwareObjects import Equipment

class myimage:
    """
    Description:	
    """
    def __init__(self, drawing):
        """
        Description:
        """ 
        self.drawing = drawing
        matrix = self.drawing.matrix()
        self.zoom = 1
        if matrix is not None:
            self.zoom = matrix.m11()
        self.image = self.drawing.getPPP()
        fd, name = tempfile.mkstemp()
        os.close(fd)
        QubImageSave.save(name, self.image, self.drawing.canvas(), \
                          self.zoom, "JPEG")
        f = open(name, "r")
        self.image_copy = f.read()
        f.close()
        os.unlink(name)

    def __str__(self):
        """
        Description:
        """
        return self.image_copy

class EMBLMiniDiff(Equipment):
    """
    Description:
    """	
    MANUAL3CLICK_MODE = "Manual 3-click"
    C3D_MODE = "Computer automatic"
    MOVE_TO_BEAM_MODE = "Move to Beam"

    MINIKAPPA = "MiniKappa"
    PLATE = "Plate"
    SC = "SC"

    def __init__(self, *args):
        """
        Description:
        """ 
        Equipment.__init__(self, *args)

        queue_model_objects.CentredPosition.\
             set_diffractometer_motor_names("phi", "focus", "phiz",  
                                            "phiy", "zoom", "sampx", 
                                            "sampy", "kappa", "kappa_phi",
                                            "beam_x", "beam_y")
        self.phiMotor = None
        self.phizMotor = None
        self.phiyMotor = None
        self.lightMotor = None
        self.zoomMotor = None
        self.sampleXMotor = None
        self.sampleYMotor = None
        self.camera_hwobj = None
        self.focusMotor = None
        self.kappaMotor = None
        self.kappaPhiMotor = None
        self.omega_reference_motor = None
        self.sample_changer_hwobj = None
        self.beam_info_hwobj = None
        self.centring_hwobj = None
        self.minikappa_correction_hwobj = None
  
        self.chan_calib_x = None
        self.chan_calib_y = None
        self.chan_head_type = None
        self.chan_fast_shutter_is_open = None
        self.chan_sync_move_motors = None
        self.cmd_start_set_phase = None
        self.cmd_start_auto_focus = None   

        self.beam_position = None
        self.zoom_centre = None
        self.pixels_per_mm_x = None
        self.pixels_per_mm_y = None
        self.image_width = None
        self.image_height = None
        self.current_sample_info = None
        self.cancel_centring_methods = None
        self.current_centring_procedure = None
        self.current_centring_method = None
        self.current_positions_dict = None
        self.current_state_dict = None
        self.current_phase = None
        self.fast_shutter_is_open = None
        self.head_type = None
        self.centring_methods = None
        self.centring_status = None
        self.centring_time = None
        self.user_confirms_centring = None
        self.user_clicked_event = None
        self.omega_reference_par = None
        self.move_to_motors_positions_task = None
        self.move_to_motors_positions_procedure = None
        self.ready_event = None
        self.in_collection = None
        self.phase_list = []
        self.reference_pos = None
        
        self.connect(self, 'equipmentReady', self.equipmentReady)
        self.connect(self, 'equipmentNotReady', self.equipmentNotReady)     

    def init(self):
        """
        Description:
        """
        self.ready_event = gevent.event.Event()
        self.centring_methods = {
             EMBLMiniDiff.MANUAL3CLICK_MODE: self.start_3Click_centring,
             EMBLMiniDiff.C3D_MODE: self.start_automatic_centring}
        self.cancel_centring_methods = {}
        self.current_positions_dict = {'phiy'  : 0, 'phiz' : 0, 'sampx' : 0,
                                       'sampy' : 0, 'zoom' : 0, 'phi' : 0,
                                       'focus' : 0, 'kappa': 0, 'kappa_phi': 0,
                                       'beam_x': 0, 'beam_y': 0}
        self.current_state_dict = {'sampx' : "", 'sampy' : "", 'phi' : "",
                                   'kappa': "", 'kappa_phi': ""}
        self.centring_status = {"valid": False}
        self.centring_time = 0 
        self.user_confirms_centring = True 
        self.user_clicked_event = AsyncResult()
        self.head_type = "Plate"

        self.camera_hwobj = self.getDeviceByRole('camera')   
        self.centring_hwobj = self.getDeviceByRole('centring')
        self.minikappa_correction_hwobj = self.getDeviceByRole('minikappa_correction')

        self.chan_calib_x = self.getChannelObject('CoaxCamScaleX')
        self.chan_calib_y = self.getChannelObject('CoaxCamScaleY') 
        self.chan_head_type = self.getChannelObject('HeadType')
        if self.chan_head_type is not None:
            self.head_type = self.chan_head_type.getValue()
        self.chan_current_phase = self.getChannelObject('CurrentPhase')
        self.chan_fast_shutter_is_open = self.getChannelObject('FastShutterIsOpen')
        if self.chan_fast_shutter_is_open is not None: 
            self.chan_fast_shutter_is_open.connectSignal("update", self.fast_shutter_state_changed)
       
        self.cmd_start_set_phase = self.getCommandObject('startSetPhase')
        self.cmd_start_auto_focus = self.getCommandObject('startAutoFocus')

        self.phiMotor = self.getDeviceByRole('phi')
        self.phizMotor = self.getDeviceByRole('phiz')
        self.phiyMotor = self.getDeviceByRole('phiy')
        self.zoomMotor = self.getDeviceByRole('zoom')
        self.lightMotor = self.getDeviceByRole('light')
        self.focusMotor = self.getDeviceByRole('focus')
        self.sampleXMotor = self.getDeviceByRole('sampx')
        self.sampleYMotor = self.getDeviceByRole('sampy')
       
        if self.head_type == "MiniKappa":
            self.kappaMotor = self.getDeviceByRole('kappa')
            self.kappaPhiMotor = self.getDeviceByRole('kappa_phi')

            if self.kappaMotor is not None:
                self.connect(self.kappaMotor, 'stateChanged', self.kappa_motor_state_changed)
                self.connect(self.kappaMotor, "positionChanged", self.kappa_motor_moved)
            else:
                logging.getLogger("HWR").error('EMBLMiniDiff: kappa motor is not defined')

            if self.kappaPhiMotor is not None:
                self.connect(self.kappaPhiMotor, 'stateChanged', self.kappa_phi_motor_state_changed)
                self.connect(self.kappaPhiMotor, 'positionChanged', self.kappa_phi_motor_moved)
            else:
                logging.getLogger("HWR").error('EMBLMiniDiff: kappa phi motor is not defined')
        else:
            logging.getLogger("HWR").debug('EMBLMinidiff: Kappa and Phi motors not initialized (Plate mode detected).')

        if self.chan_current_phase is not None:
            self.connect(self.chan_current_phase, "update", self.current_phase_changed)
        else:
            logging.getLogger("HWR").debug('EMBLMinidiff: Current phase channel not defined') 

        self.beam_info_hwobj = HardwareRepository.HardwareRepository().\
                                getHardwareObject(self.getProperty("beaminfo"))
        if self.beam_info_hwobj is not None:  
            self.connect(self.beam_info_hwobj, 'beamPosChanged', self.beam_position_changed)
        else:
            logging.getLogger("HWR").debug('EMBLMinidiff: Beaminfo is not defined')

        if self.centring_hwobj is None:
            logging.getLogger("HWR").debug('EMBLMinidiff: Centring math is not defined')

        if self.minikappa_correction_hwobj is None:
            logging.getLogger("HWR").debug('EMBLMinidiff: Minikappa correction is not defined')
        
        if self.phiMotor is not None:
            self.connect(self.phiMotor, 'stateChanged', self.phi_motor_state_changed)
            self.connect(self.phiMotor, "positionChanged", self.phi_motor_moved)
        else:
            logging.getLogger("HWR").error('EMBLMiniDiff: Phi motor is not defined')

        if self.phizMotor is not None:
            self.connect(self.phizMotor, 'stateChanged', self.phiz_motor_state_changed)
            self.connect(self.phizMotor, 'positionChanged', self.phiz_motor_moved)
        else:
            logging.getLogger("HWR").error('EMBLMiniDiff: Phiz motor is not defined')

        if self.phiyMotor is not None:
            self.connect(self.phiyMotor, 'stateChanged', self.phiy_motor_state_changed)
            self.connect(self.phiyMotor, 'positionChanged', self.phiy_motor_moved)
        else:
            logging.getLogger("HWR").error('EMBLMiniDiff: Phiy motor is not defined')

        if self.zoomMotor is not None:
            self.connect(self.zoomMotor, 'predefinedPositionChanged', 
                                          self.zoom_motor_predefined_position_changed)
            self.connect(self.zoomMotor, 'stateChanged', self.zoom_motor_state_changed)
        else:
            logging.getLogger("HWR").error('EMBLMiniDiff: Zoom motor is not defined')

        if self.sampleXMotor is not None:
            self.connect(self.sampleXMotor, 'stateChanged', self.sampleX_motor_state_changed)
            self.connect(self.sampleXMotor, 'positionChanged', self.sampleX_motor_moved)
        else:
            logging.getLogger("HWR").error('EMBLMiniDiff: Sampx motor is not defined')

        if self.sampleYMotor is not None:
            self.connect(self.sampleYMotor, 'stateChanged', self.sampleY_motor_state_changed)
            self.connect(self.sampleYMotor, 'positionChanged', self.sampleY_motor_moved)
        else:
            logging.getLogger("HWR").error('EMBLMiniDiff: Sampx motor is not defined')

        if self.focusMotor is not None:
            self.connect(self.focusMotor, 'positionChanged', self.focus_motor_moved)

        if self.zoomMotor is not None:
            self.connect(self.zoomMotor, 'positionChanged', self.zoom_motor_moved)

        if self.camera_hwobj is None:
            logging.getLogger("HWR").error('EMBLMiniDiff: Camera is not defined')
        else:
            self.image_height = self.camera_hwobj.getHeight()
            self.image_width = self.camera_hwobj.getWidth()

        try: 
            self.zoom_centre = eval(self.getProperty("zoomCentre"))
        except:              
            if self.image_width is not None and self.image_height is not None:
                self.zoom_centre = {'x': self.image_width / 2,'y' : self.image_height / 2}
                self.beam_position = [self.image_width / 2, self.image_height / 2]
                logging.getLogger("HWR").warning('EMBLMiniDiff: Zoom center is ' +\
                       'not defined continuing with the middle: %s' % self.zoom_centre)
            else:
                logging.getLogger("HWR").warning('EMBLMiniDiff: Neither zoom centre nor camera size iz defined')

        try:
            self.omega_reference_par = eval(self.getProperty("omegaReference"))
            self.omega_reference_motor = self.getDeviceByRole(self.omega_reference_par["motor_name"])
            if self.omega_reference_motor is not None:
                self.connect(self.omega_reference_motor, 'positionChanged', self.omega_reference_motor_moved)
        except:
            logging.getLogger("HWR").warning('EMBLMiniDiff: Omega axis is not defined')
  
        #Compatibility
        self.getCentringStatus = self.get_centring_status

        self.reversing_rotation = self.getProperty("reversingRotation")
        try:
            self.grid_direction = eval(self.getProperty("gridDirection"))
        except:
            self.grid_direction = {"fast": (0, 1), "slow": (1, 0)}
            logging.getLogger("HWR").warning('EMBLMiniDiff: Grid direction is not defined. Using default.')

        try:
            self.phase_list = eval(self.getProperty("phaseList"))
        except:
            self.phase_list = []  
         

    def in_plate_mode(self):
        plate_mode = False
        if self.chan_head_type is not None:
            plate_mode = self.head_type == "Plate"
        return plate_mode

    def in_sc_mode(self):
        return False

    def get_grid_direction(self):
        """
        Descript. :
        """
        return self.grid_direction

    def is_reversing_rotation(self):
        return self.reversing_rotation == True 

    def equipmentReady(self):
        """
        Descript. :
        """
        self.emit('minidiffReady', ())

    def equipmentNotReady(self):
        """
        Descript. :
        """
        self.emit('minidiffNotReady', ())

    def isReady(self):
        """
        Descript. :
        """  
        if self.isValid():
            for motor in (self.sampleXMotor, 
                          self.sampleYMotor, 
                          self.zoomMotor,
                          self.phiMotor, 
                          self.phizMotor, 
                          self.phiyMotor,
                          self.kappaMotor,
                          self.kappaPhiMotor):
                if motor is not None:
                    if motor.motorIsMoving():
                        return False
            return True
        else:
            return False

    def isValid(self):
        """
        Descript. :
        """
        return self.sampleXMotor is not None and \
            self.sampleYMotor is not None and \
            self.zoomMotor is not None and \
            self.phiMotor is not None and \
            self.phizMotor is not None and \
            self.phiyMotor is not None

    def current_phase_changed(self, phase):
        """
        Descript. :
        """ 
        self.current_phase = phase
        self.emit('minidiffPhaseChanged', (phase, )) 
        self.refresh_video()

    def get_head_type(self):
        """
        Descript. :
        """
        self.chan_head_type.getValue()

    def get_current_phase(self):
        """
        Descript. :
        """
        return self.current_phase 

    def beam_position_changed(self, value):
        """
        Descript. :
        """
        self.beam_position = list(value)
   
    def phi_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["phi"] = pos
        self.emit_diffractometer_moved() 
        self.emit("phiMotorMoved", pos)
        #self.emit('minidiffStateChanged', (self.current_state_dict["phi"], ))

    def phi_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.current_state_dict["phi"] = state
        self.emit('minidiffStateChanged', (state, ))

    def phiz_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["phiz"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def phiz_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.emit('minidiffStateChanged', (state, ))

    def phiy_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.emit('minidiffStateChanged', (state, ))

    def phiy_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["phiy"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def kappa_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["kappa"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()
        self.emit('minidiffStateChanged', (self.current_state_dict["kappa"], ))
        self.emit("kappaMotorMoved", pos)

    def kappa_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.current_state_dict["kappa"] = state
        self.emit('minidiffStateChanged', (state, ))

    def kappa_phi_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["kappa_phi"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()
        self.emit('minidiffStateChanged', (self.current_state_dict["kappa_phi"], ))
        self.emit("kappaPhiMotorMoved", pos)

    def kappa_phi_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.current_state_dict["kappa_phi"] = state
        self.emit('minidiffStateChanged', (state, ))

    def zoom_motor_predefined_position_changed(self, position_name, offset):
        """
        Descript. :
        """
        self.pixels_per_mm_x, self.pixels_per_mm_y = \
              self.get_calibration_data(offset)
        self.emit('zoomMotorPredefinedPositionChanged',
               (position_name, offset, ))

    def zoom_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.emit('minidiffStateChanged', (state, ))
        self.refresh_video()

    def sampleX_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["sampx"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def sampleX_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.current_state_dict["sampx"] = state
        self.emit('minidiffStateChanged', (state, ))

    def sampleY_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["sampy"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def sampleY_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.current_state_dict["sampy"] = state
        self.emit('minidiffStateChanged', (state, ))

    def focus_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["focus"] = pos

    def zoom_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["zoom"] = pos

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
        self.fast_shutter_is_open = is_open
	self.emit('minidiffShutterStateChanged', (self.fast_shutter_is_open, ))

    def refresh_omega_reference_position(self):
        """
        Descript. :
        """
        if self.omega_reference_motor is not None:
            reference_pos = self.omega_reference_motor.getPosition()
            self.omega_reference_motor_moved(reference_pos)

    def get_available_centring_methods(self):
        """
        Descript. :
        """
        return self.centring_methods.keys()

    def get_calibration_data(self, offset):
        """
        Descript. :
        """
        return (1.0 / self.chan_calib_x.getValue(),
                1.0 / self.chan_calib_y.getValue())

    def get_pixels_per_mm(self):
        """
        Descript. :
        """
        return (self.pixels_per_mm_x, self.pixels_per_mm_y)

    def get_positions(self): 
        """
        Descript. :
        """
        #self.current_positions_dict["beam_x"] = (self.beam_position[0] - \
        #     self.zoom_centre['x'] )/self.pixels_per_mm_y
        #self.current_positions_dict["beam_y"] = (self.beam_position[1] - \
        #     self.zoom_centre['y'] )/self.pixels_per_mm_x
        return self.current_positions_dict

    def get_omega_position(self):
        """
        Descript. :
        """
        return self.current_positions_dict.get("phi")

    def get_current_positions_dict(self):
        """
        Descript. :
        """
        return self.current_positions_dict

    def set_sample_info(self, sample_info):
        """
        Descript. :
        """
        self.current_sample_info = sample_info

    def set_in_collection(self, in_collection):
        """
        Descrip. :
        """
        self.in_collection = in_collection

    def get_in_collection(self):
        """
        Descrip. :
        """
        return self.in_collection

    def get_phase_list(self):
        return self.phase_list

    def start_set_phase(self, name):
        """
        Descript. :
        """
        if self.cmd_start_set_phase is not None:
            self.cmd_start_set_phase(name)
        self.refresh_video()

    def refresh_video(self):
        """
        Descript. :
        """
        if self.camera_hwobj is not None:
            if self.current_phase != "Unknown":  
                self.camera_hwobj.refresh_video()
        if self.beam_info_hwobj is not None: 
            self.beam_position = self.beam_info_hwobj.get_beam_position()         

    def start_auto_focus(self):
        """
        Descript. :
        """
        if self.cmd_start_auto_focus:
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

    def get_point_between_two_points(self, point_one, point_two, frame_num, frame_total):
        new_point = {}
        point_one = point_one.as_dict()
        point_two = point_two.as_dict()
        for motor in point_one.keys():
            new_motor_pos = frame_num / float(frame_total) * abs(point_one[motor] - \
                  point_two[motor]) + point_one[motor]
            new_motor_pos += 0.5 * (point_two[motor] - point_one[motor]) / \
                  frame_total
            new_point[motor] = new_motor_pos
        return new_point

    def move_to_coord(self, x, y, omega=None):
        """
        Descript. : function to create a centring point based on all motors
                    positions.
        """  
        if self.current_phase != "BeamLocation":
            try:
                pos = self.get_centred_point_from_coord(x, y, return_by_names=False)
                if omega is not None:
                    pos["phiMotor"] = omega 
                self.move_to_motors_positions(pos)
            except:
                logging.getLogger("HWR").exception("EMBLMiniDiff: could not center to beam, aborting")
        else:
            logging.getLogger("HWR").debug("Move to screen position disabled in BeamLocation phase.")

    def start_centring_method(self, method, sample_info = None):
        """
        Descript. :
        """
        if self.current_centring_method is not None:
            logging.getLogger("HWR").error("EMBLMiniDiff: already in centring method %s" % 
                                     self.currentCentringMethod)
            return
        curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.centring_status = {"valid": False, "startTime": curr_time}
        self.centring_status["angleLimit"] = None
        self.emit_centring_started(method)
        try:
            fun = self.centring_methods[method]
        except KeyError, diag:
            logging.getLogger("HWR").error("EMBLMiniDiff: unknown centring method (%s)" % str(diag))
            self.emit_centring_failed()
        else:
            try:
                fun(sample_info)
            except:
                logging.getLogger("HWR").exception("EMBLMiniDiff: problem while centring")
                self.emit_centring_failed()
    
    def cancel_centring_method(self, reject = False):
        """
        Descript. :
        """ 
        if self.current_centring_procedure is not None:
            try:
                self.current_centring_procedure.kill()
            except:
                logging.getLogger("HWR").exception("EMBLMiniDiff: problem aborting the centring method")
            try:
                fun = self.cancel_centring_methods[self.current_centring_method]
            except KeyError, diag:
                self.emit_centring_failed()
            else:
                try:
                    fun()
                except:
                    self.emit_centring_failed()
        else:
            self.emit_centring_failed()
        self.emit_progress_message("")
        if reject:
            self.reject_centring()

    def get_current_centring_method(self):
        """
        Descript. :
        """
        return self.current_centring_method

    def start_3Click_centring(self, sample_info = None):
        """
        Descript. :
        """
        self.emit_progress_message("3 click centring...")
        self.current_centring_procedure = gevent.spawn(self.manual_centring)
        self.current_centring_procedure.link(self.manual_centring_done)

    def start_automatic_centring(self, sample_info = None, loop_only = False):
        """
        Descript. :
        """
        return

    def start_2D_centring(self, coord_x=None, coord_y=None, omega=None):
        """
        Descript. :
        """
        try:
            self.centring_time = time.time()
            curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.centring_status = {"valid": True, 
                                    "startTime": curr_time,
                                    "endTime": curr_time}
            if (coord_x is None and
                coord_y is None):
                coord_x = self.beam_position[0]
                coord_y = self.beam_position[1]

            motors = self.get_centred_point_from_coord(\
                  coord_x, coord_y, return_by_names=True)
            if omega is not None:
                motors["phi"] = omega         
 
            self.centring_status["motors"] = motors
            self.centring_status["valid"] = True
            self.centring_status["angleLimit"] = True 
            self.emit_progress_message("")
            self.accept_centring()
            self.current_centring_method = None
            self.current_centring_procedure = None
        except:
            logging.exception("Could not complete 2D centring")

    def manual_centring(self):
        """
        Descript. :
        """
        self.centring_hwobj.initCentringProcedure()
        self.head_type = self.chan_head_type.getValue()
        for click in (0, 1, 2):
            self.user_clicked_event = AsyncResult()
            x, y = self.user_clicked_event.get()
            self.centring_hwobj.appendCentringDataPoint(
                 {"X": (x - self.beam_position[0])/ self.pixels_per_mm_x,
                  "Y": (y - self.beam_position[1])/ self.pixels_per_mm_y})
            if self.head_type == "MiniKappa":
                if click < 2:
                    self.phiMotor.moveRelative(90)
            elif self.head_type == "Plate":
                dynamic_limits = self.phiMotor.getDynamicLimits()
                if click == 0:
                    self.phiMotor.move(dynamic_limits[0])
                elif click == 1:
                    self.phiMotor.move(dynamic_limits[1])
        self.omega_reference_add_constraint()
        return self.centring_hwobj.centeredPosition(return_by_name=False)

    def motor_positions_to_screen(self, centred_positions_dict):
        """
        Descript. :
        """
        c = centred_positions_dict

        kappa = self.current_positions_dict["kappa"] 
        phi = self.current_positions_dict["kappa_phi"] 

        if (c['kappa'], c['kappa_phi']) != (kappa, phi) \
         and self.minikappa_correction_hwobj is not None:
            #c['sampx'], c['sampy'], c['phiy']
            c['sampx'], c['sampy'], c['phiy'] = self.minikappa_correction_hwobj.shift(
            c['kappa'], c['kappa_phi'], [c['sampx'], c['sampy'], c['phiy']], kappa, phi)
        xy = self.centring_hwobj.centringToScreen(c)
        x = (xy['X'] + c['beam_x']) * self.pixels_per_mm_x + \
              self.zoom_centre['x']
        y = (xy['Y'] + c['beam_y']) * self.pixels_per_mm_y + \
             self.zoom_centre['y']
        return x, y
 
    def manual_centring_done(self, manual_centring_procedure):
        """
        Descript. :
        """
        try:
            motor_pos = manual_centring_procedure.get()
            if isinstance(motor_pos, gevent.GreenletExit):
                raise motor_pos
        except:
            logging.exception("Could not complete manual centring")
            self.emit_centring_failed()
        else:
            self.emit_progress_message("Moving sample to centred position...")
            self.emit_centring_moving()
            try:
                self.move_to_motors_positions(motor_pos)
            except:
                logging.exception("Could not move to centred position")
                self.emit_centring_failed()
            else:
                if self.chan_head_type.getValue() == "MiniKappa":
                    self.phiMotor.syncMoveRelative(-180)
            #logging.info("EMITTING CENTRING SUCCESSFUL")
            self.centring_time = time.time()
            self.emit_centring_successful()
            self.emit_progress_message("")

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
                motor_pos = {self.sampleXMotor: centred_position.sampx,
                             self.sampleYMotor: centred_position.sampy,
                             self.phiMotor: centred_position.phi,
                             self.phiyMotor: centred_position.phiy + \
                                  self.centring_hwobj.camera2alignmentMotor(self.phiyMotor, \
                                  {"X" : dx, "Y" : dy}), 
                             self.phizMotor: centred_position.phiz + \
                                  self.centring_hwobj.camera2alignmentMotor(self.phizMotor, \
                                  {"X" : dx, "Y" : dy}),
                             self.kappaMotor: centred_position.kappa,
                             self.kappaPhiMotor: centred_position.kappa_phi}
                self.move_to_motors_positions(motor_pos)
            except:
                logging.exception("Could not move to centred position")
        else:
            logging.getLogger("HWR").debug("Move to centred position disabled in BeamLocation phase.")

    def move_kappa_and_phi(self, kappa, kappa_phi, wait = False):
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
        kappa = self.current_positions_dict["kappa"]
        kappa_phi = self.current_positions_dict["kappa_phi"]
        motor_pos_dict = {}

        if (kappa, kappa_phi ) != (new_kappa, new_kappa_phi) \
         and self.minikappa_correction_hwobj is not None:
            sampx = self.sampleXMotor.getPosition()
            sampy = self.sampleYMotor.getPosition()
            phiy = self.phiyMotor.getPosition()
            new_sampx, new_sampy, new_phiy = self.minikappa_correction_hwobj.shift( 
                                kappa, kappa_phi, [sampx, sampy, phiy] , new_kappa, new_kappa_phi)
            
            motor_pos_dict[self.kappaMotor] = new_kappa
            motor_pos_dict[self.kappaPhiMotor] = new_kappa_phi
            motor_pos_dict[self.sampleXMotor] = new_sampx
            motor_pos_dict[self.sampleYMotor] = new_sampy
            motor_pos_dict[self.phiyMotor] = new_phiy

            self.move_motors(motor_pos_dict)
 
    def move_to_motors_positions(self, motors_pos, wait = False):
        """
        Descript. :
        """
        self.emit_progress_message("Moving to motors positions...")
        self.move_to_motors_positions_procedure = gevent.spawn(self.move_motors,
                                                               motors_pos)
        self.move_to_motors_positions_procedure.link(self.move_motors_done)

    def get_motor_hwobj(self, motor_name):
        """
        Descript. :
        """
        if motor_name == 'phi':
            return self.phiMotor
        elif motor_name == 'phiz':
            return self.phizMotor
        elif motor_name == 'phiy':
            return self.phiyMotor
        elif motor_name == 'sampx':
            return self.sampleXMotor
        elif motor_name == 'sampy':
            return self.sampleYMotor
        elif motor_name == 'kappa':
            return self.kappaMotor
        elif motor_name == 'kappa_phi':
            return self.kappaPhiMotor

    def move_motors(self, motor_position_dict):
        """
        Descript. : general function to move motors.
        Arg.      : motors positions in dict. Dictionary can contain motor names 
                    as str or actual motor hwobj
        """
        for motor in motor_position_dict.keys():
            position = motor_position_dict[motor]
            if isinstance(motor, str) or isinstance(motor, unicode):
                motor_role = motor
                motor = self.get_motor_hwobj(motor_role)
                del motor_position_dict[motor_role]
                if motor is None:
                    continue
                motor_position_dict[motor] = position   
            #logging.getLogger("HWR").info("Moving motor '%s' to %f", motor.getMotorMnemonic(), position)
            motor.move(position)
        while any([motor.motorIsMoving() for motor in motor_position_dict.iterkeys()]):
            time.sleep(0.5)
        """with gevent.Timeout(15):
             while not all([m.getState() == m.READY for m in motors_positions if m is not None]):
                   time.sleep(0.1)"""

    def move_motors_done(self, move_motors_procedure):
        """
        Descript. :
        """
        self.move_to_motors_positions_procedure = None
        self.emit_progress_message("")

    def image_clicked(self, x, y, xi, yi):
        """
        Descript. :
        """
        self.user_clicked_event.set((x, y))

    def emit_centring_started(self, method):
        """
        Descript. :
        """
        self.current_centring_method = method
        self.emit('centringStarted', (method, False))

    def accept_centring(self):
        """
        Descript. : 
        Arg.      " fully_centred_point. True if 3 click centring
                    else False
        """
        self.centring_status["valid"] = True
        self.centring_status["accepted"] = True
        self.emit('centringAccepted', (True, self.get_centring_status()))

    def reject_centring(self):
        """
        Descript. :
        """
        if self.current_centring_procedure:
            self.current_centring_procedure.kill()
        self.centring_status = {"valid":False}
        self.emit_progress_message("")
        self.emit('centringAccepted', (False, self.get_centring_status()))

    def emit_centring_moving(self):
        """
        Descript. :
        """
        self.emit('centringMoving', ())

    def emit_centring_failed(self):
        """
        Descript. :
        """
        self.centring_status = {"valid": False}
        method = self.current_centring_method
        self.current_centring_method = None
        self.current_centring_procedure = None
        self.emit('centringFailed', (method, self.get_centring_status()))

    def convert_from_obj_to_name(self, motor_pos):
        motors = {}
        for motor_role in ('phiy', 'phiz', 'sampx', 'sampy', 'zoom',
                           'phi', 'focus', 'kappa', 'kappa_phi'):
            mot_obj = self.getDeviceByRole(motor_role)
            try:
               motors[motor_role] = motor_pos[mot_obj]
            except KeyError:
               motors[motor_role] = mot_obj.getPosition()
        motors["beam_x"] = (self.beam_position[0] - \
                            self.zoom_centre['x'] )/self.pixels_per_mm_y
        motors["beam_y"] = (self.beam_position[1] - \
                            self.zoom_centre['y'] )/self.pixels_per_mm_x
        return motors
 

    def emit_centring_successful(self):
        """
        Descript. :
        """
        if self.current_centring_procedure is not None:
            curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.centring_status["endTime"] = curr_time
            motor_pos = self.current_centring_procedure.get()
            motors = self.convert_from_obj_to_name(motor_pos)

            self.centring_status["motors"] = motors
            self.centring_status["method"] = self.current_centring_method
            self.centring_status["valid"] = True
           
            method = self.current_centring_method
            self.emit('centringSuccessful', (method, self.get_centring_status()))
            self.current_centring_method = None
            self.current_centring_procedure = None
        else:
            logging.getLogger("HWR").debug("EMBLMiniDiff: trying to emit centringSuccessful outside of a centring")

    def emit_progress_message(self, msg = None):
        """
        Descript. :
        """
        self.emit('progressMessage', (msg,))

    def get_centring_status(self):
        """
        Descript. :
        """
        return copy.deepcopy(self.centring_status)

    def take_snapshots_procedure(self, image_count, drawing):
        """
        Descript. :
        """
        centred_images = []
        for index in range(image_count):
            logging.getLogger("HWR").info("EMBLMiniDiff: taking snapshot #%d", index + 1)
            centred_images.append((self.phiMotor.getPosition(), str(myimage(drawing))))
            if (self.head_type == "MiniKappa"and image_count > 1):
                self.phiMotor.syncMoveRelative(-90)
            centred_images.reverse() # snapshot order must be according to positive rotation direction
        return centred_images

    def take_snapshots(self, image_count, wait = False):
        """
        Descript. :
        """
        self.camera_hwobj.forceUpdate = True
        if image_count > 0:
            snapshots_procedure = gevent.spawn(self.take_snapshots_procedure,
                                               image_count, self._drawing)
            self.emit('centringSnapshots', (None,))
            self.emit_progress_message("Taking snapshots")
            self.centring_status["images"] = []
            snapshots_procedure.link(self.snapshots_done)
            if wait:
                self.centring_status["images"] = snapshots_procedure.get()
 
    def snapshots_done(self, snapshots_procedure):
        """
        Descript. :
        """
        self.camera_hwobj.forceUpdate = False
        try:
            self.centring_status["images"] = snapshots_procedure.get()
        except:
            logging.getLogger("HWR").exception("EMBLMiniDiff: could not take crystal snapshots")
            self.emit('centringSnapshots', (False,))
            self.emit_progress_message("")
        else:
            self.emit('centringSnapshots', (True,))
            self.emit_progress_message("")
        self.emit_progress_message("Sample is centred!")

    def visual_align(self, point_1, point_2):
        """
        Descript. :
        """
        self.head_type = self.chan_head_type.getValue()
        if self.head_type == "Plate":
            logging.getLogger("HWR").info("EMBLMiniDiff: Visual align not available in Plate mode") 
            return

        cpos_1 = point_1.centred_position
        cpos_2 = point_2.centred_position

        t1 =[cpos_1.sampx, cpos_1.sampy, cpos_1.phiy]
        t2 =[cpos_2.sampx, cpos_2.sampy, cpos_2.phiy]
        kappa = self.kappaMotor.getPosition()
        phi = self.kappaPhiMotor.getPosition()
        new_kappa, new_phi, (new_sampx, new_sampy, new_phiy) = \
             self.minikappa_correction_hwobj.alignVector(t1,t2,kappa,phi)
	self.move_to_motors_positions({self.kappaMotor:new_kappa, 
                                       self.kappaPhiMotor:new_phi, 
                                       self.sampleXMotor:new_sampx,
                                       self.sampleYMotor:new_sampy, 
                                       self.phiyMotor:new_phiy})

    def update_values(self):
        self.emit('minidiffPhaseChanged', (self.current_phase, ))            
        self.emit('omegaReferenceChanged', (self.reference_pos,))
        self.emit('minidiffShutterStateChanged', (self.fast_shutter_is_open, ))

    def toggle_fast_shutter(self):
        if self.chan_fast_shutter_is_open is not None:
            self.chan_fast_shutter_is_open.setValue(not self.fast_shutter_is_open) 
