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
XalocSupervisor

[Description]
Specific HwObj to interface the Beamline Supervisor TangoDS

[Emitted signals]
- stateChanged
- phaseChanged
"""

from __future__ import print_function

import logging
import time

from mxcubecore.BaseHardwareObjects import Device
from taurus.core.tango.enums import DevState
from mxcubecore.HardwareObjects import GenericDiffractometer

from mxcubecore import HardwareRepository as HWR

__credits__ = ["ALBA"]
__version__ = "3."
__category__ = "General"
__author__ = "Roeland Boer, Jordi Andreu"

class XalocSupervisor(Device):

    def __init__(self, *args):
        Device.__init__(self, *args)
        self.logger = logging.getLogger("HWR.XalocSupervisor")
        self.user_level_log = logging.getLogger("user_level_log")

        self.cmd_go_collect = None
        self.cmd_go_sample_view = None
        self.cmd_go_transfer = None
        self.cmd_go_beam_view = None
        self.chan_state = None
        self.chan_phase = None
        self.chan_detector_cover = None

        self.current_state = None
        self.current_phase = None
        self.detector_cover_opened = None

        self.phase_list = []

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        self.cmd_go_collect = self.get_command_object("go_collect")
        self.cmd_go_sample_view = self.get_command_object("go_sample_view")
        self.cmd_go_transfer = self.get_command_object("go_transfer")
        self.cmd_go_beam_view = self.get_command_object("go_beam_view")
        self.chan_state = self.get_channel_object("state")
        self.chan_phase = self.get_channel_object("phase")
        self.chan_detector_cover = self.get_channel_object("detector_cover_open")
        #self.chan_fast_shutter_collect_position = self.get_channel_object("FastShutCollectPosition")

        try:
            self.phase_list = eval(self.get_property("phase_list"))
        except Exception:
            self.phase_list = [
                GenericDiffractometer.PHASE_TRANSFER,
                GenericDiffractometer.PHASE_CENTRING,
                GenericDiffractometer.PHASE_COLLECTION,
                GenericDiffractometer.PHASE_BEAM,
            ]

        self.chan_state.connect_signal("update", self.state_changed)
        self.chan_phase.connect_signal("update", self.phase_changed)
        self.chan_detector_cover.connect_signal("update", self.detector_cover_changed)

        self.logger.debug("Supervisor state: {0}".format(self.current_state))
        self.logger.debug("Supervisor phase: {0}".format(self.current_phase))

    #def isReady(self):
        #return True

    #def getUserName(self):
        #return self.username

    def state_changed(self, value):
        self.current_state = value
        self.emit('stateChanged', self.current_state)

    def phase_changed(self, value):
        # TODO: Define supervisor states with enum
        if value == 'Sample':
            value = 'Centring'
        self.current_phase = value
        self.emit('phaseChanged', self.current_phase)

    def get_current_phase(self):
        try:
            _value = self.chan_phase.get_value()
            #self.logger.debug('get_current_phase: (value={0}, type={1})'.format(_value, type(_value)))
        except Exception as e:
            raise RuntimeError('Cannot get supervisor current phase:\n%s' % str(e))
        return _value
        # return self.chan_phase.get_value()

    def go_collect(self):
        return self.cmd_go_collect()

    def go_transfer(self):
        return self.cmd_go_transfer()

    def go_sample_view(self):
        return self.cmd_go_sample_view()

    def go_beam_view(self):
        return self.cmd_go_beam_view()


    def get_phase(self):
        return self.current_phase

    def get_phase_list(self):
        """
        Returns list of available phases

        :returns: list with str
        """
        return self.phase_list

    def get_state(self):
        try:
            _value = self.chan_state.get_value()
            #self.logger.debug('get_state: (value={0}, type={1})'.format(_value, type(_value)))
        except Exception as e:
            raise RuntimeError('Cannot get supervisor state:\n%s' % str(e))
        return _value
        #return self.chan_state.get_value()

    def detector_cover_changed(self, value):
        self.detector_cover_opened = value

    def open_detector_cover(self):
        self.chan_detector_cover.set_value(True)

    def close_detector_cover(self):
        self.chan_detector_cover.set_value(False)

    def is_detector_cover_opened(self):
        return self.chan_detector_cover.get_value()
    
    def is_fast_shutter_in_collect_position(self):
        return self.chan_fast_shutter_collect_position.get_value()

    def wait_ready(self, timeout = 30):
        stime = time.time()
        while True:
            if self.current_state == DevState.ON:
                self.logger.debug("Supervisor is in ON state. Returning")
                break
            time.sleep(0.2)
            if timeout is not None:
                if time.time() - stime > timeout:
                    raise Exception("Supervisor timed out waiting for ON state")

    def set_phase(self, phase, timeout=None):
        #TODO: implement timeout. Current API to fulfill the API.
        """
        General function to set phase by using supervisor commands.
        """
        
        self.logger.debug("Current supervisor phase is %s" % self.current_phase)
        if phase.upper() == self.current_phase.upper():
            self.logger.warning("Suprevisor already in phase %s" % phase)
            return
        
        if phase.upper() != "TRANSFER" and HWR.beamline.ln2shower.is_pumping():
            msg = "Cannot change to non transfer phase when the lnshower is pumping, turn off the shower first"
            self.user_level_log.error(msg)
            raise Exception(msg)

        if self.current_state != DevState.ON:
            msg = "Cannot change to phase %s, supervisor is not ready, state is %s" % ( phase, self.current_state )
            self.user_level_log.error(msg)
            raise Exception(msg)

        if phase.upper() == "TRANSFER":
            self.go_transfer()
        elif phase.upper() == "COLLECT":
            self.go_collect()
        elif phase.upper() == "BEAMVIEW":
            self.go_beam_view()
        elif phase.upper() == "CENTRING":
            self.go_sample_view()
        else:
            self.logger.warning(
                "Supervisor set_phase asked for un-handled phase: %s" % phase
            )
            return

        self.logger.debug(
            "Telling supervisor to go to phase %s, with timeout %s" % ( phase, timeout )
        )
    
        if timeout:
            time.sleep(1)
            self.wait_ready( timeout = timeout )
            time.sleep(1)
            self.logger.debug(
                "Supervisor phase is %s" % ( self.get_phase() )
            )

def test_hwo(hwo):
    print("Supervisor control \"%s\"\n" % hwo.getUserName())
    print("Is Detector Cover open?:", hwo.is_detector_cover_opened())
    print("Current Phase is:", hwo.get_current_phase())
    print("Current State is:", hwo.get_state())
