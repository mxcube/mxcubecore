"""
Descript. :
"""
import os
import logging
import time
import gevent
import numpy
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from AbstractXRFSpectrum import AbstractXRFSpectrum
from HardwareRepository.TaskUtils import cleanup
from HardwareRepository.BaseHardwareObjects import HardwareObject


class EMBLXRFSpectrum(AbstractXRFSpectrum, HardwareObject):
    """
    Descript. 
    """
    def __init__(self, name):
        """
        Descript. :
        """
        AbstractXRFSpectrum.__init__(self)
        HardwareObject.__init__(self, name)

        self.can_spectrum = None
        self.ready_event = None
        self.spectrum_running = None
        self.spectrum_info = None

        self.energy_hwobj = None
        self.transmission_hwobj = None
        self.db_connection_hwobj = None
        self.beam_info_hwobj = None

        self.cmd_spectrum_start = None
        self.chan_spectrum_status = None
        self.chan_spectrum_consts = None

        self.config_filename = None

    def init(self):
        """
        Descript. :
        """
        self.ready_event = gevent.event.Event()

        self.energy_hwobj = self.getObjectByRole("energy")

        self.transmission_hwobj = self.getObjectByRole("transmission")
        if self.transmission_hwobj is None:
            logging.getLogger("HWR").warning("EMBLXRFSpectrum: Transmission hwobj not defined")

        self.db_connection_hwobj = self.getObjectByRole("dbserver")
        if self.db_connection_hwobj is None:
            logging.getLogger().warning("EMBLXRFSpectrum: DB hwobj not defined")

        self.beam_info_hwobj = self.getObjectByRole("beam_info")
        if self.beam_info_hwobj is None:
            logging.getLogger("HWR").warning("EMBLXRFSpectrum: Beam info hwobj not defined")

        self.cmd_spectrum_start = self.getCommandObject('cmdSpectrumStart')
        self.cmd_adjust_transmission = self.getCommandObject('cmdAdjustTransmission')
        self.chan_spectrum_status = self.getChannelObject('chanSpectrumStatus')
        if self.chan_spectrum_status is not None:
            self.chan_spectrum_status.connectSignal('update', self.spectrum_status_update)
        self.chan_spectrum_consts = self.getChannelObject('chanSpectrumConsts')

        self.can_spectrum = True
        self.config_filename = self.getProperty("configFile")

    def execute_spectrum_command(self, ct, filename, adjust_transmission=True):
        try:
            print 111, ct, adjust_transmission 
            self.cmd_spectrum_start((ct, adjust_transmission))
        except:
            logging.getLogger().exception('XRFSpectrum: problem in starting spectrum')
            self.emit('xrfSpectrumStatusChanged', ("Error problem in starting spectrum",))
            self.spectrum_command_aborted()

    def spectrum_status_update(self, status):
        """
        Descript. :
        """

        if self.spectrum_running == True:
            if status == 'scaning':
                logging.getLogger("HWR").info('XRF spectrum in progress...')
            elif status == 'ready':
                if self.spectrum_running:
                    self.spectrum_data = list(self.cmd_spectrum_start.get())
                    self.mca_calib = self.chan_spectrum_consts.getValue()[::-1]  
                    self.spectrum_command_finished()
                    logging.getLogger("HWR").info('XRF spectrum finished')
            elif status == 'aborting':
                if self.spectrum_running:
                    self.spectrum_command_aborted()
                    logging.getLogger("HWR").info('XRF spectrum aborted!')
            elif status == 'error':
                self.spectrum_command_failed()
                logging.getLogger("HWR").error('XRF spectrum error!')

    def cancel_spectrum(self, *args):
        """
        Descript. :
        """
        if self.spectrum_running:
            #self.doSpectrum.abort()
            self.ready_event.set()

    def adjust_transmission(self):
        if self.cmd_adjust_transmission is not None:
            self.cmd_adjust_transmission() 
