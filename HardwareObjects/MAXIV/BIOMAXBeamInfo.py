from HardwareRepository.HardwareObjects import BeamInfo
from HardwareRepository import HardwareRepository
beamline_object = HardwareRepository.get_beamline()


class BIOMAXBeamInfo(BeamInfo.BeamInfo):
    def __init__(self, *args):
        BeamInfo.BeamInfo.__init__(self, *args)

    def init(self):
        self.chan_beam_size_microns = None
        self.chan_beam_shape_ellipse = None
        BeamInfo.BeamInfo.init(self)

        self.chan_beam_pos_x = self.getChannelObject("BeamPositionHorizontal")
        self.chan_beam_pos_y = self.getChannelObject("BeamPositionVertical")
        self.chan_beam_size_x = self.getChannelObject("BeamSizeHorizontal")
        self.chan_beam_size_y = self.getChannelObject("BeamSizeVertical")
        self.chan_beam_shape_ellipse = self.getChannelObject("BeamShapeEllipse")
        self.chan_ImageZoom = self.getChannelObject("ImageZoom")
        self.chan_CoaxialCameraZoomValue = self.getChannelObject(
            "CoaxialCameraZoomValue"
        )

        self.connect(self.chan_beam_pos_x, "update", self.beam_position_changed)
        self.connect(self.chan_beam_pos_y, "update", self.beam_position_changed)
        self.connect(self.chan_ImageZoom, "update", self.beam_position_changed)
        self.connect(self.chan_beam_size_x, "update", self.beam_info_changed)
        self.connect(self.chan_beam_size_y, "update", self.beam_info_changed)
        self.connect(self.chan_beam_shape_ellipse, "update", self.beam_info_changed)
        self.connect(self.chan_CoaxialCameraZoomValue, "update", self.beam_info_changed)

        self.aperture_pos_changed(self.aperture_hwobj.getApertureSize())

    def connectNotify(self, *args):
        self.evaluate_beam_info()
        self.emit_beam_info_change()

    def beam_position_changed(self, value):
        self.get_beam_position()
        self.emit("beamPosChanged", (self.beam_position,))

    def beam_info_changed(self, value):
        self.evaluate_beam_info()
        self.emit("beamInfoChanged", (self.beam_info_dict,))

    def get_beam_position(self):
        """
        Descript. :
        Arguments :
        Return    :
        """

        return self.beam_position
        if self.chan_ImageZoom.getValue() is not None:
            zoom = self.chan_ImageZoom.getValue()
            self.beam_position[0] = self.chan_beam_pos_x.getValue() * zoom
            self.beam_position[1] = self.chan_beam_pos_y.getValue() * zoom
        else:
            self.beam_position[0] = beamline_object.graphics.camera.getWidth() / 2
            self.beam_position[1] = beamline_object.graphics.camera.getHeight() / 2

        return self.beam_position

    def set_beam_position(self, beam_x, beam_y):
        return

    def evaluate_beam_info(self, *args):
        BeamInfo.BeamInfo.evaluate_beam_info(self, *args)
        try:
            if self.chan_beam_shape_ellipse.getValue():
                self.beam_info_dict["shape"] = "ellipse"
            else:
                self.beam_info_dict["shape"] = "rectangle"
        except BaseException:
            self.beam_info_dict["shape"] = "ellipse"
        curpos = self.aperture_hwobj.getCurrentPositionName()
        size_x = size_y = eval(str(curpos)) / 1000.0
        self.beam_info_dict["size_x"] = size_x
        self.beam_info_dict["size_y"] = size_y
        self.beam_info_dict["pos"] = self.beam_position
        return self.beam_info_dict
