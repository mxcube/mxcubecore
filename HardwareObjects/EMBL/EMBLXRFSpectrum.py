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
EMBLXRFSpectrum
"""

import logging
import gevent

from AbstractXRFSpectrum import AbstractXRFSpectrum
from HardwareRepository.BaseHardwareObjects import HardwareObject


__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE colaboration"]

__version__ = "2.2."
__maintainer__ = "Ivars Karpics"
__email__ = "ivars.karpics[at]embl-hamburg.de"
__status__ = "Draft"


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
        self.config_filename = None

        self.energy_hwobj = None
        self.transmission_hwobj = None
        self.db_connection_hwobj = None
        self.beam_info_hwobj = None

        self.chan_spectrum_status = None
        self.chan_spectrum_consts = None
        self.cmd_spectrum_start = None
        self.cmd_adjust_transmission = None


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

    def execute_spectrum_command(self, count_sec, filename, adjust_transmission=True):
        try:
            self.cmd_spectrum_start((count_sec, adjust_transmission))
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
