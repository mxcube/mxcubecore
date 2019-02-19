#
#  Project: MXCuBE
#  https://github.com/mxcube.
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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
[Name] BeamInfo

[Description]
BeamInfo hardware object is used to define final beam size and shape.
It can include aperture, slits and/or other beam definer (lenses or other eq.)

[Signals]
beamInfoChanged
beamPosChanged
"""

import logging
from HardwareRepository.BaseHardwareObjects import Equipment

__credits__ = ["ALBA Synchrotron"]
__version__ = "2.3"
__category__ = "General"


class ALBABeamInfo(Equipment):

    def __init__(self, *args):
        Equipment.__init__(self, *args)

        self.aperture_hwobj = None
        self.slits_hwobj = None
        self.beam_definer_hwobj = None

        self.chan_beam_width = None
        self.chan_beam_height = None
        self.chan_beam_posx = None
        self.chan_beam_posy = None

        self.beam_size_slits = None
        self.beam_size_aperture = None
        self.beam_size_definer = None
        self.beam_position = None
        self.beam_info_dict = None
        self.default_beam_divergence = None

    def init(self):
        self.beam_size_slits = [9999, 9999]
        self.beam_size_aperture = [9999, 9999]
        self.beam_size_definer = [9999, 9999]

        self.beam_position = [0, 0]
        self.beam_info_dict = {}

        self.chan_beam_width = self.getChannelObject("BeamWidth")
        self.chan_beam_height = self.getChannelObject("BeamHeight")
        self.chan_beam_posx = self.getChannelObject("BeamPositionHorizontal")
        self.chan_beam_posy = self.getChannelObject("BeamPositionVertical")

        self.chan_beam_height.connectSignal('update', self.beam_height_changed)
        self.chan_beam_width.connectSignal('update', self.beam_width_changed)
        self.chan_beam_posx.connectSignal('update', self.beam_posx_changed)
        self.chan_beam_posy.connectSignal('update', self.beam_posy_changed)

        # divergence can be added as fixed properties in xml
        default_beam_divergence_vertical = None
        default_beam_divergence_horizontal = None

        try:
            default_beam_divergence_vertical = int(
                self.getProperty("beam_divergence_vertical"))
            default_beam_divergence_horizontal = int(
                self.getProperty("beam_divergence_horizontal"))
        except Exception as e:
            pass

        self.default_beam_divergence = [
            default_beam_divergence_horizontal,
            default_beam_divergence_vertical]

    def connectNotify(self, *args):
        self.evaluate_beam_info()
        self.emit_beam_info_change()

    def get_beam_divergence_hor(self):
        return self.default_beam_divergence[0]

    def get_beam_divergence_ver(self):
        return self.default_beam_divergence[1]

    def get_beam_position(self):
        self.beam_position = self.chan_beam_posx.getValue(), self.chan_beam_posy.getValue()
        return self.beam_position

    def get_slits_gap(self):
        return None, None

    def set_beam_position(self, beam_x, beam_y):
        self.beam_position = (beam_x, beam_y)

    def get_beam_info(self):
        return self.evaluate_beam_info()

    def get_beam_size(self):
        self.evaluate_beam_info()
        return self.beam_info_dict["size_x"], self.beam_info_dict["size_y"]

    def get_beam_shape(self):
        return self.beam_info_dict["shape"]

    def beam_width_changed(self, value):
        self.beam_info_dict['size_x'] = value
        self.emit_beam_info_changed()

    def beam_height_changed(self, value):
        self.beam_info_dict['size_y'] = value
        self.emit_beam_info_changed()

    def beam_posx_changed(self, value):
        self.beam_position['x'] = value
        self.emit_beam_info_changed()

    def beam_posy_changed(self, value):
        self.beam_position['y'] = value
        self.emit_beam_info_changed()

    def evaluate_beam_info(self):
        self.beam_info_dict["size_x"] = self.chan_beam_width.getValue() / 1000.0
        self.beam_info_dict["size_y"] = self.chan_beam_height.getValue() / 1000.0
        self.beam_info_dict["shape"] = "rectangular"
        return self.beam_info_dict

    def emit_beam_info_change(self):
        logging.getLogger("HWR").debug(" emitting beam info")
        if self.beam_info_dict["size_x"] != 9999 and \
                self.beam_info_dict["size_y"] != 9999:
            self.emit("beamSizeChanged", ((self.beam_info_dict["size_x"],
                                           self.beam_info_dict["size_y"]), ))
            self.emit("beamInfoChanged", (self.beam_info_dict, ))


def test_hwo(hwo):
    print hwo.get_beam_info()
    print hwo.get_beam_position()
