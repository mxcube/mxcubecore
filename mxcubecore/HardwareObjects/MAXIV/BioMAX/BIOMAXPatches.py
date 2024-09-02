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

    def before_load_sample(self):  # noqa
        """
        Ensure that the detector is in safe position and sample changer in SOAK
        """
        # applies reset (safe to do) always just in case the sc is in false fault
        HWR.beamline.sample_changer_maintenance.send_command("reset")

        if HWR.beamline.sample_changer.get_status() == "fault":
            raise RuntimeError("Cannot operate sample changer, state is in FAULT.")

        HWR.beamline.sample_changer_maintenance.mount_timeout_fixed = False
        logging.getLogger("HWR").info("Set sc mount timeout flag to False")

        if HWR.beamline.diffractometer.get_transfer_mode() != "SAMPLE_CHANGER":
            raise Exception(
                'MD3 sample transfer mode is not set to SAMPLE_CHANGER! Please check the setting \
                in MD3 user preferences and also make sure "Sample changer auto change phase" is checked'
            )

        if HWR.beamline.diffractometer.last_centered_position is not None:
            phiy = HWR.beamline.diffractometer.last_centered_position.get("phiy", 999)
            kappa = HWR.beamline.diffractometer.last_centered_position.get("kappa", 0)
            kappa_phi = HWR.beamline.diffractometer.last_centered_position.get(
                "kappa_phi", 0
            )
            logging.getLogger("HWR").info("The PhiY after centering is %s" % phiy)
            if abs(kappa) < 0.1 and abs(kappa_phi) < 0.1 and phiy < -4.6:
                raise RuntimeError(
                    "Sample pin is too long and there is a risk of collision! Please remove the sample manually and run empty_sample_mounted afterwards!"
                )

        self.curr_dtox_pos = HWR.beamline.detector.distance.get_value()
        if (
            HWR.beamline.detector.distance is not None
            and self.curr_dtox_pos < self.safe_position
        ):
            logging.getLogger("HWR").info(
                "Moving detector to safe position before loading a sample."
            )
            logging.getLogger("user_level_log").info(
                "Moving detector to safe position before loading a sample."
            )
            HWR.beamline.detector.distance.wait_ready(30)

            try:
                HWR.beamline.detector.distance.set_value(self.safe_position)
                HWR.beamline.detector.distance.wait_end_of_move(30)
            except Exception:
                msg = (
                    "Cannot move detector, please contact support and check the key!!!"
                )
                logging.getLogger("HWR").error(msg)
                raise Exception(msg)
            finally:
                msg = "Detector in safe position, position: {}".format(
                    HWR.beamline.detector.distance.get_value()
                )
                logging.getLogger("HWR").info(msg)
                logging.getLogger("user_level_log").info(msg)
        else:
            logging.getLogger("HWR").info("Detector already in safe position.")
            logging.getLogger("user_level_log").info(
                "Detector already in safe position."
            )

        if not HWR.beamline.sample_changer.is_powered():
            try:
                HWR.beamline.sample_changer_maintenance.send_command("powerOn")
                time.sleep(1)
                HWR.beamline.sample_changer._wait_device_ready(30)
                if not HWR.beamline.sample_changer.is_powered():
                    raise RuntimeError(
                        "Cannot power on sample changer. please make sure the hutch is searched"
                    )
            except Exception:
                raise RuntimeError(
                    "Cannot power on sample changer. please make sure the hutch is searched"
                )

        if HWR.beamline.sample_changer.is_path_running():
            timeout = 240
            HWR.beamline.sample_changer._wait_device_ready(timeout)
            if HWR.beamline.sample_changer_maintenance.is_path_running():
                raise RuntimeError(
                    "Cannot load sample, sample changer has been moving for over {} s. Please check the device".format(
                        timeout
                    )
                )
        if not self.sc_in_soak():
            logging.getLogger("HWR").info(
                "Sample changer not in SOAK position, moving there..."
            )
            try:
                HWR.beamline.sample_changer_maintenance.send_command("soak")
                time.sleep(0.25)
                HWR.beamline.sample_changer._wait_device_ready(45)
            except Exception as ex:
                raise RuntimeError(
                    "Cannot load sample, sample changer cannot go to SOAK position: %s"
                    % str(ex)
                )

        try:
            logging.getLogger("HWR").info(
                "Waiting for Diffractometer to be ready before proceeding with the sample loading."
            )
            """
            The two wait_device_ready here is a temporary solution. It's to deal with the scenario when users
            change phase after launching sample mount. As the datacollection-> centring phase change in MD3 hwobj
            is actually a phase change followed by move_sync_motors and between the two commands there is a small window
            that the MD3 device is ready. So here we added two wait to make sure the isara doesn't run getput until after
            the move_sync_motor is finished.
            """
            HWR.beamline.diffractometer.wait_ready(30)
            time.sleep(2)
            HWR.beamline.diffractometer.wait_ready(30)
        except Exception:
            logging.getLogger("HWR").error(
                "Diffractometer not ready. Check diffractometer status"
            )
            raise RuntimeError(
                "Diffractometer not ready. Check diffractometer status. Sample loading cancelled."
            )
        else:
            logging.getLogger("HWR").info(
                "Diffractometer ready, proceeding with the sample loading."
            )
            time.sleep(1)
        # clean up sample centring method, which otherwise may cause continuous failure of automatic centring
        HWR.beamline.diffractometer.current_centring_method = None
        HWR.beamline.diffractometer.last_centered_position = None

    def sc_recovery_after_timeout(self):
        """
        reset the sample changer timeout flag and also make sure the gripper doesn't end in a strange position after drying
        pop up msg to user interface
        """
        if HWR.beamline.sample_changer_maintenance.mount_timeout_fixed:
            try:
                # here we put try the waitReady twice as there could be a small windown between back and dry that the SC is ready
                HWR.beamline.sample_changer._wait_device_ready(180)
                time.sleep(1)
                self.sample_changer._wait_device_ready(180)
            except Exception as ex:
                (
                    state_dict,
                    cmd_state,
                    message,
                ) = HWR.beamline.sample_changer_maintenance.get_global_state()
                if (
                    "WAIT for Dew_C condition / 31" in message
                    or "Gripper drying in progress" in message
                ):
                    HWR.beamline.sample_changer_maintenance.send_command("abort")
                    HWR.beamline.sample_changer_maintenance.send_command("reset")
                    HWR.beamline.sample_changer_maintenance.send_command("safe")
                    HWR.beamline.sample_changer._wait_device_ready(20)
                else:
                    raise Exception(
                        "Cannot load/unload sample and get error %s while waiting for SC to put sample back, please contact support."
                        % str(ex)
                    )
            finally:
                HWR.beamline.sample_changer_maintenance.mount_timeout_fixed = False
                logging.getLogger("HWR").info("Set sc mount timeout flag to False")
            error_msg = "[SC] Timeout when waiting MD3 to move to transfer phase. Have put the sample back (if applies), please try to mount/unmount again when the Sample Changer is ready!"
            logging.getLogger("HWR").error(error_msg)
            raise Exception(error_msg)

    def after_load_sample(self):
        """
        Move to centring after loading the sample
        """
        if not HWR.beamline.sample_changer.is_powered():
            raise RuntimeError(
                "Not proceeding with the steps after sample loading, sample changer not powered"
            )

        if (
            HWR.beamline.diffractometer is not None
            and HWR.beamline.diffractometer.get_current_phase() != "Centring"
        ):
            logging.getLogger("HWR").info("Changing diffractometer phase to Centring")
            logging.getLogger("user_level_log").info(
                "Changing diffractometer phase to Centring"
            )
            try:
                HWR.beamline.diffractometer.wait_ready(15)
            except Exception:
                pass
            HWR.beamline.diffractometer.set_phase("Centring")
            logging.getLogger("HWR").info(
                "Diffractometer phase changed, current phase: %s"
                % HWR.beamline.diffractometer.get_current_phase()
            )
        else:
            logging.getLogger("HWR").info("Diffractometer already in Centring")
            logging.getLogger("user_level_log").info(
                "Diffractometer already in Centring"
            )
        sample_is_loaded = HWR.beamline.diffractometer.channel_dict[
            "SampleIsLoaded"
        ].get_value()
        if not sample_is_loaded:
            logging.getLogger("HWR").error(
                "No sample detected on the goniometer, please check the camera!"
            )
            raise Exception("No sample detected on the goniometer!")

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
        self.sc_recovery_after_timeout()
        self.after_load_sample()

    def new_unload(self, *args, **kwargs):
        logging.getLogger("HWR").info(
            "Sample changer in SOAK position: %s" % self.sc_in_soak()
        )
        self.before_load_sample()
        self.__unload(args[1])
        self.sc_recovery_after_timeout()

    def sc_in_soak(self):
        return HWR.beamline.sample_changer._chnInSoak.get_value()

    def init(self, *args):
        self.__load = HWR.beamline.sample_changer.load
        self.__unload = HWR.beamline.sample_changer.unload
        self.curr_dtox_pos = None

        HWR.beamline.sample_changer.load = types.MethodType(
            self.new_load, HWR.beamline.sample_changer
        )
        HWR.beamline.sample_changer.unload = types.MethodType(
            self.new_unload, HWR.beamline.sample_changer
        )
