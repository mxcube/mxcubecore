#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""
EMBLImageTracking
Hardware object used to control image tracking
By default ADXV is used
"""

from mxcubecore.BaseHardwareObjects import Device


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


class EMBLImageTracking(Device):
    """
    EMBLImageTracking
    """

    def __init__(self, *args):
        Device.__init__(self, *args)

        self.state = None
        self.state_dict = {"image_tracking": False, "filter_frames": False}

        self.chan_state = None
        self.chan_enable_image_tracking = None
        self.chan_filter_frames = None
        self.chan_spot_list = None
        self.cmd_load_image = None

    def init(self):

        self.chan_enable_image_tracking = self.get_channel_object(
            "chanImageTrackingEnabled", optional=True
        )
        self.chan_enable_image_tracking.connect_signal(
            "update", self.image_tracking_state_changed
        )
        self.chan_filter_frames = self.get_channel_object(
            "chanFilterFramesEnabled", optional=True
        )
        if self.chan_filter_frames is not None:
            self.chan_filter_frames.connect_signal(
                "update", self.filter_frames_enabled_changed
            )

        self.chan_spot_list = self.get_channel_object(
            "chanSpotListEnabled", optional=True
        )
        if self.chan_spot_list is not None:
            self.chan_spot_list.connect_signal("update", self.spot_list_enabled_changed)

        self.chan_spot_list.set_value(True)
        self.chan_state = self.get_channel_object("chanState")
        self.chan_state.connect_signal("update", self.state_changed)

        self.cmd_load_image = self.get_command_object("cmdLoadImage")

    def image_tracking_state_changed(self, state):
        """
        Updates image tracking state
        :param state:
        :return:
        """
        self.state_dict["image_tracking"] = state
        self.emit("imageTrackingStateChanged", (self.state_dict,))

    def filter_frames_enabled_changed(self, state):
        """
        Updates filter frames state
        :param state:
        :return:
        """
        self.state_dict["filter_frames"] = state
        self.emit("imageTrackingStateChanged", (self.state_dict,))

    def state_changed(self, state):
        """
        Updates overall state
        :param state:
        :return:
        """
        if self.state != state:
            self.state = state
        self.emit("stateChanged", (self.state,))

    def is_tracking_enabled(self):
        """
        Returns True if image tracking is enabled
        :return:
        """
        return self.chan_enable_image_tracking.get_value()

    def set_image_tracking_state(self, state):
        """
        Enables/disables image tracking
        :param state:
        :return:
        """
        self.chan_enable_image_tracking.set_value(state)

    def set_filter_frames_state(self, state):
        """
        Enables/disables image filtering based on the dozor score
        :param state:
        :return:
        """
        self.chan_filter_frames.set_value(state)

    def set_spot_list_enabled(self, state):
        """
        Enables/disables spot indication on Adxv
        :param state:
        :return:
        """
        self.chan_spot_list.set_value(state)

    def spot_list_enabled_changed(self, state):
        self.state_dict["spot_list"] = state
        self.emit("imageTrackingStateChanged", (self.state_dict,))

    def load_image(self, image_name):
        """
        Load image in the image viewer
        :param image_name:
        :return:
        """
        if self.is_tracking_enabled():
            self.set_image_tracking_state(False)
        self.cmd_load_image(str(image_name))

    def re_emit_values(self):
        """
        Reemits values
        :return:
        """
        self.emit("stateChanged", self.state)
        self.emit("imageTrackingStateChanged", (self.state_dict,))
