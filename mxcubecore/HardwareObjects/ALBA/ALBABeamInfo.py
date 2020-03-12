# encoding: utf-8
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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

__copyright__ = """MXCuBE collaboration"""
__license__ = "LGPLv3+"


import logging

from HardwareRepository.HardwareObjects.abstract.AbstractBeam import BeamShape, AbstractBeam


class ALBABeamInfo((AbstractBeam):

    def __init__(self, name):
        AbstractBeam.__init__(self, name)

    def init(self):
        self.beam_width_chan = self.getChannelObject("BeamWidth")
        self.beam_height_chan = self.getChannelObject("BeamHeight")
        self.beam_posx_chan = self.getChannelObject("BeamPositionHorizontal")
        self.beam_posy_chan = self.getChannelObject("BeamPositionVertical")

        self.beam_height_chan.connectSignal("update", self.beam_height_changed)
        self.beam_width_chan.connectSignal("update", self.beam_width_changed)
        self.beam_posx_chan.connectSignal("update", self.beam_posx_changed)
        self.beam_posy_chan.connectSignal("update", self.beam_posy_changed)

        # divergence can be added as fixed properties in xml
        default_beam_divergence_vertical = None
        default_beam_divergence_horizontal = None

        try:
            default_beam_divergence_vertical = int(
                self.getProperty("beam_divergence_vertical")
            )
            default_beam_divergence_horizontal = int(
                self.getProperty("beam_divergence_horizontal")
            )
        except BaseException:
            pass

        self._beam_divergence = [
            default_beam_divergence_horizontal,
            default_beam_divergence_vertical,
        ]

    def connectNotify(self, *args):
        self.evaluate_beam_info()
        self.emit_beam_info_change()

    def get_beam_position_on_screen(self):
        """
        Descript. :
        Arguments :
        Return    :
        """
        self._beam_position_on_screen = [
            self.beam_posx_chan.getValue(),
            self.beam_posy_chan.getValue(),
        [
        return self._beam_position_on_screen

    def get_slits_gap(self):
        return None, None

    def set_beam_position_on_screen(self, beam_x, beam_y):
        """
        Descript. :
        Arguments :
        Return    :
        """
        self._beam_position_on_screen = (beam_x, beam_y)

    def get_beam_size(self):
        """
        Descript. : returns beam size in millimeters
        Return   : list with two integers
        """
        self.evaluate_beam_info()
        return self._beam_width, self._beam_height

    def beam_width_changed(self, value):
        self._beam_width = value
        self.emit_beam_info_changed()

    def beam_height_changed(self, value):
        self._beam_height = value
        self.emit_beam_info_changed()

    def beam_posx_changed(self, value):
        self._beam_position_on_screen[0] = value
        self.emit_beam_info_changed()

    def beam_posy_changed(self, value):
        self._beam_position_on_screen[1] = value
        self.emit_beam_info_changed()

    def evaluate_beam_info(self):
        """
        Descript. : called if aperture, slits or focusing has been changed
        Return    : dictionary,{size_x:0.1, size_y:0.1, shape:"rectangular"}
        """

        self._beam_width = self.beam_width_chan.getValue() / 1000.0
        self._beam_height = self.beam_height_chan.getValue() / 1000.0
        self._beam_shape = BeamShape.RECTANGULAR

        self._beam_info_dict["size_x"] = self._beam_width
        self._beam_info_dict["size_y"] = self._beam_height
        self._beam_info_dict["shape"] = self._beam_shape

        return self._beam_info_dict.copy()

    def emit_beam_info_change(self):
        """
        Descript. :
        Arguments :
        Return    :
        """
        logging.getLogger("HWR").debug(" emitting beam info")
        if (
            self._beam_info_dict["size_x"] != 9999
            and self._beam_info_dict["size_y"] != 9999
        ):
            self.emit(
                "beamSizeChanged",
                (self._beam_width, self._beam_height)
            )
            self.emit("beamInfoChanged", (self._beam_info_dict,))


def test_hwo(hwo):
    print(hwo.get_beam_info())
    print(hwo.get_beam_position())
