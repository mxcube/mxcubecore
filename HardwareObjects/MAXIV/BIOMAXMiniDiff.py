"""
BIOMAXMinidiff (MD3)
"""

import math, numpy
import os
import time
import sample_centring
import logging
from functools import partial

from GenericDiffractometer import GenericDiffractometer

class BIOMAXMiniDiff(GenericDiffractometer):

    def __init__(self, *args):
        """
        Description:
        """
        GenericDiffractometer.__init__(self, *args)


    def init(self):

        GenericDiffractometer.init(self)

        # initialization channels and command
        self.state = self.getChannelObject('State')

        #self.start_set_phase = self.getCommandObject('startSetPhase')

        # centring motors
        self.centring_motors_list = ["phiz", "phiy","sampx","sampy"]
        self.centring_phi=sample_centring.CentringMotor(self.motor_hwobj_dict['phi'], direction=-1)
        self.centring_phiz=sample_centring.CentringMotor(self.motor_hwobj_dict['phiz'])
        self.centring_phiy=sample_centring.CentringMotor(self.motor_hwobj_dict['phiy'],direction=-1)
        self.centring_sampx=sample_centring.CentringMotor(self.motor_hwobj_dict['sampx'])
        self.centring_sampy=sample_centring.CentringMotor(self.motor_hwobj_dict['sampy'])

        for motor_name in self.centring_motors_list:
            if self.motor_hwobj_dict[motor_name] is not None:
                self.connect(self.motor_hwobj_dict[motor_name], 'stateChanged', self.motor_state_changed)
                self.connect(self.motor_hwobj_dict[motor_name], "positionChanged", self.centring_motor_moved)
            else:
                logging.getLogger("HWR").warning('%s motor is not defined' % motor_name)

        if self.motor_hwobj_dict["phi"] is not None:
            self.connect(self.motor_hwobj_dict["phi"], 'stateChanged', self.motor_state_changed)
            self.connect(self.motor_hwobj_dict["phi"], "positionChanged", self.emit_diffractometer_moved)
        else:
            logging.getLogger("HWR").error('Phi motor is not defined')

        if self.motor_hwobj_dict["zoom"] is not None:
            self.connect(self.motor_hwobj_dict["zoom"], 'predefinedPositionChanged', self.zoom_motor_predefined_position_changed)
            self.connect(self.motor_hwobj_dict["zoom"], 'stateChanged', self.zoom_motor_state_changed)
        else:
            logging.getLogger("HWR").error('zoom motor is not defined')

        if self.state:
            self.current_state = self.state.getValue()
            self.state.connectSignal("update", self.state_changed)

        # to make it comaptible
        self.camera = self.camera_hwobj



    def start3ClickCentring(self):
        self.start_centring_method(self.CENTRING_METHOD_MANUAL)

    def startAutoCentring(self):
        self.start_centring_method(self.CENTRING_METHOD_AUTO)

    def equipment_ready(self):
        self.emit('minidiffReady', ())

    def equipment_not_ready(self):
        self.emit('minidiffNotReady', ())

    def state_changed(self, state):
        self.current_state = state
        self.emit("minidiffStateChanged", (self.current_state))

    def motor_state_changed(self, state):
        """
        Descript. :
        """
        self.emit('minidiffStateChanged', (state, ))

    def zoom_motor_state_changed(self, state):
        self.emit('zoomMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))

    def centring_motor_moved(self, pos):
        """
        Descript. :
        """
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def invalidate_centring(self):
        if self.current_centring_procedure is None and self.centring_status["valid"]:
            self.centring_status={"valid":False}
            self.emit_progress_message("")
            self.emit('centringInvalid', ())

    def emit_diffractometer_moved(self, *args):
        self.emit("diffractometerMoved", ())

    def zoom_motor_predefined_position_changed(self, position_name, offset):
        """
        Descript. :
        """
        self.update_zoom_calibration()
        self.emit('zoomMotorPredefinedPositionChanged', (position_name, offset, ))
        logging.getLogger('HWR').info("position_name %s and offset is %s" % (position_name, offset))

    def start_manual_centring(self, sample_info=None, wait_result=None):
        """
        """
        self.emit_progress_message("Manual 3 click centring...")
        self.current_centring_procedure = sample_centring.start({"phi": self.centring_phi,
                                                               "phiy": self.centring_phiy,
                                                               "sampx": self.centring_sampx,
                                                               "sampy": self.centring_sampy,
                                                               "phiz": self.centring_phiz },
                                                              self.pixels_per_mm_x, self.pixels_per_mm_y,
                                                              self.beam_position[0], self.beam_position[1])
        self.current_centring_procedure.link(self.centring_done)

    def start_automatic_centring(self, sample_info=None, loop_only=False, wait_result=None):
        """
        """
        self.emit_progress_message("Automatic centring...")
        self.current_centring_procedure = sample_centring.start_auto(self.camera_hwobj,
                                                                     {"phi": self.centring_phi,
                                                                      "phiy": self.centring_phiy,
                                                                      "sampx": self.centring_sampx,
                                                                      "sampy": self.centring_sampy,
                                                                      "phiz": self.centring_phiz },
                                                                     self.pixels_per_mm_x, self.pixels_per_mm_y,
                                                                     self.beam_position[0], self.beam_position[1],
                                                                     msg_cb=self.emit_progress_message,
                                                                     new_point_cb=lambda point: self.emit("newAutomaticCentringPoint", point))
        self.current_centring_procedure.link(self.centring_done)

        if wait_result:
            self.ready_event.wait()
            self.ready_event.clear()

    def motor_positions_to_screen(self, centred_positions_dict):
        self.update_zoom_calibration()
        if None in (self.pixels_per_mm_x, self.pixels_per_mm_y):
            return 0,0
        phi_angle = math.radians(self.centring_phi.direction*self.centring_phi.getPosition())
        sampx = self.centring_sampx.direction * (centred_positions_dict["sampx"]-self.centring_sampx.getPosition())
        sampy = self.centring_sampy.direction * (centred_positions_dict["sampy"]-self.centring_sampy.getPosition())
        phiy = self.centring_phiy.direction * (centred_positions_dict["phiy"]-self.centring_phiy.getPosition())
        phiz = self.centring_phiz.direction * (centred_positions_dict["phiz"]-self.centring_phiz.getPosition())
        rot_matrix = numpy.matrix([math.cos(phi_angle), -math.sin(phi_angle), math.sin(phi_angle), math.cos(phi_angle)])
        rot_matrix.shape = (2, 2)
        inv_rot_matrix = numpy.array(rot_matrix.I)
        dx, dy = numpy.dot(numpy.array([sampx, sampy]), inv_rot_matrix)*self.pixels_per_mm_x

        x = (phiy * self.pixels_per_mm_x) + self.beam_position[0]
        y = dy + (phiz * self.pixels_per_mm_y) + self.beam_position[1]

        return x, y


    def image_clicked(self, x, y, xi, yi):
        sample_centring.user_click(x,y)

    def get_pixels_per_mm(self):
        """
        Get the values from coaxCamScaleX and coaxCamScaleY channels diretly

        :returns: list with two floats
        """
        return (1/self.channel_dict["CoaxCamScaleX"].getValue(), 1/self.channel_dict["CoaxCamScaleY"].getValue())
