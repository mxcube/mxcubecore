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
#   You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import os
import copy
import time
import logging
import tempfile
import gevent
import random

import lucid2

import queue_model_objects_v1 as qmo

from gevent.event import AsyncResult
from HardwareRepository import HardwareRepository
from HardwareRepository.TaskUtils import *
from HardwareRepository.BaseHardwareObjects import HardwareObject


last_centred_position = [200, 200]


class Qt4_DiffractometerMockup(HardwareObject):
    """
    Descript. :
    """
    MANUAL3CLICK_MODE = "Manual 3-click"
    C3D_MODE = "Computer automatic"
    MOVE_TO_BEAM_MODE = "Move to Beam"

    def __init__(self, *args):
        """
        Descript. :
        """
        HardwareObject.__init__(self, *args)

        qmo.CentredPosition.set_diffractometer_motor_names(\
            "phi", "focus", "phiz", "phiy", "zoom",
            "sampx", "sampy", "kappa", "kappa_phi")
        self.phiMotor = None
        self.phizMotor = None
        self.phiyMotor = None
        self.lightMotor = None
        self.zoomMotor = None
        self.sampleXMotor = None
        self.sampleYMotor = None
        self.camera = None

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
        self.centring_methods = None
        self.centring_status = None
        self.centring_time = None
        self.user_confirms_centring = None
        self.user_clicked_event = None
        self.phase_list = None

        self.connect(self, 'equipmentReady', self.equipmentReady)
        self.connect(self, 'equipmentNotReady', self.equipmentNotReady)

        #IK - this will be sorted out
        self.startCentringMethod = self.start_centring_method
        self.cancelCentringMethod = self.cancel_centring_method
        self.imageClicked = self.image_clicked
        self.acceptCentring = self.accept_centring
        self.rejectCentring = self.reject_centring
        self.getCentringStatus = self.get_centring_status
        self.takeSnapshots = self.take_snapshots
        self.moveMotors = self.move_motors

    def init(self):
        """
        Descript. :
        """
        self.x_calib = 0.000444
        self.y_calib = 0.000446
         
        self.pixels_per_mm_x = 1.0 / self.x_calib
        self.pixels_per_mm_y = 1.0 / self.y_calib
        self.beam_position = [200, 200]
        
        self.centring_methods = {
             Qt4_DiffractometerMockup.MANUAL3CLICK_MODE: self.start_3Click_centring,
             Qt4_DiffractometerMockup.C3D_MODE: self.start_automatic_centring}
        self.cancel_centring_methods = {}
        self.current_positions_dict = {'phiy'  : 0, 'phiz' : 0, 'sampx' : 0,
                                       'sampy' : 0, 'zoom' : 0, 'phi' : 17.6,
                                       'focus' : 0, 'kappa': 0, 'kappa_phi': 0,
                                       'beam_x': 0, 'beam_y': 0} 
        self.current_state_dict = {}
        self.centring_status = {"valid": False}
        self.centring_time = 0
        self.user_confirms_centring = True
        self.user_clicked_event = AsyncResult()

        self.image_width = 400
        self.image_height = 400

        self.equipmentReady()
        self.user_clicked_event = AsyncResult()

        self.phi_motor_hwobj = self.getObjectByRole('phi')
        if self.phi_motor_hwobj is not None:
            self.connect(self.phi_motor_hwobj, 'stateChanged', self.phi_motor_state_changed)
            self.connect(self.phi_motor_hwobj, "positionChanged", self.phi_motor_moved)

        self.reversing_rotation = self.getProperty("reversingRotation")
        try:
            self.grid_direction = eval(self.getProperty("gridDirection"))
        except:
            self.grid_direction = {"fast": (0, 1), "slow": (1, 0)}

        try:
            self.phase_list = eval(self.getProperty("phaseList"))
        except:
            self.phase_list = ['demo']


    def getStatus(self):
        """
        Descript. :
        """
        return "ready"

    def in_plate_mode(self):
        return True

    def is_reversing_rotation(self):
        return True

    def get_grid_direction(self):
        """
        Descript. :
        """
        print self.grid_direction
        return self.grid_direction

    def manual_centring(self):
        """
        Descript. :
        """
        self.user_clicked_event = AsyncResult()
        x, y = self.user_clicked_event.get()
        last_centred_position[0] = x
        last_centred_position[1] = y
        random_num = random.random()
        centred_pos_dir = {'phiy': random_num * 10, 'phiz': random_num, 
                         'sampx': 0.0, 'sampy': 9.3, 'zoom': 8.53,
                         'phi': 311.1, 'focus': -0.42, 'kappa': 0.0009, 
                         ' kappa_phi': 311.0}
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

    def phi_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["phi"] = pos
        self.emit_diffractometer_moved()
        self.emit("phiMotorMoved", pos)
        #self.emit('stateChanged', (self.current_state_dict["phi"], ))

    def phi_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.current_state_dict["phi"] = state
        self.emit('stateChanged', (state, ))

    def invalidate_centring(self):
        """
        Descript. :
        """
        if self.current_centring_procedure is None and self.centring_status["valid"]:
            self.centring_status = {"valid":False}
            self.emitProgressMessage("")
            self.emit('centringInvalid', ())

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        """
        Descript. :
        """
        random_num = random.random() 
        centred_pos_dir = {'phiy': random_num * 10, 'phiz': random_num,
                          'sampx': 0.0, 'sampy': 9.3, 'zoom': 8.53,
                          'phi': 311.1, 'focus': -0.42, 'kappa': 0.0009,
                          'kappa_phi': 311.0}
        return centred_pos_dir

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
        time.sleep(1)
   
    def moveToCentredPosition(self, centred_position, wait = False):
        """
        Descript. :
        """
        try:
            return self.move_to_centred_position(centred_position, wait = wait)
        except:
            logging.exception("Could not move to centred position")

    def image_clicked(self, x, y): 
        """
        Descript. :
        """
        self.user_clicked_event.set((x, y))
	
    def emit_cetring_started(self, method):
        """
        Descript. :
        """
        self.current_centring_method = method
        self.emit('centringStarted', method, False)

    def accept_centring(self):
        """
        Descript. :
        """
        self.centring_status["valid"] = True
        self.centring_status["accepted"] = True
        self.emit('centringAccepted', True, self.get_centring_status())
	
    def reject_centring(self):
        """
        Descript. :
        """
        if self.current_centring_procedure:
            self.current_centring_procedure.kill()
        self.centring_status = {"valid" : False}
        self.emit_progress_message("")
        self.emit('centringAccepted', False, self.get_centring_status())

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
            motors = {'phiy': random_num * 10,  'phiz': random_num*20,
                      'sampx': 0.0, 'sampy': 9.3, 'zoom': 8.53, 'phi': 311.1, 
		      'focus': -0.42, 'kappa': 0.0009, 'kappa_phi': 311.0}

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
        self.emit('progressMessage', (msg,))

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
        return {"phi": random_num * 10, "focus": random_num * 20, 
                "phiy" : -1.07, "phiz": -0.22, "sampx": 0.0, "sampy": 9.3,
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

    def start_set_phase(self, name):
        """
        Descript. :
        """
        return

    def refresh_video(self):
        """
        Descript. :
        """
        self.emit("minidiffStateChanged", 'testState')
        if self.beam_info_hwobj: 
            self.beam_info_hwobj.beam_pos_hor_changed(300) 
            self.beam_info_hwobj.beam_pos_ver_changed(200)

    def start_auto_focus(self): 
        """
        Descript. :
        """
        return 
  
    def move_to_coord(self, x, y):
        """
        Descript. :
        """
        return

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
            #centred_images.append((0, str(myimage(drawing))))
            #centred_images.reverse() 
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
            logging.getLogger("HWR").exception("EMBLMiniDiff: could not take crystal snapshots")
            self.emit('centringSnapshots', (False,))
            self.emit_progress_message("")
        else:
            self.emit('centringSnapshots', (True,))
            self.emit_progress_message("")
        self.emit_progress_message("Sample is centred!")

    def update_values(self):
        self.emit('zoomMotorPredefinedPositionChanged', None, None)
        omega_ref = [300, 0]
        self.emit('omegaReferenceChanged', omega_ref)

    def get_phase_list(self):
        return self.phase_list
