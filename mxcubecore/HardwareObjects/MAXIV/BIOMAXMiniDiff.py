"""
BIOMAXMinidiff (MD3)
"""
import os
import time
import logging

from GenericDiffractometer import GenericDiffractometer

class BIOMAXMiniDiff(GenericDiffractometer):

    def __init__(self, *args):
        """
        Description:
        """
        GenericDiffractometer.__init__(self, *args)


    def init(self):

        GenericDiffractometer.init(self)

        if self.motor_hwobj_dict["zoom"] is not None:
            self.connect(self.motor_hwobj_dict["zoom"], 'predefinedPositionChanged', self.zoom_motor_predefined_position_changed)
            self.connect(self.motor_hwobj_dict["zoom"], 'stateChanged', self.zoom_motor_state_changed)
        else:
            logging.getLogger("HWR").error('zoom motor is not defined')


        # to make it comaptible
        self.camera = self.camera_hwobj



    def start3ClickCentring(self):
        self.start_centring_method(self.CENTRING_METHOD_MANUAL)

    def startAutoCentring(self):
        self.start_centring_method(self.CENTRING_METHOD_AUTO)

    def zoom_motor_state_changed(self, state):
        self.emit('zoomMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))


    def zoom_motor_predefined_position_changed(self, position_name, offset):
        """
        Descript. :
        """
        self.update_zoom_calibration()
        self.emit('zoomMotorPredefinedPositionChanged', (position_name, offset, ))
        logging.getLogger('HWR').info("position_name %s and offset is %s" % (position_name, offset))


    def get_pixels_per_mm(self):
        """
        Get the values from coaxCamScaleX and coaxCamScaleY channels diretly

        :returns: list with two floats
        """
        return (1/self.channel_dict["CoaxCamScaleX"].getValue(), 1/self.channel_dict["CoaxCamScaleY"].getValue())
