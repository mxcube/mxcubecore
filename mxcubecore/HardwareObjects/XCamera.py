"""Class for X-rays cameras connected to framegrabbers run by Taco Device Servers

template:
  <device class = "XCamera">
    <username>user label</username>
    <taconame>device server name (//host/.../.../...)</taconame>
    <interval>polling interval (in ms.)</interval>
  </device>
"""
from HardwareRepository.HardwareObjects import TacoDevice


class XCamera(TacoDevice.TacoDevice):
    def init(self):
        if self.device.imported:
            # device is already in tcp mode (done in _init)
            self.device.DevCcdLive(0)  # stop acquisition
            self.device.DevCcdLive(1)  # start acquisition
            self.setPollCommand("DevCcdReadJpeg", 75)

            # add command for receiving statistics from Device Server
            cmdObject = self.add_command(
                {"type": "taco", "name": "statisticsCmd", "taconame": self.tacoName()},
                "DevReadSigValues",
            )
            cmdObject.poll(
                self.interval,
                (),
                valueChangedCallback=self.statisticsChanged,
                timeoutCallback=self.statisticsTimeout,
            )

    def valueChanged(self, deviceName, value):
        self.emit("imageReceived", (value,))

    def getWidth(self):
        if self.isReady():
            return self.device.DevCcdXSize()

    def getHeight(self):
        if self.isReady():
            return self.device.DevCcdYSize()

    def setSize(self, width, height):
        if self.isReady():
            return self.device.DevCcdOutputSize(width, height)

    def statisticsChanged(self, stats):
        self.emit("imageDataChanged", self.getImageData(read=False))

    def statisticsTimeout(self):
        pass

    def getImageData(self, read=True):
        if read:
            stats = self.device.DevReadSigValues()

        exposure_time = stats[0]
        threshold = stats[1]
        calib_intensity = stats[2]
        width = stats[3]
        height = stats[4]
        roi_x1 = stats[5]
        roi_y1 = stats[6]
        roi_x2 = stats[7]
        roi_y2 = stats[8]
        live_mode = stats[9]
        nb_spots = stats[10]
        intensity = stats[11]
        xbeam_center = stats[12]
        ybeam_center = stats[13]

        return (
            exposure_time,
            width,
            height,
            (roi_x1, roi_y1, roi_x2, roi_y2),
            live_mode,
            intensity,
            xbeam_center,
            ybeam_center,
        )
