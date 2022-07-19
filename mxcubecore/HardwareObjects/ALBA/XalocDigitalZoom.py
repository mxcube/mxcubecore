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
XalocDigitalZoom

Hardware Object used to integrate the zoom capabilities of the Bzoom system from
ARINAX using the TANGO layer.

Signals:
- stateChanged
- predefinedPositionChanged

"""
from __future__ import print_function
import logging

from enum import IntEnum, unique

from mxcubecore.BaseHardwareObjects import Device
from taurus.core.tango.enums import DevState

__credits__ = ["ALBA Synchrotron"]
__licence__ = "LGPLv3+"
__version__ = "3"
__category__ = "General"


@unique
class DigitalZoomState(IntEnum):
    """
    Defines valid digital zoom states
    """

    UNKNOWN = 0
    READY = 1
    LOW_LIMIT = 2
    HIGH_LIMIT = 3
    DISABLED = 4
    FAULT = -1


class XalocDigitalZoom(Device):
    """Hardware object used to control the zoom capabilities."""

    STATE = DigitalZoomState

    def __init__(self, name):
        """ Define variables """
        Device.__init__(self, name)
        self.logger = logging.getLogger("HWR.XalocDigitalZoom")
        self.user_level_log = logging.getLogger("user_level_log")
        self.chan_state = None
        self.chan_labels = None
        self.chan_blight = None

        self.current_position = 0
        self.current_state = None

    def init(self):
        """ Initialize variables """
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        # TODO: This is not an IOR anymore
        self.chan_pos = self.get_channel_object("position")
        self.chan_state = self.get_channel_object("state")
        # TODO: labels must be harcoded or read as a property
        # self.chan_labels = self.get_channel_object("labels")
        # TODO: This has to be calibrated with zoom values in the [0,1] range
        # self.chan_blight = self.get_channel_object('blight')

        self.chan_pos.connect_signal("update", self.position_changed)
        self.chan_state.connect_signal("update", self.state_changed)

        self.current_position = self.get_value()
        self.logger.debug('Initial Digital Zoom Position: %s',self.get_value())
        self.current_state = self.get_state()
        self.set_name("BZoom")

    def get_predefined_positions_list(self):
        """
        It returns the corresponding to the zoom positions. In our case,
        ['1', '2', ..., 'n']. This values should be gathered from the Arinax server

        :return: [str,]

        """
        return [str(i) for i in range(1, 8)]

    def move_to_position(self, position):
        """
        Move to one of the predefined positions defined in the predefined positions
        list. In this case, position names correspont to zoom values and only a
        casting to int is required.

        :param position: string value indicating the zoom position.
        :return: None

        """
        self.logger.debug("Moving digital zoom to position %s" % position)
        self.chan_pos.set_value(int(position))

    def get_limits(self):
        """
        Get zoom limits (i.e. the position name corresponding to the maximum and
        minimum values).

        Returns: str, str

        """
        _min = self.get_predefined_positions_list()[0]
        _max = self.get_predefined_positions_list()[-1]
        return _min, _max

    def get_state(self):
        """
        Get the Digital Zoom state (enum) mapping from current Tango state.

        Returns: DigitalZoomState

        # TODO: servers returns always UNKNWON
        # TODO: Review type and values returned by Arinax server

        """

        state = self.chan_state.get_value()
        curr_pos = self.get_value()
        if state == DevState.ON:
            return self.STATE.READY
        elif curr_pos == self.get_limits()[0]:
            return self.STATE.LOW_LIMIT
        elif curr_pos == self.get_limits()[-1]:
            return self.STATE.HIGH_LIMIT
        if state == DevState.UNKNOWN:
            # TODO: Bug in Arinax server: always in UNKNOWN
            return self.STATE.READY
            # return self.STATE.UNKNOWN
        else:
            return self.STATE.FAULT

    def get_value(self):
        """
        Get the position index from the server.

        Returns: int

        """
        return self.chan_pos.get_value()

    def get_current_position_name(self):
        """
        Returns the current zoom position name.

        Returns: str

        """
        return str(self.chan_pos.get_value())

    def state_changed(self, state):
        """
        Slot receiving the zoom state changed and emitting the signal

        Args:
            state: Zoom Tango State

        Returns: None

        """
        # TODO: Arrives a Tango State, emits DigitalZoom State
        # We should use the state received!
        state = self.get_state()

        if state != self.current_state:
            self.logger.debug(
                "State changed: {} -> {})".format(self.current_state, state)
            )
            self.current_state = state
            self.emit("stateChanged", (state,))

    def position_changed(self, position):
        """
        Slot receiving the zoom position changed and emitting the signal.
        Additionally, we could also actuate the backlight intensity here.

        Args:
            position: Zoom int position

        Returns: None

        """
        # TODO: Arrives an int, emits string
        # We should use the position received.
        position = self.get_current_position_name()

        if position != self.current_position:
            #self.logger.debug(
                #"Zoom changed: {} -> {}".format(self.current_position, position)
            #)
            self.current_position = position
            self.emit("valueChanged", position)
            self.emit("predefinedPositionChanged", (position, 0))

    def is_ready(self):
        """
        Returns: Boolean

        """
        # state = self.get_state()
        # return state == self.STATE.READY
        # TODO: Bug in Arinax server: state is ALWAYS UNKNOWN
        return True

    def get_calibration(self):
        """
          Returns the pixel size in um for the current zoom level (self.current_position)
        """
        x = None
        _zoom_lut = {}
        _zoom_lut[1] = 0.0000
        _zoom_lut[2] = 0.1810
        _zoom_lut[3] = 0.3620
        _zoom_lut[4] = 0.5430
        _zoom_lut[5] = 0.9088
        _zoom_lut[6] = 0.9540
        _zoom_lut[7] = 1.0000

        #x = 2.0040 + (-1.8370 * _zoom_lut[int(self.current_position)])
        if self.current_position != None:
            x = 2.784 + (-2.604 * _zoom_lut[int(self.current_position)])
        else: 
            self.user_level_log.error("No zoom position available, the bzoom camera DS probably needs to be restarted")
        #TODO improve calibration.
        #self.logger.debug("Getting calibration from zoom hwobj: position (level) {} pix size (um) {}".
                               #format(self.current_position,x) 
                          #)
        return x, x
