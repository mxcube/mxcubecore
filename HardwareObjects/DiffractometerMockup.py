"""
Descript. :
"""
import os
import copy
import time
import logging
import tempfile
import gevent
import random
from gevent.event import AsyncResult

import queue_model_objects_v1 as queue_model_objects

from HardwareRepository import HardwareRepository
from HardwareRepository.TaskUtils import *
from HardwareRepository.BaseHardwareObjects import Equipment

#from Qub.Tools import QubImageSave

class myimage:
    """
    Descript. :
    """
    def __init__(self, drawing):
        """
        Descript. :
        """
        self.drawing = drawing
        matrix = self.drawing.matrix()
        self.zoom = 1
        if matrix is not None:
            self.zoom = matrix.m11()
        self.img = self.drawing.getPPP()
        fd, name = tempfile.mkstemp()
        os.close(fd)
        QubImageSave.save(name, self.img, self.drawing.canvas(), self.zoom, "JPEG")
        f = open(name, "r")
        self.imgcopy = f.read()
        f.close()
        os.unlink(name)
    def __str__(self):
        """
        Descript. :
        """
        return self.imgcopy

last_centred_position = [200, 200]

class DiffractometerMockup(Equipment):
    """
    Descript. :
    """
    MANUAL3CLICK_MODE = "Manual 3-click"
    C3D_MODE = "Computer automatic"
    MOVE_TO_BEAM_MODE = "Move to Beam"

    MINIKAPPA = "MiniKappa"
    PLATE = "Plate"
    SC = "SC"

    def __init__(self, *args):
        """
        Descript. :
        """
        Equipment.__init__(self, *args)

        queue_model_objects.CentredPosition.set_diffractometer_motor_names(\
                "phi", "focus", "phiz", "phiy", "zoom",
                "sampx", "sampy", "kappa", "kappa_phi")


        self.phiMotor = None
        self.phizMotor = None
        self.phiyMotor = None
        self.lightMotor = None
        self.zoomMotor = None
        self.sampleXMotor = None
        self.sampleYMotor = None
        self.camera_hwobj = None
        self.beam_info_hwobj = None

        self.beam_position = None
        self.x_calib = None
        self.y_calib = None
        self.pixels_per_mm_x = None
        self.pixels_per_mm_y = None
        self.image_width = None
        self.image_height = None
        self.current_sample_info = None
        self.cancel_centring_methods = None
        self.current_centring_procedure = None
        self.current_centring_method = None
        self.current_positions_dict = None
        self.current_phase = None
        self.centring_methods = None
        self.centring_status = {"valid":None,"startTime":None,"endTime":None,"motors":None,"accepted":None,"method":None,"images":None}
        self.centring_time = None
        self.user_confirms_centring = None
        self.user_clicked_event = None
        self.phase_list = None
        self.head_type = None
        self._drawing = None
        self.use_sc = False
        self.transfer_mode = None


        self.connect(self, 'equipmentReady', self.equipmentReady)
        self.connect(self, 'equipmentNotReady', self.equipmentNotReady)

        self.startCentringMethod = self.start_centring_method
        self.cancelCentringMethod = self.cancel_centring_method
        self.imageClicked = self.image_clicked
        self.acceptCentring = self.accept_centring
        self.rejectCentring = self.reject_centring
        self.getCentringStatus = self.get_centring_status
        self.takeSnapshots = self.take_snapshots
        self.moveMotors = self.move_motors
        self.start3ClickCentring = self.start_3Click_centring
        self.startAutoCentring = self.start_automatic_centring
     
    def init(self):
        """
        Descript. :
        """
        self.x_calib = 0.000444
        self.y_calib = 0.000446
        self.transfer_mode = "SAMPLE_CHANGER"# available mode is DIRECT, KAPPA, SAMPLE_CHANGER, CLEARED, UNKNOWN
         
        self.pixels_per_mm_x = 1.0 / self.x_calib
        self.pixels_per_mm_y = 1.0 / self.y_calib
        self.beam_position = [200, 200]
        
        self.centring_methods = {
             DiffractometerMockup.MANUAL3CLICK_MODE: self.start_3Click_centring,
             DiffractometerMockup.C3D_MODE: self.start_automatic_centring}
        self.cancel_centring_methods = {}
        self.current_positions_dict = {'phiy'  : 0, 'phiz' : 0, 'sampx' : 0,
                                       'sampy' : 0, 'zoom' : 0, 'phi' : 17.6,
                                       'focus' : 0, 'kappa': 0, 'kappa_phi': 0,
                                       'beam_x': 0, 'beam_y': 0} 
        self.centring_status = {"valid": False}

        self.centring_time = 0
        self.user_confirms_centring = True
        self.fast_shutter_is_open = False
        self.user_clicked_event = AsyncResult()

        self.image_width = 400
        self.image_height = 400

        self.equipmentReady()
        self.user_clicked_event = AsyncResult()

        self.phiMotor = self.getDeviceByRole('phi')
        self.sampleXMotor = self.getDeviceByRole('sampx')
        self.sampleYMotor = self.getDeviceByRole('sampy')
        self.camera_hwobj = self.getDeviceByRole('camera')
        self.beam_info_hwobj = self.getObjectByRole('beam_info')
        self.camera = self.camera_hwobj
        self.beam_info = self.beam_info_hwobj
       
        self.sample_changer = self.getObjectByRole('samplechanger')
        self.front_light_motor = self.getObjectByRole('frontlight')
        self.front_light_swtich = self.getObjectByRole('frontlightswitch')
        self.back_light_motor = self.getObjectByRole('backlight')
        self.back_light_swtich = self.getObjectByRole('backlightswitch')

        if self.phiMotor is not None:
            self.connect(self.phiMotor, 'stateChanged', self.phiMotorStateChanged)
            self.connect(self.phiMotor, "positionChanged", self.phi_motor_position_changed)
        else:
            logging.getLogger("HWR").error('MiniDiff: phi motor is not defined in minidiff equipment %s', str(self.name()))

        if self.sampleXMotor is not None:
            self.connect(self.sampleXMotor, 'stateChanged', self.sampleX_motor_state_changed)
            self.connect(self.sampleXMotor, 'positionChanged', self.sampleX_motor_moved)
            self.connect(self.sampleXMotor, "positionChanged", self.emit_diffractometer_moved)
        else:
            logging.getLogger("HWR").error('MiniDiff: Sampx motor is not defined')

        if self.sampleYMotor is not None:
            self.connect(self.sampleYMotor, 'stateChanged', self.sampleY_motor_state_changed)
            self.connect(self.sampleYMotor, 'positionChanged', self.sampleY_motor_moved)
            self.connect(self.sampleYMotor, "positionChanged", self.emit_diffractometer_moved)
        else:
            logging.getLogger("HWR").error('MiniDiff: Sampx motor is not defined')

        if self.beam_info_hwobj is not None:
            self.connect(self.beam_info_hwobj, 'beamPosChanged', self.beam_position_changed)
        else:
            logging.getLogger("HWR").debug('Minidiff: Beaminfo is not defined')

        takeSnapshots = self.take_snapshots
        self.getCentringStatus = self.get_centring_status

        self.reversing_rotation = self.getProperty("reversingRotation")
        try:
            self.grid_direction = eval(self.getProperty("gridDirection"))
        except:
            self.grid_direction = {"fast": (0, 1), "slow": (1, 0)}
            logging.getLogger("HWR").warning('MiniDiff: Grid direction is not defined. Using default.')
        
        if self.sample_changer is not None and self.transfer_mode == "SAMPLE_CHANGER":
            self.use_sc = True  # by default use sample changer if it's defined
        else:
            logging.getLogger("HWR").warning('Sample Changer is not defined.')
 
        try:
            self.current_phase = "Transfer"
            self.phase_list = eval(self.getProperty("phaseList"))
            self.head_type = self.getProperty("headType")
        except:
            self.phase_list = []

    # to make it compatibile
    def __getattr__(self, attr):
        if attr.startswith("__"):
            raise AttributeError(attr)
        else:
            if attr == "currentCentringProcedure":
                return self.current_centring_procedure
            if attr == "centringStatus" :
                return self.centring_status

    def set_drawing(self, drawing):
	self._drawing = drawing

    def use_sample_changer(self):
        return self.use_sc
   
    def set_use_sc(self,state):
        self.use_sc = state
        return True

    def in_plate_mode(self):
        return self.head_type == "Plate"

    def toggle_fast_shutter(self):
        self.fast_shutter_is_open = not self.fast_shutter_is_open
        self.emit('minidiffShutterStateChanged', (self.fast_shutter_is_open, ))

    def get_head_type(self):
        return self.head_type

    def get_transfer_mode(self):
        return self.transfer_mode
         
    def get_grid_direction(self):
        return self.grid_direction

    def is_reversing_rotation(self):
        return self.reversing_rotation == True

    def phiMotorStateChanged(self,state):
        self.emit('phiMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))

    def phi_motor_position_changed(self, position):
        self.current_positions_dict["phi"] = position
        self.emit('minidiffStateChanged', ("ready",)) 

    def sampleX_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.emit('sampxMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state, ))

    def sampleY_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.emit('sampyMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state, ))

    def sampleX_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["sampx"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()

    def sampleY_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["sampy"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()

    def getStatus(self):
        """
        Descript. :
        """
        return "ready"

    def saveCurrentPos(self):
        random_num = random.random()
        centred_pos_dir = {'phiy': random_num, 'phiz': random_num * 2,
                           'sampx': random_num * 3, 'sampy': random_num * 4,
                           'zoom': 8.53, 'phi': 311.1, 'focus': -0.42,
                           'kappa': 0.0, 'kappa_phi': 0.0}
        self.centring_status["motors"] = centred_pos_dir
        self.acceptCentring()

    def manual_centring(self):
        """
        Descript. :
        """

        self.user_clicked_event = AsyncResult()
        x, y = self.user_clicked_event.get()
        last_centred_position[0] = x
        last_centred_position[1] = y
        random_num = random.random()
        centred_pos_dir = {'phiy': random_num, 'phiz': random_num * 2, 
                           'sampx': random_num * 3, 'sampy': random_num * 4, 
                           'zoom': 8.53, 'phi': 311.1, 'focus': -0.42, 
                           'kappa': 0.0, 'kappa_phi': 0.0}
        return centred_pos_dir 		

    def set_sample_info(self, sample_info):
        """
        Descript. :
        """
        self.current_sample_info = sample_info
	
    def emit_diffractometer_moved(self, *args):
        """
        Descript. :
        """
        self.emit("diffractometerMoved", ())
	
    def isReady(self):
        """
        Descript. :
        """ 
        return True

    def isValid(self):
        """
        Descript. :
        """
        return True

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

    def invalidate_centring(self):
        """
        Descript. :
        """
        if self.current_centring_procedure is None and self.centring_status["valid"]:
            self.centring_status = {"valid":False}
            self.emitProgressMessage("")
            self.emit('centringInvalid', ())

    def get_available_centring_methods(self):
        """
        Descript. :
        """
        return self.centring_methods.keys()

    def get_calibration_data(self, offset):
        """
        Descript. :
        """
        #return (1.0 / self.x_calib, 1.0 / self.y_calib)
        return (1.0 / self.x_calib, 1.0 / self.y_calib)

    def get_pixels_per_mm(self):
        """
        Descript. :
        """
        return (self.pixels_per_mm_x, self.pixels_per_mm_y)

    def refresh_omega_reference_position(self):
        """
        Descript. :
        """
        return

    def get_omega_axis_position(self):	
        """
        Descript. :
        """
        return self.current_positions_dict.get("phi")     

    def get_positions(self):
        """
        Descript. :
        """
        return self.current_positions_dict

    def get_current_positions_dict(self):
        """
        Descript. :
        """
        return self.current_positions_dict

    def beam_position_changed(self, value):
        """
        Descript. :
        """
        self.beam_position = value
  
    def start_centring_method(self, method, sample_info = None):
        """
        Descript. :
        """
        if self.current_centring_method is not None:
            logging.getLogger("HWR").error("already in centring method %s" %\
                    self.current_centring_method)
            return
        curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.centring_status = {"valid": False, "startTime": curr_time}
        self.emit_centring_started(method)
        try:
            fun = self.centring_methods[method]
        except KeyError, diag:
            logging.getLogger("HWR").error("unknown centring method (%s)" % \
                    str(diag))
            self.emit_centring_failed()
        else:
            try:
                fun(sample_info)
            except:
                logging.getLogger("HWR").exception("problem while centring")
                self.emit_centring_failed()

    def cancel_centring_method(self, reject = False):
        """
        Descript. :
        """
        if self.current_centring_procedure is not None:
            try:
                self.current_centring_procedure.kill()
            except:
                logging.getLogger("HWR").exception("problem aborting the centring method")
            try:
                fun = self.cancel_centring_methods[self.current_centring_method]
            except:
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

    def start_3Click_centring(self, sample_info=None):
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
        self.emit_progress_message("Auto centring")
        self.emit_centring_started(DiffractometerMockup.C3D_MODE)
        self.emit('centringSuccessful')
        return

    def motor_positions_to_screen(self, centred_positions_dict):
        """
        Descript. :
        """ 
        return last_centred_position[0], last_centred_position[1]

    def manual_centring_done(self, manual_centring_procedure):
        """
        Descript. :
        """
        self.emit_progress_message("Moving sample to centred position...")
        self.emit_centring_moving()
        self.centred_time = time.time()
        self.emit_centring_successful()
        self.emit_progress_message("")

    @task
    def move_to_centred_position(self, centred_pos):
        """
        Descript. :
        """
        if self.current_phase != "BeamLocation":
            time.sleep(1)
        else:
            logging.getLogger("HWR").debug("Move to centred position disabled in BeamLocation phase.") 


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
   
    def moveToCentredPosition(self, centred_position, wait = False):
        """
        Descript. :
        """
        try:
            return self.move_to_centred_position(centred_position, wait = wait)
        except:
            logging.exception("Could not move to centred position")

    def image_clicked(self, x, y, xi, yi): 
        """
        Descript. :
        """
        self.user_clicked_event.set((x, y))
	
    def emit_cetring_started(self, method):
        """
        Descript. :
        """
        self.current_centring_method = method
        self.emit('centringStarted', (method, False))

    def accept_centring(self):
        """
        Descript. :
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
        self.centring_status = {"valid" : False}
        self.emit_progress_message("")
        self.emit('centringAccepted', (False, self.get_centring_status()))

    def emit_centring_moving(self):
        """
        Descript. :
        """
        self.emit('centringMoving', ())

    def emit_centring_started(self, method):
        """
        Descript. :
        """
        self.current_centring_method = method
        self.emit('centringStarted', (method, False))

    def emit_centring_failed(self):
        """
        Descript. :
        """
        self.centring_status = {"valid" : False}
        method = self.current_centring_method
        self.current_centring_method = None
        self.current_centring_procedure = None
        self.emit('centringFailed', (method, self.get_centring_status()))

    def emit_centring_successful(self):
        """
        Descript. :
        """
        if self.current_centring_procedure is not None:
            curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.centring_status["endTime"] = curr_time
            random_num = random.random()
            motors = {'phiy': random_num,  'phiz': random_num * 2,
                      'sampx': random_num * 3, 'sampy': random_num * 4, 
                      'zoom': random_num * 5, 'phi': random_num * 6, 
		      'focus': -0.42, 'kappa': 0.0009, ' kappa_phi': 311.0}

            motors["beam_x"] = 0.1
            motors["beam_y"] = 0.1

            self.centring_status["motors"] = motors
            self.centring_status["method"] = self.current_centring_method
            self.centring_status["valid"] = True

            method = self.current_centring_method
            self.emit('centringSuccessful', (method, self.get_centring_status()))
            self.current_centring_method = None
            self.current_centring_procedure = None
        else:
            logging.getLogger("HWR").debug("trying to emit centringSuccessful outside of a centring")

    def emit_progress_message(self, msg = None):
        """
        Descript. :
        """
        self.emit('progressMessage', msg)

    def get_centring_status(self):
        """
        Descript. :
        """
        return copy.deepcopy(self.centring_status)

    def getPositions(self):
        """
        Descript. :
        """
        random_num = random.random()
        return {"phi": random_num, "focus": random_num * 2, 
                "phiy" : random_num * 3, "phiz": random_num * 4, 
                "sampx": random_num * 5, "sampy": random_num * 6,
		"kappa": 0.0009, "kappa_phi": 311.0, "zoom": 8.53}

    def simulateAutoCentring(self, sample_info = None):
        """
        Descript. :
        """
        return

    def get_current_positions_dict(self):
        """
        Descript. :
        """
        return

    def get_current_phase(self):
        """
        Descript. :
        """
        return self.current_phase

    def set_phase(self, phase, timeout=None):
	self.start_set_phase(phase)

    def start_set_phase(self, name):
        """
        Descript. :
        """
        self.current_phase = name
        self.emit('minidiffPhaseChanged', (self.current_phase, ))

    def refresh_video(self):
        """
        Descript. :
        """
        print "refresh"
        if self.beam_info_hwobj: 
            self.beam_info_hwobj.beam_pos_hor_changed(300) 
            self.beam_info_hwobj.beam_pos_ver_changed(200)
        self.emit("phiMotorMoved", 10.2)
        self.emit("kappaMotorMoved", 11.2)

    def start_auto_focus(self): 
        """
        Descript. :
        """
        return

    def move_to_beam(self, x, y, omega=None):
        """
        Descript. : function to create a centring point based on all motors
                    positions.
        """
        print "moving to beam position: %d %d" % (self.beam_position[0], self.beam_position[1])
        return

    def move_to_coord(self, x, y, omega=None):
        """
        Descript. :
        """
        print "moving to coord: %d %d" %(x ,y) 
        if self.current_phase != "BeamLocation":
            time.sleep(1)
        else:
            logging.getLogger("HWR").debug("Move to screen position disabled in BeamLocation phase.")

    def move_motors(self, motors_dict):
        return
  
    def start_2D_centring(self, coord_x=None, coord_y=None, omega=None):
        """
        Descript. :
        """
        self.centring_time = time.time()
        curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.centring_status = {"valid": True,
                                "startTime": curr_time,
                                "endTime": curr_time} 
        motors = self.getPositions()
        motors["beam_x"] = 0.1
        motors["beam_y"] = 0.1
        self.centring_status["motors"] = motors
        self.centring_status["valid"] = True
        self.centring_status["angleLimit"] = False
        self.emit_progress_message("")
        self.accept_centring()
        self.current_centring_method = None
        self.current_centring_procedure = None  

    def take_snapshots_procedure(self, image_count, drawing):
        """
        Descript. :
        """
        centred_images = []
        for index in range(image_count):
            logging.getLogger("HWR").info("MiniDiff: taking snapshot #%d", index + 1)
            centred_images.append((0, str(myimage(drawing))))
            centred_images.reverse() 
        return centred_images

    def take_snapshots(self, image_count, wait = False):
        """
        Descript. :
        """
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
        try:
            self.centring_status["images"] = snapshots_procedure.get()
        except:
            logging.getLogger("HWR").exception("MiniDiff: could not take crystal snapshots")
            self.emit('centringSnapshots', (False,))
            self.emit_progress_message("")
        else:
            self.emit('centringSnapshots', (True,))
            self.emit_progress_message("")
        self.emit_progress_message("Sample is centred!")

    def stop_kappa_phi_move(self):
        return

    def move_kappa_and_phi(self, kappa_value, phi_value):
        return

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        """
        Descript. :
        """
        random_num = random.random()
        pos = {'phiy': random_num * 10,  'phiz': random_num * 20,
               'sampx': 0.0, 'sampy': 9.3, 'zoom': 8.53, 'phi': 311.1,
               'focus': -0.42, 'kappa': 0.0009, ' kappa_phi': 311.0}
        if return_by_names:
            pos = self.convert_from_obj_to_name(pos)
        return pos

    def convert_from_obj_to_name(self, motor_pos):
        motors = {}
        for motor_role in ('phiy', 'phiz', 'sampx', 'sampy', 'zoom',
                           'phi', 'focus', 'kappa', 'kappa_phi'):
            try:
               motors[motor_role] = motor_pos[None]
            except KeyError:
               motors[motor_role] = 10
        motors["beam_x"] = 10
        motors["beam_y"] = 10
        return motors 

    def get_last_video_frame(self):
        if self.camera_hwobj is not None:
            return self.camera_hwobj.get_last_frame()

    def update_values(self):
        pass

    def get_phase_list(self):
        return self.phase_list 
 
