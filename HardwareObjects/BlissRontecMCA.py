from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareObjects.abstract.AbstractMCA import AbstractMCA
from HardwareRepository.TaskUtils import task


class BlissRontecMCA(AbstractMCA, HardwareObject):
    def __init__(self, name):
        AbstractMCA.__init__(self)
        HardwareObject.__init__(self, name)
        self.mca = None
        self.calib_cf = []

    def init(self):
        session = self.get_object_by_role("bliss_session")
        obj_name = self.get_property("object_name")
        self.mca = getattr(session, obj_name)

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
