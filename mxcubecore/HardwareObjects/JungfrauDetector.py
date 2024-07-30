import math
from tango import DeviceProxy, DevState
from mxcubecore.utils.units import us_to_sec, sec_to_us, ev_to_kev, meter_to_mm
from mxcubecore.HardwareObjects.abstract.AbstractDetector import AbstractDetector
from mxcubecore.BaseHardwareObjects import HardwareObjectState

# custom tango reply timeout
TANGO_TIMEOUT_MS = 6000

# time to wait between reading detector state, in seconds
STATE_POLL_INTERVAL = 0.4

TANGO_TO_HWO_STATES = {
    DevState.ON: HardwareObjectState.READY,
    DevState.RUNNING: HardwareObjectState.BUSY,
    DevState.OFF: HardwareObjectState.OFF,
    DevState.FAULT: HardwareObjectState.FAULT,
}


class JungfrauDetector(AbstractDetector):
    """
    Detector hardware object implementation for Jungfrau line of detectors.

    This hardware object assumes that detector control is abstracted by a tango device,
    as implemented here:

    https://gitlab.maxiv.lu.se/scisw/detectors/dev-maxiv-jungfrau/

    This hardware object requires tango device version 0.6.1 or later.

    Hardware object properties:
        detector_device (str): name of the detector's tango device
    """

    # pixel size in millimeters (75 µm)
    PIXEL_SIZE = 0.075
    FILE_SUFFIX = "h5"

    def __init__(self, *args):
        super().__init__(*args)

        # set default values for some properties
        self.set_property("model", "JUNGFRAU")
        self.set_property("type", "charge integrating dynamic gain switching device")
        self.set_property("manufacturer", "PSI")
        self.set_property("file_suffix", self.FILE_SUFFIX)

        self.col_config = {
            "OmegaStart": None,
            "OmegaIncrement": None,
            "BeamCenterX": None,
            "BeamCenterY": None,
            "DetectorDistance": None,
            "CountTime": None,
            "NbImages": None,
            "NbTriggers": None,
            "ImagesPerFile": None,
            "RoiMode": None,
            "FilenamePattern": None,
            "PhotonEnergy": None,
            "TriggerMode": "exts",
            "UnitCellA": None,
            "UnitCellB": None,
            "UnitCellC": None,
            "UnitCellAlpha": None,
            "UnitCellBeta": None,
            "UnitCellGamma": None,
        }

    def init(self):
        super().init()
        self.dev = DeviceProxy(self.detector_device)
        # Arm() command can block for more than 3 seconds,
        # increase the default tango timeout
        self.dev.set_timeout_millis(TANGO_TIMEOUT_MS)

        #
        # pull detector's tango device state
        # TODO: replace poller with event listener
        #
        channel = self.add_channel(
            {
                "type": "tango",
                "name": "_chnState",
                "tangoname": self.detector_device,
                "polling": 300,
            },
            "State",
        )
        channel.connect_signal("update", self._state_changed)

    def _state_changed(self, tango_state):
        hwo_state = TANGO_TO_HWO_STATES.get(tango_state, HardwareObjectState.UNKNOWN)
        self.update_state(hwo_state)

    #
    # Sends the software trigger to Jungfrau,
    # This is not part of the AbstractDetector API,
    # probably software triggering should be done differently.
    #
    def trigger(self):
        self.dev.SoftwareTrigger()

    def get_storage_cell_count(self):
        return self.dev.storage_cell_count

    def get_minimum_exposure_time(self) -> float:
        """
        current minimum exposure time, in seconds, inclusive
        """
        return us_to_sec(self.dev.frame_time_us)

    def get_pixel_size_x(self):
        return self.PIXEL_SIZE

    def get_pixel_size_y(self):
        return self.PIXEL_SIZE

    def set_photon_energy(self, energy):
        """
        set energy, in KeV
        """
        self.dev.photon_energy_keV = ev_to_kev(energy)

    def enable_filewriter(self):
        # we don't need to enable Jungfrau file writer,
        # it is always running, thus this is a NOP
        pass

    def enable_stream(self):
        # not implemented
        pass

    def disable_stream(self):
        # not implemented
        pass

    def prepare_acquisition(self, config):
        def maybe_set(attr: str, conf_name: str):
            """
            Optionally set tango device attribute from the config dictionary.

            If config value is None, don't set.
            If config value is not None, write its value to the specified attribute.
            """
            val = config[conf_name]
            if val is None:
                return
            setattr(dev, attr, val)

        # make sure that detector is in 'idle' mode,
        # otherwise we won't be able to arm it
        self.stop_acquisition()

        #
        # send acquisition parameters to the detector
        #

        dev = self.dev
        dev.omega__start = config["OmegaStart"]
        dev.omega__step = config["OmegaIncrement"]
        dev.beam_x_pxl = config["BeamCenterX"]
        dev.beam_y_pxl = config["BeamCenterY"]
        dev.detector_distance_mm = meter_to_mm(config["DetectorDistance"])
        dev.images_per_trigger = config["NbImages"]
        dev.ntrigger = config["NbTriggers"]

        maybe_set("unit_cell__a", "UnitCellA")
        maybe_set("unit_cell__b", "UnitCellB")
        maybe_set("unit_cell__c", "UnitCellC")
        maybe_set("unit_cell__alpha", "UnitCellAlpha")
        maybe_set("unit_cell__beta", "UnitCellBeta")
        maybe_set("unit_cell__gamma", "UnitCellGamma")

        exposure_time = sec_to_us(config["CountTime"])
        dev.summation = math.ceil(exposure_time / dev.frame_time_us)

        # hard-coded rotation axis
        dev.write_attribute("omega__vector__#1", 0.0)
        dev.write_attribute("omega__vector__#2", 1.0)
        dev.write_attribute("omega__vector__#3", 0.0)

        #
        # set where file should be written,
        # Jungfrau takes paths without the leading '/',
        # e.g. '/foo/bar/muu' must be specified as 'foo/bar/muu'
        #
        dev.file_prefix = config["FilenamePattern"][1:]

        #
        # Arm detector
        #
        dev.Arm()

    def stop_acquisition(self):
        self.dev.Stop()
        self.wait_ready()

    def get_acquisition_time(self) -> float:
        """
        current acquisition time, in seconds
        """
        dev = self.dev
        acq_time_us = dev.images_per_trigger * dev.frame_time_us * dev.summation
        return us_to_sec(acq_time_us)

    def wait_config_done(self):
        # the config is fully applied when Arm command finishes in the
        # prepare_acquisition() method above, thus no need to wait for anything
        pass

    def set_header_appendix(self, _):
        # hopefully no need to do anything with the header on Jungfrau detectors,
        # presumably they already contain required fields
        pass

    def disarm(self):
        # Jungfrau does not support disarming, so no-op
        pass

    def pedestal(self):
        self.dev.Pedestal()
