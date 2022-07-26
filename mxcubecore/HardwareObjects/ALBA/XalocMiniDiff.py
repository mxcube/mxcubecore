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

"""
[Name]
XalocMiniDiff

[Description]
Specific HwObj for M2D2 diffractometer @ ALBA

[Emitted signals]
- pixelsPerMmChanged
- kappaMotorMoved
- phiMotorMoved
- stateChanged
- zoomMotorPredefinedPositionChanged
- minidiffStateChanged
- minidiffPhaseChanged
"""

from __future__ import print_function

import logging
import time
import gevent
import math
import os
import tempfile
from PIL import Image
import numpy as np
from mxcubecore import HardwareRepository as HWR

logger = logging.getLogger('HWR')

try:
    logger.warning("Importing lucid3")
    import lucid3 as lucid
except ImportError:
    try:
        logger.warning("Could not find lucid3, importing lucid")
        import lucid
    except ImportError:
        logger.warning("Could not find autocentring library, automatic centring is disabled")


import queue_model_objects
import queue_entry

from GenericDiffractometer import GenericDiffractometer, DiffractometerState
from taurus.core.tango.enums import DevState

__credits__ = ["ALBA Synchrotron"]
__version__ = "3"
__category__ = "General"


class XalocMiniDiff(GenericDiffractometer):
    """
    Specific diffractometer HwObj for XALOC beamline.
    """

    def __init__(self, *args):
        GenericDiffractometer.__init__(self, *args)
        self.logger = logging.getLogger("HWR.XalocMiniDiff")
        self.userlogger = logging.getLogger("user_level_log")
        self.centring_hwobj = None
        self.super_hwobj = None
        self.chan_state = None
        self.phi_motor_hwobj = None
        self.phiz_motor_hwobj = None
        self.phiy_motor_hwobj = None
        self.zoom_motor_hwobj = None
        self.focus_motor_hwobj = None
        self.sample_x_motor_hwobj = None
        self.sample_y_motor_hwobj = None
        self.kappa_motor_hwobj = None
        self.kappa_phi_motor_hwobj = None

        self.omegaz_reference = None
        self.omegaz_reference_channel = None

        self.phi_direction = None # direction of the phi rotation angle as defined in centringMath
        self.phi_centring_direction = None # change centring direction depending on phi value
        self.saved_zoom_pos = None
        self.sample_has_been_centred = None
        
        # Number of images and total angle range used in automatic centering, defined in centring-math.xml
        self.numCentringImages = None
        self.centringAngleRange = None
        

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))

        self.centring_hwobj = self.get_object_by_role('centring')
        self.super_hwobj = self.get_object_by_role('beamline-supervisor')

        if self.centring_hwobj is None:
            self.logger.debug('XalocMinidiff: Centring math is not defined')

        if self.super_hwobj is not None:
            self.connect(
                self.super_hwobj,
                'stateChanged',
                self.supervisor_state_changed)
            self.connect(
                self.super_hwobj,
                'phaseChanged',
                self.supervisor_phase_changed)

        self.chan_state = self.get_channel_object("State")
        self.connect(self.chan_state, "update", self.state_changed)

        self.phi_motor_hwobj = self.get_object_by_role('phi')
        self.phiz_motor_hwobj = self.get_object_by_role('phiz')
        self.phiy_motor_hwobj = self.get_object_by_role('phiy')
        self.zoom_motor_hwobj = self.get_object_by_role('zoom')
        self.focus_motor_hwobj = self.get_object_by_role('focus')
        self.sample_x_motor_hwobj = self.get_object_by_role('sampx')
        self.sample_y_motor_hwobj = self.get_object_by_role('sampy')
        self.kappa_motor_hwobj = self.get_object_by_role('kappa')
        self.kappa_phi_motor_hwobj = self.get_object_by_role('kappa_phi')
        
        self.omegaz_reference_channel = self.get_channel_object("omegazReference")
        
        for axis in self.centring_hwobj.gonioAxes:
            if axis['motor_name'] == 'phi':
                self.logger.warning('XalocMinidiff: phi rotation direction is %s' % str(axis['direction']) )
                self.phi_direction = sum( axis['direction'] )
        self.phi_centring_direction = 1
        self.saved_zoom_pos = self.zoom_motor_hwobj.get_value()

        
        # For automatic centring
        self.numCentringImages = self.centring_hwobj.get_property('numCentringImages')
        if self.numCentringImages < 2: 
          self.logger.warning('XalocMinidiff: numCentringImages should be at least 2, reset to 2')
          self.numCentringImages = 2
        self.centringAngleRange = self.centring_hwobj.get_property('centringAngleRange')
        if self.centringAngleRange > 360: 
          self.logger.warning('XalocMinidiff: centringAngleRange should be smaller than 360 degrees, reset to 360 degrees')
          self.centringAngleRange = 360
        self.numAutoCentringCycles = self.centring_hwobj.get_property('numAutoCentringCycles')
        if self.centringAngleRange < 0: 
          self.logger.warning('XalocMinidiff: numAutoCentringCycles should be at least 1, reset to 1')
          self.numAutoCentringCycles = 1

        if self.phi_motor_hwobj is not None:
            self.connect(
                self.phi_motor_hwobj,
                'stateChanged',
                self.phi_motor_state_changed)
            self.connect(self.phi_motor_hwobj, "valueChanged", self.phi_motor_moved)
            self.current_motor_positions["phi"] = self.phi_motor_hwobj.get_value()
            if self.phi_motor_hwobj.get_value() > 0: self.phi_centring_direction = -1
            else: self.phi_centring_direction = 1
        else:
            self.logger.error('Phi motor is not defined')

        if self.phiz_motor_hwobj is not None:
            self.connect(
                self.phiz_motor_hwobj,
                'stateChanged',
                self.phiz_motor_state_changed)
            self.connect(
                self.phiz_motor_hwobj,
                'valueChanged',
                self.phiz_motor_moved)
            self.current_motor_positions["phiz"] = self.phiz_motor_hwobj.get_value()
        else:
            self.logger.error('Phiz motor is not defined')

        if self.phiy_motor_hwobj is not None:
            self.connect(
                self.phiy_motor_hwobj,
                'stateChanged',
                self.phiy_motor_state_changed)
            self.connect(
                self.phiy_motor_hwobj,
                'valueChanged',
                self.phiy_motor_moved)
            self.current_motor_positions["phiy"] = self.phiy_motor_hwobj.get_value()
        else:
            self.logger.error('Phiy motor is not defined')

        if self.zoom_motor_hwobj is not None:
            self.connect(
                self.zoom_motor_hwobj,
                'valueChanged',
                self.zoom_position_changed)
            self.connect(
                self.zoom_motor_hwobj,
                'predefinedPositionChanged',
                self.zoom_motor_predefined_position_changed)
            self.connect(
                self.zoom_motor_hwobj,
                'stateChanged',
                self.zoom_motor_state_changed)
        else:
            self.logger.error('Zoom motor is not defined')

        if self.sample_x_motor_hwobj is not None:
            self.connect(
                self.sample_x_motor_hwobj,
                'stateChanged',
                self.sampleX_motor_state_changed)
            self.connect(
                self.sample_x_motor_hwobj,
                'valueChanged',
                self.sampleX_motor_moved)
            self.current_motor_positions["sampx"] = self.sample_x_motor_hwobj.get_value()
        else:
            self.logger.error('Sampx motor is not defined')

        if self.sample_y_motor_hwobj is not None:
            self.connect(
                self.sample_y_motor_hwobj,
                'stateChanged',
                self.sampleY_motor_state_changed)
            self.connect(
                self.sample_y_motor_hwobj,
                'valueChanged',
                self.sampleY_motor_moved)
            self.current_motor_positions["sampy"] = self.sample_y_motor_hwobj.get_value()
        else:
            self.logger.error('Sampx motor is not defined')

        if self.focus_motor_hwobj is not None:
            self.connect(
                self.focus_motor_hwobj,
                'valueChanged',
                self.focus_motor_moved)

        if self.kappa_motor_hwobj is not None:
            self.connect(
                self.kappa_motor_hwobj,
                'stateChanged',
                self.kappa_motor_state_changed)
            self.connect(
                self.kappa_motor_hwobj,
                "valueChanged",
                self.kappa_motor_moved)
            self.current_motor_positions["kappa"] = self.kappa_motor_hwobj.get_value()
        else:
            self.logger.error('Kappa motor is not defined')

        if self.kappa_phi_motor_hwobj is not None:
            self.connect(
                self.kappa_phi_motor_hwobj,
                'stateChanged',
                self.kappa_phi_motor_state_changed)
            self.connect(
                self.kappa_phi_motor_hwobj,
                "valueChanged",
                self.kappa_phi_motor_moved)
            self.current_motor_positions["kappa_phi"] = self.kappa_phi_motor_hwobj.get_value()
        else:
            self.logger.error('Kappa-Phi motor is not defined')

        GenericDiffractometer.init(self)

        # overwrite default centring motors configuration from GenericDiffractometer
        # when using sample_centring. Fix phiz position to a reference value.
        self.omegaz_reference = self.omegaz_reference_channel.get_value()

        queue_model_objects.CentredPosition.\
            set_diffractometer_motor_names(
                "phi", "phiy", "phiz", "sampx", "sampy", "kappa", "kappa_phi")

        # TODO: Explicit update would not be necessary, but it is.
        # Added to make sure pixels_per_mm is initialised
        self.update_pixels_per_mm()

        #Set the beam_x and beam_y positions so the center point is kept
        self.current_motor_positions["beam_x"] = (self.beam_position[0] - \
             self.zoom_centre['x'] )/self.pixels_per_mm_x
        self.current_motor_positions["beam_y"] = (self.beam_position[1] - \
             self.zoom_centre['y'] )/self.pixels_per_mm_y


    def state_changed(self, state):
        """
        Overwrites method to map Tango ON state to Diffractometer State Ready.

        @state: Taurus state but string for Ready state
        """
        if state == DevState.ON:
            state = DiffractometerState.tostring(DiffractometerState.Ready)

        if state != self.current_state:
            #self.logger.debug("State changed %s (was: %s)" %
                #(str(state), self.current_state))
            self.current_state = state
            self.emit("minidiffStateChanged", (self.current_state))

    def getCalibrationData(self, offset=None):
        """
        Returns the number of pixels per mm for the camera image

        @offset: Unused
        @return: 2-tuple float

        """
        #self.logger.debug("Getting calibration data")
        calibx, caliby = [1,1]
        if self.zoom_motor_hwobj != None:
            calibx, caliby = self.zoom_motor_hwobj.get_calibration()
        else: 
            self.userlogger.error('zoom_motor_hwobj not defined. The bzoom camera DS probably needs to be reset ')
        return 1000.0 / calibx, 1000.0 / caliby

    def get_pixels_per_mm(self):
        """
        Returns the pixel/mm for x and y. Overrides GenericDiffractometer method.
        """
        px_x, px_y = self.getCalibrationData()
        return px_x, px_y

    def update_pixels_per_mm(self, *args):
        """
        Emit signal with current pixel/mm values.
        """
        self.pixels_per_mm_x, self.pixels_per_mm_y = self.getCalibrationData()
        self.emit('pixelsPerMmChanged', ((self.pixels_per_mm_x, self.pixels_per_mm_y), ))

    # Overwrite from generic diffractometer
    def update_zoom_calibration(self):
        """
        """
        self.update_pixels_per_mm()

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        """
        Returns a dictionary with motors name and positions centred corresponding to the camera image point with 
           coordinates x and y.
        It is expected in start_move_to_beam and move_to_beam methods in
        GenericDiffractometer HwObj, 
        Also needed for the calculation of the motor positions after definition of the mesh grid 
            (Qt4_GraphicsManager, update_grid_motor_positions)

        point x,y is relative to the lower left corner on the camera, this functions returns the motor positions for that point,
        where the motors that are changed are phiy and phiz. 
        
        @return: dict
        """
        #self.logger.info('get_centred_point_from_coord x %s and y %s and return_by_names %s' % ( x, y, return_by_names ) )
        #self.logger.info('get_centred_point_from_coord pixels_per_mm_x %s and pixels_per_mm_y %s' % ( self.pixels_per_mm_x, self.pixels_per_mm_y ) )
        #self.logger.info('get_centred_point_from_coord beam_position[0] %s and beam_position[1] %s' % 
                                          #( self.beam_position[0], self.beam_position[1] ) 
                                      #)

        self.update_zoom_calibration()
        
        loc_centred_point = {}
        loc_centred_point['phi'] = self.phi_motor_hwobj.get_value()
        loc_centred_point['kappa'] = self.kappa_motor_hwobj.get_value()
        loc_centred_point['kappa_phi'] = self.kappa_phi_motor_hwobj.get_value()
        loc_centred_point['phiy'] = self.phiy_motor_hwobj.get_value() - ( 
                                           ( float( x ) - float( self.beam_position[0] ) ) / 
                                           float( self.pixels_per_mm_x )
                                        )

        # Overwrite phiz, which should remain in the actual position, hopefully the center of rotation
        omegaz_diff = 0
        if self.omegaz_reference_channel != None: 
            self.omegaz_reference = self.omegaz_reference_channel.get_value()
            loc_centred_point['phiz'] = self.omegaz_reference
            omegaz_diff = self.phiz_motor_hwobj.get_value() - self.omegaz_reference
        else: 
            loc_centred_point['phiz'] = self.phiz_motor_hwobj.get_value() 

        # Calculate the positions of sampx and sampy that correspond to the camera x,y coordinates
        vertdist = omegaz_diff + ( float( y ) - float ( self.beam_position[1] ) ) / float (self.pixels_per_mm_y ) 
        sampxpos = self.sample_x_motor_hwobj.get_value()
        sampypos = self.sample_y_motor_hwobj.get_value()
        dx, dy = self.vertical_dist_to_samp_pos (self.phi_motor_hwobj.get_value() , vertdist)
        
        loc_centred_point['sampx'] = sampxpos + dy
        loc_centred_point['sampy'] = sampypos + dx

        # 20220706 RB: These lines cause the grid to move to the center of camera, do not use!
        #if return_by_names:
            #loc_centred_point = self.convert_from_obj_to_name(loc_centred_point)

        self.logger.info('get_centred_point_from_coord loc_centred_point %s ' % ( loc_centred_point ) )
        
        return loc_centred_point

    def vertical_dist_to_samp_pos(self, phipos, vertdist):
        """
          returns the relative displacement of sampx and sampy 
        """
        d_sampx = 0
        d_sampy = 0

        #self.logger.debug("phipos %.4f , vertdist %.4f" % ( phipos, vertdist ) ) 

        if self.use_sample_centring: 
            phi_angle = math.radians(self.centring_phi.direction * \
                    phipos )
        else: 
            phi_angle = math.radians( phipos * self.phi_direction )

        #self.logger.debug("phi_angle %.4f" % ( phi_angle ) ) 

        d_sampy = math.cos(phi_angle) * vertdist
        d_sampx = math.sin(phi_angle) * vertdist
        
        return d_sampy, d_sampx

    # RB: Never called?
    #def getBeamInfo(self, update_beam_callback):
        #"""
        #Update beam info (position and shape) ans execute callback.

        #@update_beam_callback: callback method passed as argument.
        #"""
        #size_x = self.getChannelObject("beamInfoX").get_value() / 1000.0
        #size_y = self.getChannelObject("beamInfoY").get_value() / 1000.0

        #data = {
            #"size_x": size_x,
            #"size_y": size_y,
            #"shape": "ellipse",
        #}

        #update_beam_callback(data)

    # TODO:Implement dynamically
    def use_sample_changer(self):
        """
        Overrides GenericDiffractometer method.
        """
        return True

    # TODO:Implement dynamically
    def in_plate_mode(self):
        """
        Overrides GenericDiffractometer method.
        """
        return False

    # overwrite generic diff method to avoid centering when mounting fails
    def start_centring_method(self, method, sample_info=None, wait=False):
        """
        """

        if self.current_centring_method is not None:
            logging.getLogger("HWR").error(
                "Diffractometer: already in centring method %s"
                % self.current_centring_method
            )
            return
        curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.centring_status = {
            "valid": False,
            "startTime": curr_time,
            "angleLimit": None,
        }
        self.emit_centring_started(method)

        try:
            centring_method = self.centring_methods[method]
        except KeyError as diag:
            logging.getLogger("HWR").error(
                "Diffractometer: unknown centring method (%s)" % str(diag)
            )
            self.emit_centring_failed()
        else:
            if HWR.beamline.sample_changer.sample_can_be_centered:
                try:
                    self.prepare_centring()
                except Exception as e:
                    self.userlogger.error("The diffractometer could not be prepared for centering, warn the lc/floor coordinator")
                    raise Exception(e)
                try:
                    centring_method(sample_info, wait_result=wait)
                except Exception:
                    logging.getLogger("HWR").exception(
                        "Diffractometer: problem while centring"
                    )
                    self.emit_centring_failed()
            else:
                logging.getLogger("HWR").error(
                    "Diffractometer: there was a problem in loading the sample, centering cancelled"
                )
                self.emit_centring_failed()
                

    def manual_centring(self):
        """
        Descript. :
        """
        self.centring_hwobj.initCentringProcedure()
        if not self.sample_has_been_centred: 
            self.zoom_motor_hwobj.move_to_position( 1 )
            
        for click in range(3):
            self.user_clicked_event = gevent.event.AsyncResult()
            x, y = self.user_clicked_event.get()
            #logger.debug("manual_centring : x %s, y %s" % ( str(x), str(y) ) )       
            self.centring_hwobj.appendCentringDataPoint(
                 {"X": (x - self.beam_position[0])/ self.pixels_per_mm_x,
                  "Y": (y - self.beam_position[1])/ self.pixels_per_mm_y})
            if self.in_plate_mode():
                pass
                ##dynamic_limits = self.phi_motor_hwobj.getDynamicLimits()
                #dynamic_limits = self.get_osc_limits()
                #if click == 0:
                    #self.motor_hwobj_dict['phi'].set_value(dynamic_limits[0] + 0.5)
                #elif click == 1:
                    #self.motor_hwobj_dict['phi'].set_value(dynamic_limits[1] - 0.5)
                #elif click == 2:
                    #self.motor_hwobj_dict['phi'].set_value((dynamic_limits[0] + \
                                                       #dynamic_limits[1]) / 2.)
            else:
                if click < 2:
                    new_pos = self.motor_hwobj_dict['phi'].get_value() + ( self.phi_centring_direction * 90 )
                    self.motor_hwobj_dict['phi'].set_value( new_pos )
        #self.omega_reference_add_constraint()
        centred_pos_dict = self.centring_hwobj.centeredPosition(return_by_name=False)
        
        # Fix the omegaz (phiz) motor position to the known center
        centred_pos_dict[ self.motor_hwobj_dict['phiz'] ] = self.omegaz_reference

        if not self.sample_has_been_centred: 
            self.zoom_motor_hwobj.move_to_position( self.saved_zoom_pos)
            self.sample_has_been_centred = True

        #self.logger.debug( "centred_pos_dict %s" % str( centred_pos_dict ) )
        
        return centred_pos_dict
    
    def move_to_beam(self, x, y, omega=None):
        """
        Descript. : function to create a centring point based on all motors
                    positions.
        """
        logging.getLogger("HWR").debug("move_to_beam x %s y %s" % (x,y) )
        
        try:
            pos = self.get_centred_point_from_coord(x, y, return_by_names=False)
            if omega is not None:
                pos["phiMotor"] = omega
            self.move_to_motors_positions(pos)
            self.centring_status["motors"] = self.convert_from_obj_to_name( pos )
            logging.getLogger("HWR").debug("centring_status %s" % self.centring_status)
        except Exception:
            logging.getLogger("HWR").exception(
                "Diffractometer: could not center to beam, aborting"
            )



    #def start_move_to_beam(self, coord_x=None, coord_y=None, omega=None, wait_result=None):
        #"""
        #Descript. :
        #"""
        
        ##TODO: add these things to a queue and execute the queue in the end.
        #try:
            #self.emit_progress_message("Move to beam...")
            #self.centring_time = time.time()
            #curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
            #self.centring_status = {"valid": True,
                                    #"startTime": curr_time,
                                    #"endTime": curr_time}
            #if (coord_x is None and
                #coord_y is None):
                #coord_x = self.beam_position[0]
                #coord_y = self.beam_position[1]

            #self.start_automatic_centring()
            
            ##TODO: should this be in the queue entry mount_sample method, calling XrayCenteringQueueEntry?
            #self.current_centring_procedure_list = gevent.spawn ( self.start_3d_mesh_centring() )
        #except Exception as ex:
            #raise Exception(ex)

    # Override GenericDiffractometer to add prepare_centring, which sets omega velocity to 60. 
    def start_automatic_centring(self, sample_info=None, loop_only=False, wait_result=None):
        """
        Start Automatic centring. Overrides GenericDiffractometer method.
        Prepares diffractometer for automatic centring.
        """
        self.automatic_centring_try_count = 0
        
        self.logger.debug('automatic_centring_try_count, numAutoCentringCycles: %d, %d' % \
                          (self.automatic_centring_try_count, self.numAutoCentringCycles) ) 
        
        #TODO: whould the wait_result argument to start_automatic_centring be set to True?
        self.emit_progress_message("Automatic centring...")

        #self.logger.debug('Start automatic centring: %s' % self.pixels_per_mm_x)
        if self.use_sample_centring:
            if self.numAutoCentringCycles > 1: 
                self.logger.debug( 'Multiple centring not supported when use_sample_centring is set to True' )
                self.userlogger.info( 'Started 1 cycle of automatic centring' )
                self.current_centring_procedure = \
                    sample_centring.start_auto(self.camera_hwobj,
                                                {"phi": self.centring_phi,
                                                "phiy": self.centring_phiy,
                                                "sampx": self.centring_sampx,
                                                "sampy": self.centring_sampy,
                                                "phiz": self.centring_phiz },
                                                self.pixels_per_mm_x,
                                                self.pixels_per_mm_y,
                                                self.beam_position[0],
                                                self.beam_position[1],
                                                msg_cb = self.emit_progress_message,
                                                new_point_cb=lambda point: self.emit("newAutomaticCentringPoint", (point,)))
        else:
            #TODO: can this be added to a queue and execute the queue? SampleCentringQueueEntry does not work for this
            # GPHL uses queue_model_objects.SampleCentring in enqueue_sample_centring
            self.userlogger.info( 'Started %d cycles of automatic centring' % self.numAutoCentringCycles )
            for i in range(self.numAutoCentringCycles):
                self.current_centring_procedure = gevent.spawn( self.automatic_centring, i )
                self.current_centring_procedure.link(self.centring_done)

        # TODO: fix this somewhere else, after moving the motors! 
        # Activate the sample tree after centring
        #self.accept_centring()
        
        self.zoom_motor_hwobj.move_to_position( self.saved_zoom_pos)
        #self.backlight_hwobj.setLevel( self.saved_backlight_level )
        
        #TODO: make method called finish_centring to reset values?

    #def accept_centring(self):
        #"""
        #Descript. :
        #Arg.      " fully_centred_point. True if 3 click centring
                    #else False
        #"""
        #logging.getLogger("HWR").debug("accept_centring: centring_status %s" % self.centring_status)
        #self.centring_status["valid"] = True
        #self.centring_status["accepted"] = True
        #centring_status = self.get_centring_status()
        #if "motors" not in centring_status:
            #logging.getLogger("HWR").debug("getting stored motor positions %s" % self.get_positions() )
            #centring_status["motors"] = self.get_positions()
        #self.emit("centringAccepted", (True, centring_status))
        #self.emit("fsmConditionChanged", "centering_position_accepted", True)
       
    def automatic_centring(self, pid):
        """Automatic centring procedure. Rotates n times and executes
           centring algorithm. Optimal scan position is detected.
        """

        #self.logger.info("Cued new automatic centring number %d" % pid+1)

        # wait till it is the turn of this cycle
        stime = time.time()
        timeout = 20 * ( pid + 1 )
        while pid != self.automatic_centring_try_count:
            gevent.sleep(1)
            if time.time() - stime > timeout: 
                self.cancel_centring_method()

        self.userlogger.info("Started new automatic centring cycle %d of %d" % ( pid+1, self.numAutoCentringCycles ) )

        if self.phi_motor_hwobj.get_value() > 0: self.phi_centring_direction = -1
        else: self.phi_centring_direction = 1

        # This cycle now starts
        if pid == 0: 
            self.zoom_motor_hwobj.move_to_position(1)
            gevent.sleep(0.1) # wait for zoom update
        else: 
            self.zoom_motor_hwobj.move_to_position(4)
            gevent.sleep(1) # wait for motors from previous centrings to start moving
        
        self.wait_device_ready(20) # wait for motors from previous centrings to finish
 
        #self.logger.debug('find_loop output %s' % str(self.find_loop_xaloc()) )

        # check if loop is there, if not, search
        it = 0
        maxit = 3
        x, y, info, surface_score = self.find_loop_xaloc()
        while ( -1 in [x,y]) and it < maxit: 
            self.logger.debug('-1 in first x,y find_loop output %s, %s' % ( str(x), str(y) ) )
            if not self.search_pin(): 
                self.userlogger.error("Reached minimal position for omegax, sample cannot be found, aborting centring")
                self.phiy_motor_hwobj.set_value(0, timeout = 5 )
                self.cancel_centring_method(True)
                return
            it += 1
            gevent.sleep(0.1)
            x, y, info, surface_score = self.find_loop_xaloc()
        else: 
            if -1 in [x,y]: self.cancel_centring_method()
        
        # check if loop is past camera, and the pin is seen. If so, first move loop out
        it = 0
        image_edge_margin = 100
        while x < image_edge_margin and it < maxit: 
            self.logger.debug('x < image_edge_margin, x and y from find_loop %s, %s' % ( str(x), str(y) ) )
            self.retreat_pin()
            it += 1
            gevent.sleep(0.1)
            x, y, info, surface_score = self.find_loop_xaloc()
        else: 
            if ( -1 in [x,y] ) or y < image_edge_margin : self.cancel_centring_method()
 
        surface_score_list = []
        self.centring_hwobj.initCentringProcedure()
        #self.logger.debug("self.numCentringImages %d, self.centringAngleRange %d" % \
              #(self.numCentringImages, self.centringAngleRange) )
        for image in range( self.numCentringImages ):
            if self.current_centring_method == None: break
            #self.logger.debug("Harvesting fotos for automatic_centring : x %s, y %s, info %s, surface_score %s" % 
                              #( str(x), str(y), str(info), str(surface_score) ) ) 
            if x > 0 and y > 0:
                self.centring_hwobj.appendCentringDataPoint(
                    {"X": (x - self.beam_position[0])/ self.pixels_per_mm_x,
                     "Y": (y - self.beam_position[1])/ self.pixels_per_mm_y})
            surface_score_list.append(surface_score)
            # Now rotate and take another point
            if image < self.numCentringImages - 1: # Last rotation is not necessary
                new_pos = self.motor_hwobj_dict['phi'].get_value() + ( self.phi_centring_direction * \
                    self.centringAngleRange/ ( self.numCentringImages - 1 ) )
                self.motor_hwobj_dict['phi'].set_value( new_pos, timeout = 5 )
                gevent.sleep(0.01)
                self.wait_device_ready(15)
                x, y, info, surface_score = self.find_loop_xaloc()
        #self.omega_reference_add_constraint()
        centred_pos_dict = self.centring_hwobj.centeredPosition(return_by_name=False)
        self.emit("newAutomaticCentringPoint", centred_pos_dict)
    

        #TODO: add the difference between self.motor_hwobj_dict['phiz'] and self.omegaz_reference to centx & centy
        vertdist = centred_pos_dict[ self.motor_hwobj_dict['phiz'] ] - self.omegaz_reference 
        # Fix the omegaz (phiz) motor position to the known center
        #self.logger.debug("Calculated phiz %.4f, difference with reference %.4f" % \
        #      (centred_pos_dict[ self.motor_hwobj_dict[ 'phiz' ] ] , vertdist ) )
        
        dx = 0
        dy = 0
        dx, dy = self.vertical_dist_to_samp_pos (self.phi_motor_hwobj.get_value() , -vertdist)
        centred_pos_dict[ self.motor_hwobj_dict['phiz'] ] = self.omegaz_reference
        centred_pos_dict[ self.motor_hwobj_dict['sampx'] ] = centred_pos_dict[ self.motor_hwobj_dict['sampx'] ] + dy
        centred_pos_dict[ self.motor_hwobj_dict['sampy'] ] = centred_pos_dict[ self.motor_hwobj_dict['sampy'] ] + dx

        #self.logger.debug( "centred_pos_dict %s" % str( centred_pos_dict ) )

        self.automatic_centring_try_count += 1
                                                                                     
        return centred_pos_dict

    def retreat_pin(self):
        hor_mot_hwobj = self.phiy_motor_hwobj
        half_camera_width_mm = HWR.beamline.sample_view.camera.get_width() / self.pixels_per_mm_x / 2 # half camera width in mm
        #self.logger.debug( "half camera_width_mm %.4f" % half_camera_width_mm )
        hor_mot_hwobj.set_value( hor_mot_hwobj.get_value() + half_camera_width_mm, timeout = 6 ) 
        gevent.sleep(0.1) # wait for zoom update

    def search_pin(self):
        spindle_mot_hwobj = self.phi_motor_hwobj
        hor_mot_hwobj = self.phiy_motor_hwobj
        
        # Save initial velocity
        hor_mot_ini_vel = hor_mot_hwobj.get_velocity()
        
        # get camera width in mm
        camera_width_mm = HWR.beamline.sample_view.camera.get_width() / self.pixels_per_mm_x # full camera width in mm
        #self.logger.debug( "camera_width_mm %.4f" % camera_width_mm )
        
        #TODO:check the limit of the phiy motor and make relative movement smalle if necessary
        relmovdist = 0
        if camera_width_mm > math.fabs( hor_mot_hwobj.get_limits()[0] - hor_mot_hwobj.get_value() ):
            relmovdist = math.fabs( hor_mot_hwobj.get_limits()[0] - hor_mot_hwobj.get_value() ) - 0.002
        else: relmovdist = camera_width_mm
        if relmovdist < 0.003: return False #omegax at minimum
        
        # set horizontal motor velocity so that a full camera with can be scanned with 180 deg rotation of spindle axis
        time_for_scan = 180 / spindle_mot_hwobj.get_velocity() + 0.01 # in seconds
        hor_vel = camera_width_mm / time_for_scan
        #self.logger.debug( "Calculated horizontal velocity %.4f" % hor_vel )
        if hor_vel < hor_mot_hwobj.get_velocity(): 
            if hor_vel < 0.001: hor_vel = 0.001
            else: hor_mot_hwobj.set_velocity(hor_vel)
    
        #self.logger.debug( 'hor mot pos channel info %s' % str( hor_mot_hwobj.position_channel.get_info().minval ) )
        #self.logger.debug( 'hor mot limits %s' % str( hor_mot_hwobj.get_limits() ) )
        
        # start the motor positions asynchronously 
        self.logger.debug("Moving omegax relative %s" % relmovdist)
        hor_mot_hwobj.set_value( hor_mot_hwobj.get_value() - relmovdist )
        spindle_mot_hwobj.set_value( spindle_mot_hwobj.get_value() + 180 )
        
        # Keep  checking the location of the loop. When found, stop the motor movements
        stime = time.time()
        while time.time() - stime < time_for_scan:
            if not ( -1 in self.find_loop_xaloc()[:1] ):
                hor_mot_hwobj.stop()
                spindle_mot_hwobj.stop()
                break
            gevent.sleep(0.1)
        
        # reset the velocities
        hor_mot_hwobj.set_velocity(hor_mot_ini_vel)
        return True

    #def start_3d_mesh_centring(self):
        ## first wait for optical centring to finish
        #timeout = self.numAutoCentringCycles  * 20
        #while self.automatic_centring_try_count < self.numAutoCentringCycles and time.time()-stime < timeout:
            #gevent.sleep(1)
        
        #self.logger.debug("Starting 3d centring")
        ## setup collection
        ## based on Qt4_create_task_base create_task method
        ##TODO: get sample instance
        #mesh_dc = self._create_dc_from_grid( sample )
        #mesh_dc.run_processing_parallel = "XrayCentering"
        #xray_centering = queue_model_objects.XrayCentering(mesh_dc)
        

    #def create_dc_from_grid(self, sample, grid=None):
        #if grid is None:
            #grid = self._graphics_manager_hwobj.get_auto_grid()

        #grid.set_snapshot(self._graphics_manager_hwobj.\
                          #get_scene_snapshot(grid))

        #grid_properties = grid.get_properties()

        #acq = self._create_acq(sample)
        #acq.acquisition_parameters.centred_position = \
            #grid.get_centred_position()
        #acq.acquisition_parameters.mesh_range = \
            #[grid_properties["dx_mm"],
             #grid_properties["dy_mm"]]
        #acq.acquisition_parameters.num_lines = \
            #grid_properties["num_lines"]
        #acq.acquisition_parameters.num_images = \
            #grid_properties["num_lines"] * \
            #grid_properties["num_images_per_line"]
        #grid.set_osc_range(acq.acquisition_parameters.osc_range)

        #processing_parameters = deepcopy(self._processing_parameters)

        #dc = queue_model_objects.DataCollection([acq],
                                                #sample.crystals[0],
                                                #processing_parameters)

        #dc.set_name(acq.path_template.get_prefix())
        #dc.set_number(acq.path_template.run_number)
        #dc.set_experiment_type(queue_model_enumerables.EXPERIMENT_TYPE.MESH)
        #dc.set_requires_centring(False)
        #dc.grid = grid

        #self._path_template.run_number += 1

        #return dc


    def motor_positions_to_screen(self, centred_positions_dict):
        """
        Descript. :
        """
        c = centred_positions_dict

        #kappa = self.current_motor_positions["kappa"]
        #phi = self.current_motor_positions["kappa_phi"]

        kappa = self.motor_hwobj_dict['kappa'].get_value()
        phi = self.motor_hwobj_dict['kappa_phi'].get_value()
        #IK TODO remove this director call

        # TODO:implement minikappa_correction_hwobj
        #if (c['kappa'], c['kappa_phi']) != (kappa, phi) \
         #and self.minikappa_correction_hwobj is not None:
            ##c['sampx'], c['sampy'], c['phiy']
            #c['sampx'], c['sampy'], c['phiy'] = self.minikappa_correction_hwobj.shift(
            #c['kappa'], c['kappa_phi'], [c['sampx'], c['sampy'], c['phiy']], kappa, phi)

        #TODO: beam_x and beam_y are not part of c? These give difference in beam pos with respect to center
        #self.logger.debug('motor_positions_to_screen, zoom_centre x %d, y %d' % \
                          #(self.zoom_centre['x'], self.zoom_centre['y']) ) 
        #self.logger.debug('motor_positions_to_screen, pixels_per_mm_x %d, y %d' % \
                          #(self.pixels_per_mm_x, self.pixels_per_mm_y) ) 
        beam_x = ( self.beam_position[0] - self.zoom_centre['x'] ) / self.pixels_per_mm_x
        beam_y = ( self.beam_position[1] - self.zoom_centre['y'] ) / self.pixels_per_mm_y
        
        xy = self.centring_hwobj.centringToScreen(c)
        #self.logger.debug( 'xy dict %s' % str(xy) )
        if xy:
            #self.logger.debug( 'xy[\'X\'] %s xy[\'Y\'] %s' % ( xy['X'], xy['Y'] ) )
            x = ( xy['X'] + beam_x ) * self.pixels_per_mm_x + \
                 self.zoom_centre['x']
            y = ( xy['Y'] + beam_y ) * self.pixels_per_mm_y + \
                 self.zoom_centre['y']
            #self.logger.debug( 'x %4.2f y %4.2f' % ( x, y ) )
            return x, y

    def centring_done(self, centring_procedure):
        """
        Descript. :
        """
        try:
            motor_pos = centring_procedure.get()
            if isinstance(motor_pos, gevent.GreenletExit):
                raise motor_pos
        except:
            logging.exception("Could not complete centring")
            self.emit_centring_failed()
        else:
            self.emit_progress_message("Moving sample to centred position...")
            self.emit_centring_moving()

            try:
                # msg = ''
                # for mot, pos in motor_pos.items():
                #     msg += '%s = %s\n' % (str(mot.name()), pos)
                logging.getLogger("HWR").debug("Centring finished")#. Moving motors to:\n%s" % msg)
                self.move_to_motors_positions(motor_pos, wait=True)
            except:
                logging.exception("Could not move to centred position")
                self.emit_centring_failed()
            else:
                #if 3 click centring move -180. well. dont, in principle the calculated
                # centred positions include omega to initial position
                pass
                #if not self.in_plate_mode():
                #    logging.getLogger("HWR").debug("Centring finished. Moving omega back to initial position")
                #    self.motor_hwobj_dict['phi'].set_value(self.motor_hwobj_dict['phi'].get_value() - 180, timeout = 4 )
                #    logging.getLogger("HWR").debug("         Moving omega done")

            #if self.current_centring_method == GenericDiffractometer.CENTRING_METHOD_AUTO:
            #    self.emit("newAutomaticCentringPoint", motor_pos)
            self.ready_event.set()
            self.centring_time = time.time()
            self.update_centring_status(motor_pos)
            if self.current_centring_method == GenericDiffractometer.CENTRING_METHOD_AUTO and  \
                self.automatic_centring_try_count == self.numAutoCentringCycles or \
                self.current_centring_method != GenericDiffractometer.CENTRING_METHOD_AUTO: 
                self.emit_centring_successful()
                self.emit_progress_message("")

    def update_centring_status(self, motor_pos):
        curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.centring_status["endTime"] = curr_time
        self.centring_status["motors"] = self.convert_from_obj_to_name(motor_pos)
        self.centring_status["method"] = self.current_centring_method
        self.centring_status["valid"] = True

    def emit_centring_successful(self):
        """
        Descript. :
        """
        method = self.current_centring_method
        self.emit('centringSuccessful', (method, self.get_centring_status()))
        self.current_centring_method = None
        self.current_centring_procedure = None

    def find_loop_xaloc(self):
        """
        Description:
        """

        #=================================================================================

        # the following lines are used because the lucid3 package installed at xaloc 
        #      does not allow an array as argument. Lucid3 should be updated to use the code below
        #self.logger.debug("starting find_loop")       
        #snapshot_filename = os.path.join(tempfile.gettempdir(), "mxcube_sample_snapshot.png")
        #image_array = HWR.beamline.sample_view.camera.get_snapshot(return_as_array=True)
        ## Now flip the image and convert to PIL type image
        #im = Image.fromarray( np.fliplr( image_array ) )
        #im.save( snapshot_filename )
        ##self.logger.debug("in find_loop: snapshot_filename is %s" % snapshot_filename)       
        #(info, x, y) = lucid.find_loop( snapshot_filename , IterationClosing=6 )
        #self.logger.debug('Lucid output: info %s x %s y %s' % ( str(info), str(x), str(y) ) )

        #the following lines should be used when lucid3 is updated to the newest version 
        image_array = HWR.beamline.sample_view.camera.get_snapshot(return_as_array=True)
        #self.logger.debug("image_array: %s" % str(image_array))
        #self.logger.debug("type( image_array ): %s" % str( type(image_array) ) )
        if type( image_array ) == str: self.logger.debug("image_array  is a string" )
        image_array = np.fliplr( image_array )
        (info, x, y) = lucid.find_loop( image_array , IterationClosing=6 )
        #self.logger.debug('Lucid output: info %s x %s y %s' % ( str(info), str(x), str(y) ) )
        
        #=================================================================================
        
        #self.logger.debug("find_loop output : info %s, x %s, y %s" % ( str(info), str(x), str(y) ) )       
        if x > 0 and y > 0:
            x = 900 - x
        
        surface_score = 10
        return x, y, info, surface_score

    def prepare_centring(self):
        """
        Prepare beamline for to sample_view phase.
        """

        self.saved_zoom_pos = self.zoom_motor_hwobj.get_value()

        if not self.super_hwobj.get_current_phase().upper() == "SAMPLE":
            self.logger.info("Not in sample view phase. Asking supervisor to go")
            success = self.go_sample_view()
            # TODO: workaround to set omega velocity to 60
            try:
                self.phi_motor_hwobj.set_velocity(60)
            except:
                self.logger.error("Cannot apply workaround for omega velocity")
            if not success:
                self.logger.error("Cannot set SAMPLE VIEW phase")
                return False
        # TODO: dynamic omegaz_reference
        if self.omegaz_reference_channel != None:
            if self.use_sample_centring: self.centring_phiz.reference_position = self.omegaz_reference_channel.get_value()
            self.omegaz_reference = self.omegaz_reference_channel.get_value()

        if self.phi_motor_hwobj.get_value() > 0: self.phi_centring_direction = -1
        else: self.phi_centring_direction = 1

        return True

    def omega_reference_add_constraint(self):
        """
        Descript. : WHAT DOES THIS DO?
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

    def move_to_motors_positions(self, motors_positions, wait=False):
        """
        """
        self.emit_progress_message("Moving to motors positions...")
        self.move_to_motors_positions_procedure = gevent.spawn(\
             self.move_motors, motors_positions)
        self.move_to_motors_positions_procedure.link(self.move_motors_done)
        if wait:
            self.wait_device_not_ready(50)
            self.wait_device_ready(10)
 
    def get_grid_direction(self):
        
        grid_direction = self.get_property("gridDirection")

        grid_direction = {}
        self.grid_direction['omega_ref'] = 1
        self.grid_direction['fast'] = [ 1, 0 ] # Qt4_GraphicsLib.py line 1184/85 MD2
        self.grid_direction['slow'] = [ 0, -1 ] # Qt4_GraphicsLib.py line 1184/85 MD2
        self.logger.info('diffr_hwobj grid_direction %s' % self.grid_direction)
        
        return self.grid_direction
        
    def go_sample_view(self):
        """
        Go to sample view phase.
        """
        self.super_hwobj.go_sample_view()

        while True:
            super_state = self.super_hwobj.get_state()
            self.logger.debug('Waiting for go_sample_view done (supervisor state is %s)'
                              % super_state)
            if super_state != DevState.MOVING:
                self.logger.debug('Go_sample_view done (%s)' % super_state)
                return True
            time.sleep(0.2)

    def supervisor_state_changed(self, state):
        """
        Emit stateChanged signal according to supervisor current state.
        """
        return
        self.current_state = state
        self.emit('stateChanged', (self.current_state, ))

    # TODO: Review override current_state by current_phase
    def supervisor_phase_changed(self, phase):
        """
        Emit stateChanged signal according to supervisor current phase.
        """
        #self.current_state = phase
        self.emit('minidiffPhaseChanged', (phase, ))

    def phi_motor_moved(self, pos):
        """
        Emit phiMotorMoved signal with position value.
        """
        self.current_motor_positions["phi"] = pos
        self.emit("phiMotorMoved", pos)

    def phi_motor_state_changed(self, state):
        """
        Emit stateChanged signal with state value.
        """
        self.emit('stateChanged', (state, ))

    def phiz_motor_moved(self, pos):
        """
        """
        self.current_motor_positions["phiz"] = pos

    def phiz_motor_state_changed(self, state):
        """
        Emit stateChanged signal with state value.
        """
        self.emit('stateChanged', (state, ))

    def phiy_motor_state_changed(self, state):
        """
        Emit stateChanged signal with state value.
        """
        self.emit('stateChanged', (state, ))

    def phiy_motor_moved(self, pos):
        """
        """
        self.current_motor_positions["phiy"] = pos

    def zoom_position_changed(self, value):
        """
        Update positions after zoom changed.

        @value: zoom position.
        """
        #self.logger.debug("zoom position changed")
        self.update_pixels_per_mm()
        self.current_motor_positions["zoom"] = value

    def zoom_motor_predefined_position_changed(self, position_name, offset):
        """
        Update pixel size and emit signal.
        """
        #self.logger.debug("zoom predefined position changed")
        self.update_pixels_per_mm()
        self.emit('zoomMotorPredefinedPositionChanged',
                  (position_name, offset, ))

    def zoom_motor_state_changed(self, state):
        """
        Emit signal for motor zoom changed

        @state: new state value to emit.
        """
        self.emit('stateChanged', (state, ))

    def sampleX_motor_moved(self, pos):
        """
        """
        self.current_motor_positions["sampx"] = pos

    def sampleX_motor_state_changed(self, state):
        """
        Emit stateChanged signal with state value.
        """
        self.current_motor_states["sampx"] = state
        self.emit('stateChanged', (state, ))

    def sampleY_motor_moved(self, pos):
        """
        """
        self.current_motor_positions["sampy"] = pos

    def sampleY_motor_state_changed(self, state):
        """
        Emit stateChanged signal with state value.
        """
        self.current_motor_states["sampy"] = state
        self.emit('stateChanged', (state, ))

    def kappa_motor_moved(self, pos):
        """
        Emit kappaMotorMoved signal with position value.
        """
        self.current_motor_positions["kappa"] = pos
        self.emit("kappaMotorMoved", pos)

    def kappa_motor_state_changed(self, state):
        """
        Emit stateChanged signal with state value.
        """
        self.current_motor_states["kappa"] = state
        self.emit('stateChanged', (state, ))

    def kappa_phi_motor_moved(self, pos):
        """
        Emit kappa_phiMotorMoved signal with position value.
        """
        self.current_motor_positions["kappa_phi"] = pos
        self.emit("kappa_phiMotorMoved", pos)

    def kappa_phi_motor_state_changed(self, state):
        """
        Emit stateChanged signal with state value.
        """
        self.current_motor_states["kappa_phi"] = state
        self.emit('stateChanged', (state, ))

    def focus_motor_moved(self, pos):
        """
        """
        self.current_motor_positions["focus"] = pos

    def start_auto_focus(self):
        pass

    def move_omega(self, pos, velocity=None):
        """
        Move omega to absolute position.

        @pos: target position
        """
        # turn it on
        if velocity is not None:
            self.phi_motor_hwobj.set_velocity(velocity)
        self.phi_motor_hwobj.set_value(pos)
        time.sleep(0.2)
        # it should wait here

    def move_omega_relative(self, relpos):
        """
        Move omega to relative position.

        @relpos: target relative position
        """
        #TODO:Are all these waiting times really necessary??'
        self.wait_device_ready()
        self.phi_motor_hwobj.set_value( self.phi_motor_hwobj.get_value() + relpos, timeout = 10 )
        time.sleep(0.2)
        self.wait_device_ready()

    # TODO: define phases as enum members.
    def set_phase(self, phase, timeout=None):
        #TODO: implement timeout. Current API to fulfilll the API.
        """
        General function to set phase by using supervisor commands.
        """
        if phase == "Transfer":
            self.super_hwobj.go_transfer()
        elif phase == "Collect":
            self.super_hwobj.go_collect()
        elif phase == "BeamView":
            self.super_hwobj.go_beam_view()
        elif phase == "Centring":
            self.super_hwobj.go_sample_view()
        else:
            self.logger.warning(
                "Diffractometer set_phase asked for un-handled phase: %s" %
                phase)
    
    # Copied from GenericDiffractometer just to improve error loggin
    def wait_device_ready(self, timeout=30):
        """ Waits when diffractometer status is ready:

        :param timeout: timeout in second
        :type timeout: int
        """
        gevent.sleep(1) # wait a bit to see if state does not change inmediately
        with gevent.Timeout(timeout, Exception("Timeout waiting for Diffracometer ready, check bl13/eh/diff. Is omegax close enough to 0??")):
            while not self.is_ready():
                time.sleep(0.01)


def test_hwo(hwo):
    print(hwo.get_phase_list())
