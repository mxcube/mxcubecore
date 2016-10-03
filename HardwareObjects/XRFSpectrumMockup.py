import logging
import gevent
import time
import numpy

from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.TaskUtils import cleanup

class XRFSpectrumMockup(HardwareObject):
    def init(self):
        self.ready_event = gevent.event.Event()

        self.spectrumInfo = {}
        self.spectrumInfo['startTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.spectrumInfo['endTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.spectrumInfo["energy"] = 0
        self.spectrumInfo["beamSizeHorizontal"] = 0
        self.spectrumInfo["beamSizeVertical"] = 0
        self.ready_event = gevent.event.Event()

    def isConnected(self):
        return True

    def canSpectrum(self):
        return True

    def startXrfSpectrum(self, ct, directory, archive_directory, prefix,
           session_id=None, blsample_id=None, adjust_transmission=False):

        self.scanning = True
        self.emit('xrfSpectrumStarted', ())

        with cleanup(self.ready_event.set):
            self.spectrumInfo["sessionId"] = session_id
            self.spectrumInfo["blSampleId"] = blsample_id
      
            mcaData = []
            calibrated_data = []  
            values = [0, 20, 340, 70, 100, 110, 120, 200, 200, 210, 1600,
                      210, 200, 200, 200, 250, 300, 200, 100, 0, 0 ,0, 90]
            for n, value in enumerate(values):
                mcaData.append((n, value))

            mcaCalib = [10,1, 21, 0]
            mcaConfig = {}
            mcaConfig["legend"] = "XRF test scan from XRF mockup"
            mcaConfig['htmldir'] = "html dir not defined"
            mcaConfig["min"] = values[0]
            mcaConfig["max"] = values[-1]
            mcaConfig["file"] = "/Not/existing/Configure/file"

            time.sleep(3)
            self.emit('xrfSpectrumFinished', (mcaData, mcaCalib, mcaConfig))
