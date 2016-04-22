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
      
        self.front_light = self.getObjectByRole('frontlight')
        self.back_light = self.getObjectByRole('backlight')
        self.back_light_switch = self.getObjectByRole('frontlightswitch')
        self.front_light_switch = self.getObjectByRole('backlightswitch')

        # to make it comaptible
        self.camera = self.camera_hwobj


    def start3ClickCentring(self):
        self.start_centring_method(self.CENTRING_METHOD_MANUAL)

    def startAutoCentring(self):
        self.start_centring_method(self.CENTRING_METHOD_AUTO)

    def get_pixels_per_mm(self):
        """
        Get the values from coaxCamScaleX and coaxCamScaleY channels diretly

        :returns: list with two floats
        """
        return (1/self.channel_dict["CoaxCamScaleX"].getValue(), 1/self.channel_dict["CoaxCamScaleY"].getValue())
