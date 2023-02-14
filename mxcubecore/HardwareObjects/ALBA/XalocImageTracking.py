"""
[Name] XalocImageTracking

[Description] Hardware object used to control image tracking
By default ADXV is used

Copy from EMBLImageTracking
"""
import os
import time
import logging
import socket
from mxcubecore.BaseHardwareObjects import Device


class XalocImageTracking(Device):

    def __init__(self, *args):
        Device.__init__(self, *args)
        self.logger = logging.getLogger("HWR.XalocImageTracking")

        # self.cmd_start = None
        # self.cmd_stop = None
        self.cmd_send_image = None

        # self.chan_state = None
        # self.chan_status = None
        # self.image_tracking_enabled = None

    def init(self):

        # self.chan_state = self.getChannelObject("State")
        # self.chan_status = self.getChannelObject("Status")
        # self.connect(self.chan_state, "update", self.state_changed)
        #
        # self.cmd_start = self.getCommandObject('start')
        # self.cmd_stop = self.getCommandObject('stop')
        self.cmd_send_image = self.get_command_object('send_image')

    # def enable_image_tracking_changed(self, state):
    #     self.logger.debug('enable_image_tracking_changed: %s' % state)
    #     self.image_tracking_enabled = state
    #     self.emit("imageTrackingEnabledChanged", (self.image_tracking_enabled, ))
    #
    # def state_changed(self, state):
    #     self.logger.debug('state_changed: %s' % state)
    #     if self.state != state:
    #         self.state = state
    #     self.emit("stateChanged", (self.state, ))
    #
    # def is_tracking_enabled(self):
    #     self.logger.debug('is_tracking enabled')
    #     if self.chan_enable_image_tracking is not None:
    #         return self.chan_enable_image_tracking.get_value()
    #
    # def set_image_tracking_state(self, state):
    #     self.logger.debug('set image tracking state: %s' % state)
    #     if self.chan_enable_image_tracking is not None:
    #         self.chan_enable_image_tracking.set_value(state)

    def load_image(self, image_name):
        self.logger.debug('load_image: %s' % image_name)
        self.cmd_send_image(image_name)


# This was a first version, not based on the Tango DS for the ADXV
class XalocImageTrackingLocal(Device):

    def __init__(self, *args):
        Device.__init__(self, *args)
        self.logger = logging.getLogger("HWR.XalocImageTrackingLocal")
        self.binary = None
        self.host = None
        self.port = None
        self.autofront = None
        self.start_adxv_cmd = None

    def init(self):
        self.binary = self.get_property('executable')
        self.host = self.get_property('host')
        self.port = self.get_property('port', '8100')
        self.autofront = self.get_property('autofront', True)

        if self.binary:
            _cmd = '{} -socket {}'.format(self.binary, self.port)
            if self.host:
                self.start_adxv_cmd = 'ssh {} "{}"'.format(self.host, _cmd)
            else:
                self.host = socket.gethostname()
                self.start_adxv_cmd = _cmd

    def load_image(self, image_name):
        self._load_image(str(image_name))

    def _load_image(self, image_file_name):
        """
        Send the image path associated to this spot to the adxv via socket.

        :param image_file_name: image file associated to the spot.
        :return: None
        """
        def send():
            self.logger.debug(
                "Opening socket connection for image: %s" % image_file_name)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.host, self.port))
            self.logger.debug("Sending image {}".format(image_file_name))
            if self.autofront:
                s.send("raise_window Image\n")
            s.send("load_image %s\n" % image_file_name)
        try:
            send()
        except Exception as e:
            os.system(self.start_adxv_cmd)
            time.sleep(2)
            send()
