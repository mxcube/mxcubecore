from HardwareRepository import HardwareRepository
import BeamInfo


class ID30BeamInfo(BeamInfo.BeamInfo):
    def __init__(self, *args):
        BeamInfo.BeamInfo.__init__(self, *args)

    def init(self):
        self.chan_beam_size_microns = None
        self.chan_beam_shape_ellipse = None
        BeamInfo.BeamInfo.init(self)

        self.beam_size_slits = map(
            float, self.getProperty("beam_size_slits").split()
        )  # [0.1, 0.05]
        self.camera = self.getDeviceByRole("camera")
        self.beam_position = (self.camera.getWidth() / 2, self.camera.getHeight() / 2)

        self.flux = self.getObjectByRole("flux")

    def get_beam_position(self):
        return self.beam_position

    def set_beam_position(self, beam_x, beam_y):
        return

    def evaluate_beam_info(self, *args):
        BeamInfo.BeamInfo.evaluate_beam_info(self, *args)
        self.beam_info_dict["shape"] = "ellipse"
        return self.beam_info_dict

    def get_flux(self):
        return self.flux.getCurrentFlux()
