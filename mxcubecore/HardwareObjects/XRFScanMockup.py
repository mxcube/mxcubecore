import logging
import gevent
import time
import numpy

from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository.TaskUtils import cleanup

class XRFScanMockup(Equipment):
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

    def startXrfSpectrum(self, ct, directory, prefix, session_id = None, blsample_id = None):

        self.scanning = True
        self.emit('xrfScanStarted', ())

        with cleanup(self.ready_event.set):
            self.spectrumInfo["sessionId"] = session_id
            self.spectrumInfo["blSampleId"] = blsample_id
      
            mcaData = []
            calibrated_data = []  
            values = [0, 200, 300, 500, 600, 700, 800, 900, 1000, 1500, 1600,
                      1000, 700, 600, 500, 450, 300, 200, 100, 0, 0 ,0, 90]
            for n, value in enumerate(values):
                mcaData.append((n, value))

            mcaCalib = [10,1, 21, 0]
            mcaConfig = {}
            mcaConfig["legend"] = "XRF test scan from XRF mockup"
            mcaConfig['htmldir'] = "html dir not defined"
            mcaConfig["min"] = values[0]
            mcaConfig["max"] = values[-1]
            mcaConfig["file"] = None

            time.sleep(3)

            self.emit('xrfScanFinished', (mcaData, mcaCalib, mcaConfig))
