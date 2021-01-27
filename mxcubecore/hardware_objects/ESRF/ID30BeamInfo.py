from mxcubecore.hardware_objects import BeamInfo
from mxcubecore import HardwareRepository as HWR


class ID30BeamInfo(BeamInfo.BeamInfo):
    def __init__(self, *args):
        BeamInfo.BeamInfo.__init__(self, *args)

    def init(self):
        self.chan_beam_size_microns = None
        self.chan_beam_shape_ellipse = None
        BeamInfo.BeamInfo.init(self)

        self.beam_size_slits = tuple(
            map(float, self.get_property("beam_size_slits").split())
        )  # [0.1, 0.05]
        self.beam_position = (
            HWR.beamline.sample_view.camera.get_width() / 2,
            HWR.beamline.sample_view.camera.get_height() / 2,
        )

    def get_beam_position(self):
        return self.beam_position

    def set_beam_position(self, beam_x, beam_y):
        return

    def evaluate_beam_info(self, *args):
        BeamInfo.BeamInfo.evaluate_beam_info(self, *args)
        self.beam_info_dict["shape"] = "ellipse"
        return self.beam_info_dict
