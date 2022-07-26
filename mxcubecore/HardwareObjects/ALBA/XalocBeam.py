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
beamSizeChanged
"""

#from __future__ import print_function

import logging
from mxcubecore.HardwareObjects.BeamInfo import BeamInfo
#from mxcubecore.HardwareObjects.abstract import AbstractBeam

__credits__ = ["ALBA Synchrotron"]
__version__ = "3"
__category__ = "General"


class XalocBeam(BeamInfo):

    def __init__(self, *args):
        BeamInfo.__init__(self, *args)
        self.logger = logging.getLogger("HWR.XalocBeamInfo")

        self.chan_beam_width = None
        self.chan_beam_height = None
        self.chan_beam_posx = None
        self.chan_beam_posy = None

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        BeamInfo.init(self)

        self.chan_beam_width = self.get_channel_object("BeamWidth")
        self.chan_beam_height = self.get_channel_object("BeamHeight")
        self.chan_beam_posx = self.get_channel_object("BeamPositionHorizontal")
        self.chan_beam_posy = self.get_channel_object("BeamPositionVertical")

        # Initialize these values BEFORE connecting the signals, they are needed in 
        self.beam_info_dict["size_x"] = self.chan_beam_width.get_value() / 1000.
        self.beam_info_dict["size_y"] = self.chan_beam_height.get_value() / 1000.
        self.logger.debug("self.beam_info_dict[\"size_x\"] %s" % self.beam_info_dict["size_x"] )
        self.logger.debug("self.beam_info_dict[\"size_y\"] %s" % self.beam_info_dict["size_y"] )

        self.chan_beam_height.connect_signal('update', self.beam_height_changed)
        self.chan_beam_width.connect_signal('update', self.beam_width_changed)
        self.chan_beam_posx.connect_signal('update', self.beam_posx_changed)
        self.chan_beam_posy.connect_signal('update', self.beam_posy_changed)

        self.beam_position = self.chan_beam_posx.get_value(),\
                             self.chan_beam_posy.get_value()

    #def connect_notify(self, *args):
        #self.evaluate_beam_info()
        #self.emit_beam_info_changed()

    #def get_beam_divergence_hor(self):
        #return self.default_beam_divergence[0]

    #def get_beam_divergence_ver(self):
        #return self.default_beam_divergence[1]

    def get_beam_position(self):
        self.beam_position = self.chan_beam_posx.get_value(),\
                             self.chan_beam_posy.get_value()
        return self.beam_position

    #def get_slits_gap(self):
        #return None, None

    def set_beam_position(self, beam_x, beam_y):
        self.beam_position = (beam_x, beam_y)

    def get_beam_info(self):
        return self.evaluate_beam_info()

    #def get_beam_size(self):
        #self.evaluate_beam_info()
        #return self.beam_info_dict["size_x"], self.beam_info_dict["size_y"]

    #def get_beam_shape(self):
        #return self.beam_info_dict["shape"]

    def beam_width_changed(self, value):
        self.beam_info_dict['size_x'] = value / 1000.
        self.logger.debug("New beam width %.3f" % value)

        self.evaluate_beam_info()
        self.re_emit_values()

    def beam_height_changed(self, value):
        self.beam_info_dict['size_y'] = value / 1000.
        self.evaluate_beam_info()
        self.re_emit_values()

    def beam_posx_changed(self, value):
        self.beam_position = ( value, self.beam_position[1] )
        self.emit_beam_info_changed()

    def beam_posy_changed(self, value):
        self.beam_position = ( self.beam_position[0], value )
        self.emit_beam_info_changed()

    ##def evaluate_beam_info(self):
        ##self.beam_info_dict["size_x"] = self.chan_beam_width.get_value() / 1000.0
        ##self.beam_info_dict["size_y"] = self.chan_beam_height.get_value() / 1000.0
        ##self.beam_info_dict["shape"] = "rectangular"
        ##return self.beam_info_dict

    #def emit_beam_info_changed(self):
        #self.logger.debug(" emitting beam info")
        #if self.beam_info_dict["size_x"] != 9999 and \
                #self.beam_info_dict["size_y"] != 9999:
            #self.emit("beamSizeChanged", ((self.beam_info_dict["size_x"],
                                           #self.beam_info_dict["size_y"]), ))
            #self.emit("beamInfoChanged", (self.beam_info_dict, ))

    def get_beam_position_on_screen(self):
        """Get the beam position
        Returns:
            (tuple): Position (x, y) [pixel]
        """
        # TODO move this method to AbstractSampleView
        # What is the difference between beam_position and beam_position_on_screen??
        #return self._beam_position_on_screen
        return self.get_beam_position()

    def emit_beam_info_changed(self):
        self.logger.debug(" emitting beam info")
        if self.beam_info_dict["size_x"] != 9999 and \
                self.beam_info_dict["size_y"] != 9999:
            self.emit("beamSizeChanged", ((self.beam_info_dict["size_x"],
                                           self.beam_info_dict["size_y"]), ))
            self.emit("beamInfoChanged", (self.beam_info_dict, ))




def test_hwo(hwo):
    print(hwo.get_beam_info())
    print(hwo.get_beam_position())
