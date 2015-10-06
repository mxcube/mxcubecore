import os
import sys
import time
import abc
import logging
from HardwareRepository.TaskUtils import *
"""
set_calibration - set the energy calibration - fname=None, calib_cf=[0,1,0]:
                  filename with the calibration factors or
                  list of calibration factors

get_calibration - get the calibration array.

set_presets - preset parametsrs - **kwargs:
              ctime - real time [s]
              erange - the energy range [keV] - 10:0, 20:1, 40:2, 80:3

clear_spectrum - clear the acquired spectrum

start_acq - start new acquisition - cnt_time=None:
            if specifiefied, cnt_time is the count time [s]

stop_acq - stop the running acquisition

set_roi - configure a ROI - emin, emax, **kwargs:
          emin - energy [keV] or channel number
          emax - energy [keV] or channel number
            channel - output conenctor channel number (1-8)
            element - element name as in periodic table
            atomic_nb - element atomic number

clear_roi - clear ROI settings - **kwargs:
            channel - output conenctor channel number (1-8)

get_roi - get ROI settings, return a dictionarry - **kwargs:
          channel - output conenctor channel number (1-8)

get_times - return a dictionary with the preset and elapsed real time [s],
            elapsed live time (if possible) [s] and the dead time [%]

get_presets - get the preset paramets **kwargs, e.g.:
              ctime - real time
              erange - energy range

read_data - read the data, return an array
            chmin - channel number or energy [keV]
            chmax - channel number or energy [keV]
            calib - True/False
            x - channels or energy (if calib=True)
            y - data

read_raw_data - read the data from chmin to chmax, return a list
            chmin - channel number
            chmax - channel number

read_roi_data - read the data for the configured roi, return a list
"""

class AbstractMCA(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.mca = None
        self.calib_cf = []

    @task
    def read_raw_data(self, chmin, chmax):
        """
        Read the data from chmin to chmax, return a list
        """
        pass

    @task
    def read_roi_data(self):
        """
        Read the data for the configured roi, return a list
        """
        pass

    @abc.abstractmethod
    @task
    def read_data(self, chmin, chmax, calib):
        """
        read the data, return an array
            chmin - channel number or energy [keV]
            chmax - channel number or energy [keV]
            calib - True/False
            x - channels or energy (if calib=True)
            y - data
        """
        pass

    @task
    def set_calibration(self, fname=None, calib_cf=[0,1,0]):
        """
        set the energy calibration - filename with the calibration factors or
        list of calibration factors
        """
        pass

    @abc.abstractmethod
    @task
    def get_calibration(self):
        """
        return a list with energy calibration factors
        """
        pass

    @task
    def set_roi(self, emin, emax, **kwargs):
        """
        configure a ROI:
        emin - energy [keV] or channel number
        emax - energy [keV] or channel number
        kwargs could be:
          channel - output conenctor channel number
          element - element name as in periodic table
          atomic_nb - element atomic number
        """
        pass

    @abc.abstractmethod
    @task
    def get_roi(self, **kwargs):
        """
        get ROI settings, return a dictionarry
        kwargs could be:
          channel - output conenctor channel number
        """
        pass


    @task
    def clear_roi(self, **kwargs):
        """
        clear a configured roi. If kwargs it could be:
          channel - output conenctor channel number
        """
        pass
        
    @task
    def get_times(self):
        """
        return a dictionary with possibly the preset and elapsed real time [s],
            elapsed live time [s], dead time [%]...
        """
        pass

    @task
    def get_presets(self, **kwargs):
        """
        get the preset paramets, where kwargs could be:
              ctime - real time
              erange - energy range ...
        """
        pass

    @task
    def set_presets(self, **kwargs):
        """
        set the preset paramets , where kwargs could be:
              ctime - real time
              erange - energy range ...
        """
        pass

    @abc.abstractmethod
    @task
    def start_acq (self, cnt_time=None):
        """
        Start new acquisition. If specifiefied, cnt_time is the count time [s]
        """
        pass

    @abc.abstractmethod
    @task
    def stop_acq (self):
        """
        stop the running acquisition
        """
        pass

    @task
    def clear_spectrum (self):
        """
        clear the acquired spectrum
        """
        pass



