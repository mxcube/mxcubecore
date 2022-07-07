# -*- coding: utf-8 -*-
"""
Vortex (Hitachi) Fluorescence Detector control hardware object.

Could use Tango or Epics channels
"""
import time
import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractMCA import AbstractMCA

import logging

__author__ = "Bernard Lavault and Daniel Homs - ARINAX"
__credits__ = ["The MxCuBE collaboration"]

__email__ = ""
__status__ = "Beta"


class VortexFluoDetector(AbstractMCA, HardwareObject):

        # "CONNECT": "CONNECT",
        # "CONNECTED": "CONNECTED",
        # "ACQUIRE": "Acquire",
        # "ERASE": "ERASE",
        # "UPDATE": "UPDATE",
        # "NUM_IMAGE": "NumImages",  # current value of number of frame to acquire
        # "NUM_IMAGE_RBV": "NumImages_RBV",  # RBV is the last set value
        # "NUM_CHANNELS": "NUM_CHANNELS",  # number of channels of system
        # "CTRL_MCA_ROI": "CTRL_MCA_ROI",  # enable ROI calculations
        # "CTRL_MCA_ROI_RBV": "CTRL_MCA_ROI_RBV",
        # "CTRL_DTC": "CTRL_DTC",
        # "ARRAY_DATA": "ArrayData",
        # "SUM_ARRAY_DATA": "SumArrayData",
        # "LOWER_LIMIT_ROI": "C1_MCA_ROI1_LLM",  # lower limit for the first ROI
        # "UPPER_LIMIT_ROI": "C1_MCA_ROI1_HLM",  # upper limit for the first ROI
        # "STATE": "DetectorState_RBV",
        # "STATUS": "StatusMessage_RBV",
        # "ROI_MIN_ENERGY": "ROIDATA_MinX",  # ROI minimum energy bin, 0 based
        # "ROI_MIN_ENERGY_RBV": "ROIDATA_MinX_RBV",  # ROI minimum energy bin with readback value
        # "ROI_SIZE_ENERGY": "ROIDATA_Size_X",  # size of energy ROI
        # "ROI_SIZE_ENERGY_RBV": "ROIDATA_Size_X_RBV",  # size of energy ROI with readback value
        # "ROI_MIN_CHANNEL": "ROIDATA_MinY",  # ROI minimum channel number, 0 based
        # "ROI_MIN_CHANNEL_RBV": "ROIDATA_MinY_RBV",  # ROI minimum channel number with readback value
        # "ROI_SIZE_CHANNEL": "ROIDATA_SizeY",  # ROI number of channels, 0 based
        # "ROI_SIZE_CHANNEL_RBV": "ROIDATA_SizeY_RBV",  # ROI number of channels with readback value
        # "ROI_SUM_VALUE": "ROI_Sum_Value",  # integrated ROI readback value
        # "ROI_SUM_ARRAY_DATA": "ROI_Sum_ArrayData",  # the ROI for every frame from an acqusition

    def __init__(self, name):
        AbstractMCA.__init__(self)
        HardwareObject.__init__(self, name)
        self.state = "UNKNOWN"
        self.pv_base = "XSPRESS3-EXAMPLE"
        # self.chan_obj_dict = {}

    def init(self):
        self.state = "READY"
        self.pv_base = self.get_property("pv_base")
        self.adc_clock = 80000000 # Hz  per point


    def connect_device(self):
        # TODO SET CONNECT PARAMS
        self.get_channel_object("CONNECT").set_value(1)
        return self.is_connected()

    def is_connected(self):
        return self.get_channel_object("CONNECTED").get_value()

    # def read

    def get_roi_count(self):
        return self.get_channel_object("ROI_Sum_Value").get_value()

    #
    # def start(self):
    #     # XSPRESS3-EXAMPLE:Acquire
    #     pass

    def wait_ready(self, timeout=None):
        self.state = "READY"
        start_time = time.time()
        stop_time = start_time + timeout

        while (time.time() < stop_time):
            gevent.sleep(0.25)
            if self.is_ready():
                return

        raise Exception("Timeout waiting Fluo Detector to be ready")

    """ AbstractMCA Methods Override """

    def read_raw_data(self, chmin, chmax):
        """Read the raw data from min energy bins to max energy bins

        Keyword Args:
            chmin (int): energy channel, defaults to 0
            chmax (int): energy channel, defaults to 4095

        Returns:
            list. Raw data.
        """
        return self.get_channel_object("SumArrayData").get_value()[chmin:chmax]

    def read_roi_data(self):
        """Read the data for the predefined ROI

        Returns:
            list. Raw data for the predefined ROI channels.
        """

        return self.get_channel_object("ROI_Sum_ArrayData").get_value()

    def read_data(self, chmin, chmax, calib):
        """Read the data

        Keyword Args:
            chmin (float): energy channel number or energy [keV]
            chmax (float): energy channel number or energy [keV]
            calib (bool): use calibration, defaults to False

        Returns:
            numpy.array. x - channels or energy (if calib=True), y - data.
        """
        pass

    def set_calibration(self, fname=None, calib_cf=[0, 1, 0]):
        """Set the energy calibration. Give a filename or a list of calibration factors.

        Kwargs:
            fname (str): optional filename with the calibration factors
            calib_cf (list): optional list of calibration factors

        Returns:
            list. Calibration factors.

        Raises:
            IOError, ValueError
        """
        pass

    def get_calibration(self):
        """Get the calibration factors list

        Returns:
            list. Calibration factors.
        """
        pass

    def set_roi(self, emin, emax, **kwargs):
        """Configure a ROI

        Args:
            emin (float): energy [keV] or channel number
            emax (float): energy [keV] or channel number

        Keyword Args:
            element (str): element name as in periodic table
            atomic_nb (int): element atomic number
            channel (int): output connector channel number (1-8)

        Returns:
            None

        Raises:
            KeyError
        """

        if isinstance(emin, float):
            # TODO conversion to channel value
            pass
        if isinstance(emax, int):
            # TODO conversion to channel value
            pass

        idx_range = emax - emin
        self.get_channel_object("ROIDATA_MinY").set_value(emin)
        self.get_channel_object("ROIDATA_SizeY").set_value(idx_range + 1)

    def get_roi(self, **kwargs):
        """Get ROI settings

        Keyword Args:
            channel (int): output connector channel number (1-8)

        Returns:
            dict. ROI dictionary.
        """
        ROI_dict = {}
        ROI_dict["ROI_MIN_CHANNEL"] = self.get_channel_object("ROIDATA_MinY").get_value()
        ROI_dict["ROI_SIZE_CHANNEL"] = self.get_channel_object("ROIDATA_SizeY").get_value()
        return ROI_dict

    def clear_roi(self, **kwargs):
        """Clear ROI settings

         Keyword Args:
            channel (int): optional output connector channel number (1-8)

         Returns:
            None
        """
        self.set_roi(0, 4095)

    def get_times(self):
        """Return a dictionary with the preset and elapsed real time [s],
        elapsed live time (if possible) [s] and the dead time [%].

        Returns:
            dict. Times dictionary.

        Raises:
            RuntimeError
        """
        pass

    def get_presets(self, **kwargs):
        """Get the preset parameters

        Keyword Args:
            ctime (float): Real time
            erange (int): energy range
            fname (str): filename where the data are stored
            ...

        Returns:
            dict.

        Raises:
            RuntimeError
        """
        pass

    # def set_preset(self, integration_time):
    #     pass

    def set_presets(self, **kwargs):
        """Set presets parameters

        Keyword Args:
           ctime (float): real time [s]
           erange (int): the energy range
           fname (str): file name (full path) to save the raw data

        Returns:
           None
        """
        count_time = kwargs["ctime"] or 1
        erange = kwargs["erange"] or 1
        fname = kwargs["fname"] or None

        if not self.is_connected():
            self.connect_device()

        # TODO Verify sending channel numbers is correct
        # set NUM_FRAMES_CONFIG ?
        # self.chan_obj_dict["ROI_SIZE_ENERGY"].set_value(kwargs["erange"])

    def start_acq(self, cnt_time=None):
        """Start new acquisition. If cnt_time is not specified, counts for preset real time.

        Keyword Args:
            cnt_time (float, optional): count time [s]; 0 means to count indefinitely.

        Returns:
            None
        """
        if cnt_time is not None:
            frame_duration = self.get_roi()["ROI_SIZE_CHANNEL"] * self.adc_clock  # TODO check if this is correct
            num_frames = round(cnt_time / self.frame_duration)  # number of frames of 1 cycle (when Value_RBV=1 ?)
            # TODO check if use of C1_SCA0:Value_RBV is necessary
            self.get_channel_object("NumImages_RBV").set_value(num_frames)

        self.state = "RUNNING"
        self.get_channel_object("Acquire").set_value(1)

    def stop_acq(self):
        """Stop the running acquisition"""
        self.get_channel_object("Acquire").set_value(0)

    def clear_spectrum(self):
        """Clear the acquired spectrum"""
        self.get_channel_object("ERASE").get_value()

    """ HardwareObject Methods Override """

    def is_ready(self):
        return self.get_state().lower() == "Idle".lower()

    def get_state(self):
        """ Getter for state attribute

        Implementations must query the hardware directly, to ensure current results

        Returns:
            string Idle or Acquire
        """
        return self.get_channel_object("DetectorState_RBV").get_value()
