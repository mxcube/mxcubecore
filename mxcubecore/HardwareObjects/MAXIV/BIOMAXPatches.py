from mxcubecore.BaseHardwareObjects import HardwareObject
import types
import logging
import gevent
import time
from mxcubecore import HardwareRepository as HWR


class BIOMAXPatches(HardwareObject):
    """
    Hwobj for patching hwobj methods without inheriting classes.
    """

    def before_load_sample(self):
        """
        Ensure that the detector is in safe position and sample changer in SOAK
        """
        if not HWR.beamline.config.sample_changer._chnPowered.get_value():
            raise RuntimeError("Cannot load sample, sample changer not powered")
        if not self.sc_in_soak():
            logging.getLogger("HWR").info(
                "Sample changer not in SOAK position, moving there..."
            )
            try:
                self.sample_changer_maintenance.send_command("soak")
                time.sleep(0.25)
                HWR.beamline.config.sample_changer._wait_device_ready(45)
            except Exception as ex:
                raise RuntimeError(
                    "Cannot load sample, sample changer cannot go to SOAK position: %s"
                    % str(ex)
                )
        self.curr_dtox_pos = HWR.beamline.config.detector.distance.get_value()
        if (
            HWR.beamline.config.detector.distance is not None
            and HWR.beamline.config.detector.distance.get_value() < self.safe_position
        ):
            logging.getLogger("HWR").info(
                "Moving detector to safe position before loading a sample."
            )
            logging.getLogger("user_level_log").info(
                "Moving detector to safe position before loading a sample."
            )

        self.wait_motor_ready(HWR.beamline.config.detector.distance)
        try:
            HWR.beamline.config.detector.distance.set_value(self.safe_position, timeout=30)
        except Exception:
            logging.getLogger("HWR").warning("Cannot move detector")
        else:
            logging.getLogger("HWR").info("Detector already in safe position.")
            logging.getLogger("user_level_log").info(
                "Detector already in safe position."
            )
        try:
            logging.getLogger("HWR").info(
                "Waiting for Diffractometer to be ready before proceeding with the sample loading."
            )
            HWR.beamline.config.diffractometer.wait_device_ready(15)
        except Exception as ex:
            logging.getLogger("HWR").warning(
                "Diffractometer not ready. Proceeding with the sample loading, good luck..."
            )
        else:
            logging.getLogger("HWR").info(
                "Diffractometer ready, proceeding with the sample loading."
            )
            time.sleep(1)

    def after_load_sample(self):
        """
        Move to centring after loading the sample
        """
        if not HWR.beamline.config.sample_changer._chnPowered.get_value():
            raise RuntimeError(
                "Not proceeding with the steps after sample loading, sample changer not powered"
            )
        if (
            HWR.beamline.config.diffractometer is not None
            and HWR.beamline.config.diffractometer.get_current_phase() != "Centring"
        ):
            logging.getLogger("HWR").info("Changing diffractometer phase to Centring")
            logging.getLogger("user_level_log").info(
                "Changing diffractometer phase to Centring"
            )
            try:
                HWR.beamline.config.diffractometer.wait_device_ready(15)
            except Exception:
                pass
            HWR.beamline.config.diffractometer.set_phase("Centring")
            logging.getLogger("HWR").info(
                "Diffractometer phase changed, current phase: %s"
                % HWR.beamline.config.diffractometer.get_current_phase()
            )
        else:
            logging.getLogger("HWR").info("Diffractometer already in Centring")
            logging.getLogger("user_level_log").info(
                "Diffractometer already in Centring"
            )
        logging.getLogger("HWR").info(
            "Moving detector to pre-mount position %s" % self.curr_dtox_pos
        )
        try:
            if not HWR.beamline.config.sample_changer._chnPowered.get_value():
                raise RuntimeError(
                    "Not moving detector to pre-mount position, sample changer not powered"
                )
            HWR.beamline.config.detector.distance.set_value(self.curr_dtox_pos, timeout=30)
        except Exception:
            logging.getLogger("HWR").warning("Cannot move detector")

    def new_load(self, *args, **kwargs):
        logging.getLogger("HWR").debug("Patched sample load version.")
        try:
            sample = kwargs.get("sample", None)
        except Exception:
            pass
        if sample is None:
            sample = args[1]

        logging.getLogger("HWR").debug(
            "Patched sample load version. Sample to load: %s" % sample
        )

        self.before_load_sample()
        self.__load(sample)
        self.after_load_sample()

    def new_unload(self, *args, **kwargs):
        logging.getLogger("HWR").info(
            "Sample changer in SOAK position: %s" % self.sc_in_soak()
        )
        self.before_load_sample()
        self.__unload(args[1])
        # self.after_load_sample()

    def wait_motor_ready(self, mot_hwobj, timeout=30):
        with gevent.Timeout(timeout, RuntimeError("Motor not ready")):
            while mot_hwobj.is_moving():
                gevent.sleep(0.5)

    def sc_in_soak(self):
        return HWR.beamline.config.sample_changer._chnInSoak.get_value()

    def init(self, *args):
        self.sample_changer_maintenance = self.get_object_by_role(
            "sample_changer_maintenance"
        )
        self.__load = HWR.beamline.config.sample_changer.load
        self.__unload = HWR.beamline.config.sample_changer.unload
        self.curr_dtox_pos = None

        HWR.beamline.config.sample_changer.load = types.MethodType(
            self.new_load, HWR.beamline.config.sample_changer
        )
        HWR.beamline.config.sample_changer.unload = types.MethodType(
            self.new_unload, HWR.beamline.config.sample_changer
        )
