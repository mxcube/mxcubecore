from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.TaskUtils import task
from mxcubecore import HardwareRepository as HWR


class BlissRontecMCA(HardwareObject):

    def __init__(self, name):
        super().__init__(name)
        self.mca = None

    def init(self):
        actuator_name = self.get_property("actuator_name")
        try:
            self.mca = HWR.beamline.bliss_proxy.get_object(actuator_name)
        except Exception as exc:
            # BLISS object missing — run in offline/no-hardware mode
            import logging

            logging.getLogger("MX3.HWR").warning(
                "BlissRontecMCA '%s': BLISS object '%s' not available (%s)",
                self.name if hasattr(self, "name") else actuator_name,
                actuator_name,
                exc,
            )
            self.mca = None

    @task
    def read_raw_data(self, chmin=0, chmax=4095, save_data=False):
        return self.mca.read_raw_data(chmin, chmax, save_data)

    @task
    def read_roi_data(self, save_data=False):
        return self.mca.read_roi_data(save_data)

    @task
    def read_data(self, chmin=0, chmax=4095, calib=False, save_data=False):
        return self.mca.read_data(chmin, chmax, calib, save_data)

    @task
    def set_calibration(self, fname=None, calib_cf=None):
        calib = None
        if fname:
            calib = fname
        elif calib_cf:
            calib = calib_cf
        return self.mca.set_calibration(calib)

    @task
    def get_calibration(self):
        return self.mca.get_calibration()

    @task
    def set_roi(self, emin, emax, **kwargs):
        self.mca.set_roi(emin, emax, **kwargs)

    @task
    def get_roi(self, **kwargs):
        return self.mca.get_roi(**kwargs)

    @task
    def clear_roi(self, **kwargs):
        self.mca.clear_roi(**kwargs)

    @task
    def get_times(self):
        return self.mca.get_times()

    @task
    def get_presets(self, **kwargs):
        return self.mca.get_presets(**kwargs)

    @task
    def set_presets(self, **kwargs):
        self.mca.set_presets(**kwargs)

    @task
    def start_acq(self, cnt_time=None):
        self.mca.start_acq(cnt_time)

    @task
    def stop_acq(self):
        self.mca.stop_acq()

    @task
    def clear_spectrum(self):
        self.mca.clear_spectrum()
