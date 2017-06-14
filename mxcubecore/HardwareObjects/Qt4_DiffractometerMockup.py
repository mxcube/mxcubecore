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

try:
   import lucid2
except:
   pass

import queue_model_objects_v1 as qmo

from GenericDiffractometer import GenericDiffractometer
from gevent.event import AsyncResult


last_centred_position = [200, 200]


class Qt4_DiffractometerMockup(GenericDiffractometer):
    """
    Descript. :
    """

    def __init__(self, *args):
        """
        Descript. :
        """
        GenericDiffractometer.__init__(self, *args)

        self.phiMotor = None
        self.phizMotor = None
        self.phiyMotor = None
        self.lightMotor = None
        self.zoomMotor = None
        self.sampleXMotor = None
        self.sampleYMotor = None
        self.camera = None

    def init(self):
        """
        Descript. :
        """
        GenericDiffractometer.init(self)
        self.x_calib = 0.000444
        self.y_calib = 0.000446
         
        self.pixels_per_mm_x = 1.0 / self.x_calib
        self.pixels_per_mm_y = 1.0 / self.y_calib
        self.beam_position = [200, 200]
        
        self.cancel_centring_methods = {}
        self.current_positions_dict = {'phiy'  : 0}
        self.current_state_dict = {}
        self.centring_status = {"valid": False}
        self.centring_time = 0

        self.image_width = 400
        self.image_height = 400

        self.equipment_ready()

    def getStatus(self):
        """
        Descript. :
        """
        return "ready"

    def in_plate_mode(self):
        return True

    def use_sample_changer(self):
        return True

    def is_reversing_rotation(self):
        return True

    def get_grid_direction(self):
        """
        Descript. :
        """
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
        centred_pos_dir = {'phi': random_num}
        return centred_pos_dir 		

    def is_ready(self):
        """
        Descript. :
        """ 
        return True

    def isValid(self):
        """
        Descript. :
        """
        return True

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
        centred_pos_dir = {'phi': random_num * 10}
        return centred_pos_dir

    def get_calibration_data(self, offset):
        """
        Descript. :
        """
        #return (1.0 / self.x_calib, 1.0 / self.y_calib)
        return (1.0 / self.x_calib, 1.0 / self.y_calib)

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
        return last_centred_position[0], last_centred_position[1]

    def moveToCentredPosition(self, centred_position, wait = False):
        """
        Descript. :
        """
        try:
            return self.move_to_centred_position(centred_position, wait = wait)
        except:
            logging.exception("Could not move to centred position")

    def get_positions(self):
        """
        Descript. :
        """
        random_num = random.random()
        return {"phi": random_num * 10}

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
  
    def move_to_beam(self, x, y):
        """
        Descript. :
        """
        return

    def start_move_to_beam(self, coord_x=None, coord_y=None, omega=None):
        """
        Descript. :
        """
        self.centring_time = time.time()
        curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.centring_status = {"valid": True,
                                "startTime": curr_time,
                                "endTime": curr_time} 
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

    def update_values(self):
        self.emit('zoomMotorPredefinedPositionChanged', None, None)
        omega_ref = [300, 0]
        self.emit('omegaReferenceChanged', omega_ref)
