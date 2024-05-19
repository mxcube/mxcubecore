"""
[Name] BeamInfo

[Description]
BeamInfo hardware object informs mxCuBE (HutchMenuBrick) about the beam position
and size.

This is the Soleil PX1 version

Beam size is hardcoded in this file.
Beam Position is updated whenever the zoom motor changes position. Values taken from
   zoom xml configuration

[Emited signals]

beamInfoChanged
beamPosChanged

"""

import logging

from mxcubecore.BaseHardwareObjects import HardwareObject


class PX1BeamInfo(HardwareObject):
    def __init__(self, *args):
        super().__init__(*args)

        self.beam_position = [None, None]
        self.beam_size = [100, 100]
        self.shape = "rectangular"

        self.beam_size_slits = [9999, 9999]

        self.beam_info_dict = {}
        self.beam_info_dict["size_x"] = self.beam_size[0]
        self.beam_info_dict["size_y"] = self.beam_size[1]
        self.beam_info_dict["shape"] = self.shape

        # Zoom motor
        self.zoomMotor = None

    def init(self):
        try:
            self.beamx_chan = self.get_channel_object("beamsizex")
        except KeyError:
            logging.getLogger().warning(
                "%s: cannot connect to beamsize x channel ", self.id
            )

        try:
            self.beamy_chan = self.get_channel_object("beamsizey")
            self.beamy_chan.connect_signal("update", self.beamsize_x_changed)
        except KeyError:
            logging.getLogger().warning(
                "%s: cannot connect to beamsize y channel ", self.id
            )

        self.zoomMotor = self.get_deviceby_role("zoom")

        if self.beamx_chan is not None:
            self.beamx_chan.connect_signal("update", self.beamsize_x_changed)
        else:
            logging.getLogger().info("BeamSize X channel not defined")

        if self.beamy_chan is not None:
            self.beamy_chan.connect_signal("update", self.beamsize_y_changed)
        else:
            logging.getLogger().info("BeamSize Y channel not defined")

        if self.zoomMotor is not None:
            self.connect(
                self.zoomMotor, "predefinedPositionChanged", self.zoomPositionChanged
            )
            self.zoomPositionChanged()
        else:
            logging.getLogger().info("Zoom motor not defined")

        if None in [self.beamy_chan, self.beamx_chan]:
            try:
                beam_size = self.get_property("beam_size")
                if beam_size is not None:
                    beamx, beamy = beam_size.split(",")
                    self.beam_info_dict["size_x"] = self.beam_size[0] = float(beamx)
                    self.beam_info_dict["size_y"] = self.beam_size[1] = float(beamy)
            except Exception:
                pass

    def connect_notify(self, signal):
        if signal == "beamInfoChanged":
            self.sizeUpdated()
        elif signal == "position_changed":
            self.positionUpdated()

    def zoomPositionChanged(self, name=None, offset=None):
        zoom_props = self.zoomMotor.getCurrentPositionProperties()
        if "beamPositionX" in zoom_props:
            self.beam_position = [
                zoom_props["beamPositionX"],
                zoom_props["beamPositionY"],
            ]
            self.positionUpdated()

    def positionUpdated(self):
        self.emit("beamPosChanged", (self.beam_position,))
        self.sizeUpdated()

    def sizeUpdated(self):
        if None not in [self.beamx_chan, self.beamy_chan]:
            x_beam = self.beamx_chan.get_value()
            y_beam = self.beamy_chan.get_value()
            self.beam_info_dict["size_x"] = x_beam
            self.beam_info_dict["size_y"] = y_beam
        self.emit("beamInfoChanged", (self.beam_info_dict,))

    def get_beam_info(self):
        return self.beam_info_dict

    def get_beam_position(self):
        return self.beam_position

    def get_beam_size(self):
        return self.beam_size

    def get_beam_shape(self):
        return self.shape

    def get_slits_gap(self):
        return self.beam_size_slits

    def get_beam_divergence_hor(self):
        return 0

    def get_beam_divergence_ver(self):
        return 0

    def beamsize_x_changed(self, value=None):
        self.sizeUpdated()

    def beamsize_y_changed(self, value=None):
        self.sizeUpdated()


def test_hwo(hwo):
    print("BEAM info: ", hwo.get_beam_info())
    print("BEAM position: ", hwo.get_beam_position())
