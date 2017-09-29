"""
BIOMAXMinidiff (MD2)
"""
import os
import time
import logging
import math

from GenericDiffractometer import *

class BIOMAXMD2(GenericDiffractometer):

    MOTOR_TO_EXPORTER_NAME = {"focus":"AlignmentX", "kappa":"Kappa",
                                  "kappa_phi":"Phi", "phi": "Omega",
                                  "phiy":"AlignmentY", "phiz":"AlignmentZ",
                                  "sampx":"CentringX", "sampy":"CentringY",
                                  "zoom":"Zoom"}

    def __init__(self, *args):
        """
        Description:
        """
        GenericDiffractometer.__init__(self, *args)


    def init(self):

        GenericDiffractometer.init(self)
      
        self.front_light = self.getObjectByRole('frontlight')
        self.back_light = self.getObjectByRole('backlight')
        self.back_light_switch = self.getObjectByRole('backlightswitch')
        self.front_light_switch = self.getObjectByRole('frontlightswitch')

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

    def osc_scan(self, start, end, exptime, wait=False):
        if self.in_plate_mode():
            scan_speed = math.fabs(end-start) / exptime
            # todo, JN, get scan_speed limit
            """
            low_lim, hi_lim = map(float, self.scanLimits(scan_speed))
            if start < low_lim:
                raise ValueError("Scan start below the allowed value %f" % low_lim)
            elif end > hi_lim:
                raise ValueError("Scan end abobe the allowed value %f" % hi_lim)
            """

        scan_params = "1\t%0.3f\t%0.3f\t%0.4f\t1"% (start, (end-start), exptime)
        scan = self.command_dict["startScanEx"]
        self.wait_device_ready(200)
        scan(scan_params)
        print "scan started at ----------->", time.time()
        if wait:
            self.wait_device_ready(300) #timeout of 5 min
            print "finished at ---------->", time.time()

    def set_phase(self, phase, wait=False, timeout=None):
        if self.is_ready():
            print "current state is", self.current_state
            self.command_dict["startSetPhase"](phase)
            if wait:
                if not timeout:
                    timeout = 40
                self.wait_device_ready(timeout)
        else:
            print "moveToPhase - Ready is: ", self.is_ready()


    def move_sync_motors(self, motors_dict, wait=False, timeout=None):
        argin = ""
        #print "start moving motors =============", time.time()
        for motor in motors_dict.keys():
            position = motors_dict[motor]
            if position is None:
                continue
            name=self.MOTOR_TO_EXPORTER_NAME[motor]
            argin += "%s=%0.3f;" % (name, position)
        if not argin:
            return
        self.wait_device_ready(100)
        self.command_dict["startSimultaneousMoveMotors"](argin)

        if wait:
            while not self.is_ready():
                time.sleep(0.5)

    def is_ready(self):
        """
        Detects if device is ready
        """
        return self.channel_dict["State"].getValue() == DiffractometerState.tostring(\
                    DiffractometerState.Ready)

    def moveToBeam(self, x, y):
        try:
            self.beam_position = self.beam_info_hwobj.get_beam_position()
            beam_xc = self.beam_position[0]
            beam_yc = self.beam_position[1]
            self.centring_phiz.moveRelative((y-beam_yc)/float(self.pixelsPerMmZ))
            self.centring_phiy.moveRelative(-1*(x-beam_xc)/float(self.pixelsPerMmY))
        except:
            logging.getLogger("HWR").exception("MiniDiff: could not center to beam, aborting")

