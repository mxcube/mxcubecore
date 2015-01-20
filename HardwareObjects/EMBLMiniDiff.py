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

    def __init__(self, *args):
        """
        Description:
        """ 
        Equipment.__init__(self, *args)

        self.phiMotor = None
        self.phizMotor = None
        self.phiyMotor = None
        self.lightMotor = None
        self.zoomMotor = None
        self.sampleXMotor = None
        self.sampleYMotor = None
        self.camera = None
        self.focusMotor = None
        self.kappaMotor = None
        self.kappaPhiMotor = None
        self.omega_reference_motor = None
        self.sample_changer_hwobj = None
        self.beam_info_hwobj = None
        self.centring_hwobj = None
        self.minikappa_correction_hwobj = None
  
        self.chan_x_calib = None
        self.chan_y_calib = None
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
        self.centring_methods = None
        self.centring_status = None
        self.centring_time = None
        self.user_confirms_centring = None
        self.user_clicked_event = None
        self.omega_reference_par = None
        #self.move_to_center_position_task = None
        self.move_to_motors_positions_task = None
        self.move_to_motors_positions_procedure = None
        self.ready_event = None
        self.in_collection = None
        
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

        self.phiMotor = self.getDeviceByRole('phi')
        self.phizMotor = self.getDeviceByRole('phiz')
        self.phiyMotor = self.getDeviceByRole('phiy')
        self.zoomMotor = self.getDeviceByRole('zoom')
        self.lightMotor = self.getDeviceByRole('light')
        self.focusMotor = self.getDeviceByRole('focus')
        self.sampleXMotor = self.getDeviceByRole('sampx')
        self.sampleYMotor = self.getDeviceByRole('sampy')
        self.kappaMotor = self.getDeviceByRole('kappa')
        self.kappaPhiMotor = self.getDeviceByRole('kappa_phi')
        self.camera = self.getDeviceByRole('camera')   

        self.chan_x_calib = self.addChannel({ "type":"exporter",
                                 "exporter_address": self.exporter_address,
                                 "name":"MD_0/CoaxCamScaleX" }, 
                                 "CoaxCamScaleX")
        self.chan_y_calib = self.addChannel({ "type":"exporter",
                                 "exporter_address": self.exporter_address,
                                 "name":"MD_0/CoaxCamScaleY" }, 
                                 "CoaxCamScaleY")
        self.chan_sync_move_motors = self.addCommand({"type":"exporter",
				 "exporter_address": self.exporter_address,
                                 "name":"MD_0/SyncMoveMotor" },
                                 "SyncMoveMotors")
        self.chan_current_phase = self.addChannel({ "type":"exporter",
                                 "exporter_address": self.exporter_address,
                                 "name":"MD_0/CurrentPhase" },
                                 "CurrentPhase")
        if self.chan_current_phase is not None:
            self.connect(self.chan_current_phase, "update", 
                         self.current_phase_changed)

        self.cmd_start_set_phase = self.addCommand( {"type":"exporter",
                                 "name":"MD_0/startSetPhase" },
                                 "startSetPhase")
        self.cmd_start_auto_focus = self.addCommand( {"type":"exporter",
                                 "name":"MD_0/startAutoFocus"},
                                 "startAutoFocus")
        
        self.beam_info_hwobj = HardwareRepository.HardwareRepository().\
                                getHardwareObject(self.getProperty("beaminfo"))
        if self.beam_info_hwobj is not None:  
            self.connect(self.beam_info_hwobj, 'beamPosChanged', self.beam_position_changed)
        else:
            logging.getLogger("HWR").debug('EMBLMinidiff: Beaminfo is not defined')

        self.centring_hwobj = HardwareRepository.HardwareRepository().\
                               getHardwareObject(self.getProperty("centring"))
        if self.centring_hwobj is None:
            logging.getLogger("HWR").debug('EMBLMinidiff: Centring math is not defined')

        try:
            self.minikappa_correction_hwobj = HardwareRepository.HardwareRepository().\
                               getHardwareObject(self.getProperty("minikappaCorrection"))
        except:
            logging.getLogger("HWR").debug('EMBLMinidiff: Minikappa correction is not defined')
        
        if self.phiMotor is not None:
            self.connect(self.phiMotor, 'stateChanged', self.phi_motor_state_changed)
            self.connect(self.phiMotor, "positionChanged", self.phi_motor_moved)
        else:
            logging.getLogger("HWR").error('EMBLMiniDiff: Phi motor is not defined')

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

        if self.camera is None:
            logging.getLogger("HWR").error('EMBLMiniDiff: Camera is not defined')
        else:
            self.image_height = self.camera.getHeight()
            self.image_width = self.camera.getWidth()
        self.image_height = 1024
        self.image_width = 1360

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
            self.connect(self.omega_reference_motor, 'positionChanged', self.omega_reference_motor_moved)
        except:
            logging.getLogger("HWR").warning('EMBLMiniDiff: Omega axis is not defined')

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

    def is_vertical_gonio(self):
        """
        Descript. :
        """
        isVertical = False
        if self.omega_reference_par is not None:
            isVertical = self.omega_reference_par["camera_axis"].lower() == "x"
        return isVertical     

    def current_phase_changed(self, phase):
        """
        Descript. :
        """ 
        self.current_phase = phase
        self.emit('minidiffPhaseChanged', (phase, )) 
        self.refresh_video()

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
        self.emit('kappaMotorMoved', pos)
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
        self.emit('phiMotorMoved', pos)
        self.emit('minidiffStateChanged', (self.current_state_dict["kappa_phi"], ))
        self.emit("phiMoved", pos)

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
            reference_pos = (pos, -10)
        else:
            pos = self.omega_reference_par["direction"] * \
                  (pos - self.omega_reference_par["position"]) * \
                  self.pixels_per_mm_y + self.zoom_centre['y']
            reference_pos = (-10, pos)
        self.emit('omegaReferenceChanged', (reference_pos,))

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
        return (1.0 / self.chan_x_calib.getValue(),
                1.0 / self.chan_y_calib.getValue())

    def get_pixels_per_mm(self):
        """
        Descript. :
        """
        return (self.pixels_per_mm_x, self.pixels_per_mm_y)

    def get_positions(self): 
        """
        Descript. :
        """
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
        if self.camera is not None:
            if self.current_phase != "Unknown":  
                self.camera.refresh_video()
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
            """pos["kappa"] = self.kappaMotor.getPosition()
            pos["kappa_phi"] = self.kappaPhiMotor.getPosition()
            pos["beam_x"] = (self.beam_position[0] - self.zoom_centre['x']) \
                             / self.pixels_per_mm_y
            pos["beam_y"] = (self.beam_position[1] - self.zoom_centre['y']) \
                             /self.pixels_per_mm_x"""
        return pos


    def move_to_coord(self, x, y):
        """
        Descript. : function to create a centring point based on all motors
                    positions.
        """  
        try:
            pos = self.get_centred_point_from_coord(x, y, return_by_names=False)
            self.move_to_motors_positions(pos)
        except:
            logging.getLogger("HWR").exception("EMBLMiniDiff: could not center to beam, aborting")

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

    def start_2D_centring(self):
        """
        Descript. :
        """
        try:
            self.centring_time = time.time()
            curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.centring_status = {"valid": True, 
                                    "startTime": curr_time,
                                    "endTime": curr_time}
            motors = self.get_centred_point_from_coord(self.beam_position[0],
                                                       self.beam_position[1],
                                                       return_by_names=True)
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
        for click in (0, 1, 2):
            self.user_clicked_event = AsyncResult()
            x, y = self.user_clicked_event.get()
            self.centring_hwobj.appendCentringDataPoint(
                 {"X": (x - self.beam_position[0])/ self.pixels_per_mm_x,
                  "Y": (y - self.beam_position[1])/ self.pixels_per_mm_y})
            if click < 2:
                self.phiMotor.moveRelative(90)
        self.omega_reference_add_constraint()
        return self.centring_hwobj.centeredPosition(return_by_name=False)

    def motor_positions_to_screen(self, centred_positions_dict):
        """
        Descript. :
        """
        c = centred_positions_dict
        kappa = self.kappaMotor.getPosition()
        phi = self.kappaPhiMotor.getPosition()

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
            """motor_pos["kappa"] = self.kappaMotor.getPosition()
            motor_pos["kappa_phi"] = self.kappaPhiMotor.getPosition()
            motor_pos["beam_x"] = (self.beam_position[0] - self.zoom_centre['x']) \
                              / self.pixels_per_mm_y
            motor_pos["beam_y"] = (self.beam_position[1] - self.zoom_centre['y']) \
                              /self.pixels_per_mm_x"""           
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
                self.phiMotor.syncMoveRelative(-180)
            #logging.info("EMITTING CENTRING SUCCESSFUL")
            self.centring_time = time.time()
            self.emit_centring_successful()
            self.emit_progress_message("")

    def move_to_centred_position(self, centred_position):
        """
        Descript. :
        """
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
        
        if kappa is not None:
            if abs(kappa - self.kappaMotor.getPosition()) > 0.1:
                self.kappaMotor.move(kappa)
                logging.info("Moving kappa to position: %0.2f" % kappa) 
        if kappa_phi is not None:
            if abs(kappa_phi - self.kappaPhiMotor.getPosition()) > 0.1:
                self.kappaPhiMotor.move(kappa_phi)
                logging.info("Moving kappa phi to position: %0.2f" % kappa_phi)

        with gevent.Timeout(15):
            while not (self.kappaMotor.getState() == self.kappaMotor.READY and \
                       self.kappaPhiMotor.getState() == self.kappaPhiMotor.READY):   
                  time.sleep(0.1) 

    @task
    def free_correcting_move_kappa(self, new_kappa, new_kappa_phi):"""

        #new_kappa=float(raw_input("give kappa"))
        #new_kappa_phi=float(raw_input("give phi"))
        kappa = self.kappaMotor.getPosition()
        kappa_phi = self.kappaPhiMotor.getPosition()
        if (kappa, kappa_phi ) != (new_kappa, new_kappa_phi) \
         and self.minikappa_correction_hwobj is not None:
            sampx = self.sampleXMotor.getPosition()
            sampy = self.sampleYMotor.getPosition()
            phiy = self.phiyMotor.getPosition()
            new_sampx, new_sampy, new_phiy = self.minikappa_correction_hwobj.shift( 
                                kappa, kappa_phi, [sampx, sampy, phiy] , new_kappa, new_kappa_phi)
            self.kappaMotor.move(new_kappa)
            self.kappaPhiMotor.move(new_kappa_phi)
            self.sampleXMotor.move(new_sampx)
            self.sampleYMotor.move(new_sampy)
            self.phiyMotor.move(new_phiy)
            with gevent.Timeout(30):
                 while not (self.kappaMotor.getState() == self.kappaMotor.READY and       \
                            self.kappaPhiMotor.getState() == self.kappaPhiMotor.READY and \
                            self.sampleXMotor.getState() == self.sampleXMotor.READY and   \
                            self.sampleYMotor.getState() == self.sampleYMotor.READY and   \
                            self.phiyMotor.getState()  == self.phiyMotor.READY ):
                       time.sleep(1)
 
    def move_to_motors_positions(self, motors_pos, wait = False):
        """
        Descript. :
        """
        self.emit_progress_message("Moving to motors positions...")
        self.move_to_motors_positions_procedure = gevent.spawn(self.move_motors,
                                                               motors_pos)
        self.move_to_motors_positions_procedure.link(self.move_motors_done)

    def move_motors(self, motors_positions):
        """
        Descript. :
        """
        for motor, pos in motors_positions.iteritems():
            if motor is not self.phiMotor:
                if motor is self.phizMotor:
                    if abs(self.phizMotor.getPosition() - pos) >= 2e-4:
                       motor.move(pos)
                else:
                   motor.move(pos)
        with gevent.Timeout(15):
             while not all([m.getState() == m.READY for m in motors_positions if m is not None]):
                   time.sleep(0.1)

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
        #motors["kappa"] = self.kappaMotor.getPosition()
        #motors["kappa_phi"] = self.kappaPhiMotor.getPosition()
        return motors
 

    def emit_centring_successful(self):
        """
        Descript. :
        """
        if self.current_centring_procedure is not None:
            curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.centring_status["endTime"] = curr_time
            #motors = {}
            motor_pos = self.current_centring_procedure.get()
            motors = self.convert_from_obj_to_name(motor_pos)
            """for motor_role in ('phiy', 'phiz', 'sampx', 'sampy', 'zoom', 
                               'phi', 'focus', 'kappa', 'kappa_phi'):
                mot_obj = self.getDeviceByRole(motor_role)
                try:
                    motors[motor_role] = motor_pos[mot_obj] 
                except KeyError:
                    motors[motor_role] = mot_obj.getPosition()
          
            #motors = self.current_positions_dict
            motors["beam_x"] = (self.beam_position[0] - \
                   self.zoom_centre['x'] )/self.pixels_per_mm_y
            motors["beam_y"] = (self.beam_position[1] - \
                   self.zoom_centre['y'] )/self.pixels_per_mm_x"""

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
            self.phiMotor.syncMoveRelative(-90)
            centred_images.reverse() # snapshot order must be according to positive rotation direction
        return centred_images

    def take_snapshots(self, image_count, wait = False):
        """
        Descript. :
        """
        self.camera.forceUpdate = True
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
        self.camera.forceUpdate = False
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
        #self.free_correcting_move_kappa()
        #return
        cpos_1 = point_1.centred_position
        cpos_2 = point_2.centred_position

        t1 =[cpos_1.sampx, cpos_1.sampy, cpos_1.phiy]
        t2 =[cpos_2.sampx, cpos_2.sampy, cpos_2.phiy]
        kappa = self.kappaMotor.getPosition()
        phi = self.kappaPhiMotor.getPosition()
        new_kappa, new_phi, (new_sampx, new_sampy, new_phiy) = self.minikappa_correction_hwobj.alignVector(t1,t2,kappa,phi)
	self.move_to_motors_positions({ self.kappaMotor:new_kappa, \
                           self.kappaPhiMotor:new_phi, \
                           self.sampleXMotor:new_sampx, \
                           self.sampleYMotor:new_sampy, \
                           self.phiyMotor:new_phiy})


