import logging
import time

import gevent
import numpy

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.TaskUtils import cleanup

SCAN_LENGTH = 500


class XRFMockup(HardwareObject):
    def init(self):
        self.ready_event = gevent.event.Event()
        self.spectrumInfo = {}
        self.spectrumInfo["startTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.spectrumInfo["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.spectrumInfo["energy"] = 0
        self.spectrumInfo["beamSizeHorizontal"] = 0
        self.spectrumInfo["beamSizeVertical"] = 0
        self.ready_event = gevent.event.Event()
        self.__scan_data = dict()

        # self.plottin_hwobj = self.get_object_by_role('plotting')

    def is_connected(self):
        return True

    def canSpectrum(self):
        return True

    def gaussian(self, x, mu, sig):
        return numpy.exp(-numpy.power(x - mu, 2.0) / (2 * numpy.power(sig, 2.0)))

    # for mu, sig in [(-1, 1), (0, 2), (2, 3)]:
    #     mp.plot(gaussian(np.linspace(-3, 3, 120), mu, sig))

    def startXrfSpectrum(
        self, ct, directory, arch_dir, prefix, session_id=None, blsample_id=None
    ):
        s1 = self.gaussian(numpy.linspace(0, 3, SCAN_LENGTH), 1, 0.1)
        s2 = self.gaussian(numpy.linspace(0, 3, SCAN_LENGTH), 2, 0.3) * (
            0.25 * numpy.random.rand()
        )
        raw_data = s1 + s2

        logging.getLogger("HWR").info("XRF Spectrum Started, task id: %d" % blsample_id)
        self.scanning = True
        self.emit("xrfSpectrumStarted", ())
        with cleanup(self.ready_event.set):
            self.spectrumInfo["sessionId"] = session_id
            self.spectrumInfo["blSampleId"] = blsample_id
            if blsample_id is None:
                blsample_id = numpy.random.randint(1, 999999)

            scan_info = {
                "scan_nb": blsample_id,
                "title": "XRF Scan",
                "labels": ["energy", "diode value"],
            }
            scan_id = scan_info["scan_nb"]
            self.__scan_data[scan_id] = list()

            self.emit(
                "new_plot",
                {
                    "id": scan_info["scan_nb"],
                    "title": scan_info["title"],
                    "labels": scan_info["labels"],
                },
            )

            for i in range(SCAN_LENGTH):
                try:
                    data = {"energy": i, "diode value": raw_data[i]}
                    new_data = numpy.column_stack(
                        [data[name] for name in scan_info["labels"]]
                    )
                    self.__scan_data[scan_id].append(new_data)
                    aux = numpy.concatenate(self.__scan_data[scan_id]).tolist()
                    self.emit("plot_data", {"id": scan_id, "data": aux})
                    if divmod(i, SCAN_LENGTH / 10)[1] == 0:
                        progress = i / float(SCAN_LENGTH)
                        logging.getLogger("HWR").info(
                            "XRF Spectrum Progress %f" % progress
                        )
                        self.emit("xrf_task_progress", (blsample_id, progress))

                    gevent.sleep(0.02)
                except Exception as ex:
                    print(("Exception ", ex))

            self.emit(
                "plot_end",
                {
                    "id": scan_id,
                    "data": numpy.concatenate(self.__scan_data[scan_id]).tolist(),
                    "type": "XRFScan",
                },
            )

            mcaCalib = [10, 1, 21, 0]
            mcaConfig = {}
            mcaConfig["legend"] = "XRF test scan from XRF mockup"
            mcaConfig["htmldir"] = "html dir not defined"
            mcaConfig["min"] = raw_data[0]
            mcaConfig["max"] = raw_data[-1]
            mcaConfig["file"] = None
            res = []
            for arr in self.__scan_data[scan_id]:
                res.append(arr[0].tolist())

            self.emit("xrfSpectrumFinished", (res, mcaCalib, mcaConfig))
            logging.getLogger("HWR").info("XRF Spectrum Finished")
            del self.__scan_data[scan_id]
