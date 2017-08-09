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
import random
import warnings

try:
   import lucid2
except:
   pass

import queue_model_objects_v1 as qmo

from GenericDiffractometer import GenericDiffractometer
from gevent.event import AsyncResult


last_centred_position = [200, 200]


class DiffractometerMockup(GenericDiffractometer):
    """
    Descript. :
    """

    def __init__(self, *args):
        """
        Descript. :
        """
        GenericDiffractometer.__init__(self, *args)

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
        self.current_positions_dict = {'phiy'  : 0, 'phiz' : 0, 'sampx' : 0,
                                       'sampy' : 0, 'zoom' : 0, 'phi' : 17.6,
                                       'focus' : 0, 'kappa': 11, 'kappa_phi': 12,
                                       'beam_x': 0, 'beam_y': 0}
        self.current_state_dict = {}
        self.centring_status = {"valid": False}
        self.centring_time = 0

        self.image_width = 400
        self.image_height = 400

        self.mount_mode = self.getProperty("sample_mount_mode")
        if self.mount_mode is None:
            self.mount_mode = "manual"

        self.equipment_ready()

    def getStatus(self):
        """
        Descript. :
        """
        return "ready"

    def in_plate_mode(self):
        return self.mount_mode == "plate"

    def use_sample_changer(self):
        return self.mount_mode == "sample_changer"

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
        for click in range(3):
            self.user_clicked_event = AsyncResult()
            x, y = self.user_clicked_event.get()
        last_centred_position[0] = x
        last_centred_position[1] = y
        random_num = random.random()
        centred_pos_dir = {'phiy': random_num * 10, 'phiz': random_num,
                         'sampx': 0.0, 'sampy': 9.3, 'zoom': 8.53,
                         'phi': 311.1, 'focus': -0.42, 'kappa': 11,
                         'kappa_phi': 22.0}
        return centred_pos_dir

    def automatic_centring(self):
        """Automatic centring procedure"""
        random_num = random.random()
        centred_pos_dir = {'phiy': random_num * 10, 'phiz': random_num,
                         'sampx': 0.0, 'sampy': 9.3, 'zoom': 8.53,
                         'phi': 311.1, 'focus': -0.42, 'kappa': 11,
                         'kappa_phi': 22.0}
        self.emit("newAutomaticCentringPoint", centred_pos_dir)
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

    def invalidate_centring(self):
        """
        Descript. :
        """
        if self.current_centring_procedure is None and self.centring_status["valid"]:
            self.centring_status = {"valid":False}
            #self.emitProgressMessage("")
            self.emit('centringInvalid', ())

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        """
        Descript. :
        """
        random_num = random.random() 
        centred_pos_dir = {'phiy': random_num * 10, 'phiz': random_num,
                          'sampx': 0.0, 'sampy': 9.3, 'zoom': 8.53,
                          'phi': 311.1, 'focus': -0.42, 'kappa': 11,
                          'kappa_phi': 23.0}
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
        return {"phi": random_num * 10, "focus": random_num * 20,
                "phiy" : -1.07, "phiz": -0.22, "sampx": 0.0, "sampy": 9.3,
                "kappa": 45, "kappa_phi": 30, "zoom": 8.53}

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

    def move_to_beam(self, x, y, omega=None):
        """
        Descript. : function to create a centring point based on all motors
                    positions.
        """
        
        print "moving to beam position: %d %d" % (self.beam_position[0], self.beam_position[1])
        return

    def move_to_coord(self, x, y, omega=None):
        """
        Descript. : function to create a centring point based on all motors
                    positions.
        """
        warnings.warn("Deprecated method, call move_to_beam instead", DeprecationWarning)
        return self.move_to_beam(x, y, omega)

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

    def move_kappa_and_phi(self, kappa, kappa_phi):
        return

    def get_osc_dynamic_limits(self):
        """Returns dynamic limits of oscillation axis"""
        return (0, 20)

    def get_scan_limits(self, num_images, exp_time):
        motor_acc_const = 5
        motor_acc_time = num_images / exp_time / motor_acc_const
        min_acc_time = 0.0015
        acc_time = max(motor_acc_time, min_acc_time)

        shutter_time = 3.7 / 1000.
        max_limit = num_images / exp_time * (acc_time+2*shutter_time + 0.2) / 2

        return (0, max_limit)

    def get_scan_dynamic_limits(self, speed=None):
        return (0, 20)

    def move_omega_relative(self, relative_angle):
        self.motor_hwobj_dict['phi'].syncMoveRelative(relative_angle, 5)
