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

from HardwareRepository.BaseHardwareObjects import Device

__credits__ = ["ALBA"]
__version__ = "2.3."
__category__ = "General"


class ALBASupervisor(Device):

    def __init__(self, *args):
        Device.__init__(self, *args)
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
        self.cmd_go_collect = self.getCommandObject("go_collect")
        self.cmd_go_sample_view = self.getCommandObject("go_sample_view")
        self.cmd_go_transfer = self.getCommandObject("go_transfer")
        self.cmd_go_beam_view = self.getCommandObject("go_beam_view")
        self.chan_state = self.getChannelObject("state")
        self.chan_phase = self.getChannelObject("phase")
        self.chan_detector_cover = self.getChannelObject("detector_cover_open")

        self.chan_state.connectSignal("update", self.state_changed)
        self.chan_phase.connectSignal("update", self.phase_changed)
        self.chan_detector_cover.connectSignal("update", self.detector_cover_changed)

    def isReady(self):
        return True

    def getUserName(self):
        return self.username

    def state_changed(self, value):
        self.current_state = value
        self.emit('stateChanged', self.current_state)

    def phase_changed(self, value):
        if value == 'Sample':
            value = 'Centring'
        self.current_phase = value
        self.emit('phaseChanged', self.current_phase)

    def get_current_phase(self):
        return self.chan_phase.getValue()

    def go_collect(self):
        return self.cmd_go_collect()

    def go_transfer(self):
        return self.cmd_go_transfer()

    def go_sample_view(self):
        return self.cmd_go_sample_view()

    def go_beam_view(self):
        return self.cmd_go_beam_view()

    def get_state(self):
        return self.chan_state.getValue()

    def detector_cover_changed(self, value):
        self.detector_cover_opened = value

    def open_detector_cover(self):
        self.chan_detector_cover.setValue(True)

    def close_detector_cover(self):
        self.chan_detector_cover.setValue(False)

    def is_detector_cover_opened(self):
        return self.chan_detector_cover.getValue()


def test_hwo(hwo):
    print "\nSupervisor control \"%s\"\n" % hwo.getUserName()
    print "   Is Detector Cover open?:", hwo.is_detector_cover_opened()
    print "   Current Phase is:", hwo.get_current_phase()
    print "   Current State is:", hwo.get_state()
