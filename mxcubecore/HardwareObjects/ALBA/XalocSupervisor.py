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

from mxcubecore.BaseHardwareObjects import Device

__credits__ = ["ALBA"]
__version__ = "3."
__category__ = "General"


class XalocSupervisor(Device):

    def __init__(self, *args):
        Device.__init__(self, *args)
        self.logger = logging.getLogger("HWR.XalocSupervisor")
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

        self.chan_state.connect_signal("update", self.state_changed)
        self.chan_phase.connect_signal("update", self.phase_changed)
        self.chan_detector_cover.connect_signal("update", self.detector_cover_changed)


        self.current_state = self.get_state()
        self.current_phase = self.get_current_phase()
        self.logger.debug("Supervisor state: {0}".format(self.current_state))
        self.logger.debug("Supervisor phase: {0}".format(self.current_phase))

    def isReady(self):
        return True

    def getUserName(self):
        return self.username

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


def test_hwo(hwo):
    print("Supervisor control \"%s\"\n" % hwo.getUserName())
    print("Is Detector Cover open?:", hwo.is_detector_cover_opened())
    print("Current Phase is:", hwo.get_current_phase())
    print("Current State is:", hwo.get_state())
