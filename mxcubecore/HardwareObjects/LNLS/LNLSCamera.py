from mxcubecore.BaseHardwareObjects import HardwareObject


class LNLSCamera(HardwareObject):
    """
    A class for LNLS camera. Video streaming is configured
    outside of mxcube.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSCamera.LNLSCamera
    configuration:
        width: 1280
        height: 1024
        scale: 1
    """

    def init(self):
        super().init()
        self.stream_hash = ""
        self._current_stream_size = (0, 0)
        self.width = self.get_property("width", 0)
        self.height = self.get_property("height", 0)
        self.scale = self.get_property("scale", 1)

    def get_width(self) -> int:
        return self.width

    def get_height(self) -> int:
        return self.height

    def get_available_stream_sizes(self):
        return []

    def get_stream_size(self):
        return (self.width, self.height, self.scale)
