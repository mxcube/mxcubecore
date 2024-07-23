import gevent
import time
import copy
import logging

from mxcubecore.TaskUtils import task
from mxcubecore.model.queue_model_objects import PathTemplate
from mxcubecore.HardwareObjects.abstract.AbstractDetector import AbstractDetector
from mxcubecore import HardwareRepository as HWR


class BIOMAXEiger(AbstractDetector):
    """Eiger hwobj based on tango
    hardware status:
    ready:   ready for trigger (this is the state after an "Arm" command)
    idle:    ready for config (this should be the state after a "Disarm" command)
    """

    def __init__(self, *args, **kwargs):
        """
        Descrip. :
        """
        AbstractDetector.__init__(self, *args, **kwargs)

        self.device = None
        self.file_suffix = None
        self.default_exposure_time = None
        self.default_compression = None
        self.buffer_limit = None
        self.dcu = None
        self.config_state = None
        self.initialized = False
        self.status_chan = None
        self.energy_change_threshold_default = 20

    def init(self):
        super(BIOMAXEiger, self).init()
        tango_device = self.get_property("detector_device")
        self.cover_hwobj = self.get_object_by_role("detector_cover")
        self.file_suffix = self.get_property("file_suffix")
        self.default_exposure_time = self.get_property("default_exposure_time")
        self.default_compression = self.get_property("default_compression")
        self.buffer_limit = self.get_property("buffer_limit")
        self.dcu = self.get_property("dcu")
        attr_list = (
            "NbImages",
            "Temperature",
            "Humidity",
            "CountTime",
            "CountrateCorrectionCountCutoff",
            "FrameTime",
            "PhotonEnergy",
            "Wavelength",
            "EnergyThreshold",
            "FlatfieldEnabled",
            "AutoSummationEnabled",
            "TriggerMode",
            "RateCorrectionEnabled",
            "BitDepth",
            "ReadoutTime",
            "Description",
            "Time",
            "NbTriggers",
            "XPixelSize",
            "YPixelSize",
            "CountTimeInte",
            "DownloadDirectory",
            "FilesInBuffer",
            "Error",
            "BeamCenterX",
            "BeamCenterY",
            "DetectorDistance",
            "OmegaIncrement",
            "OmegaStart",
            "Compression",
            "RoiMode",
            "State",
            # "Status",
            "XPixelsDetector",
            "YPixelsDetector",
            "CollectionUUID",
            "RoiMode",
            "HeaderDetail",
            "HeaderAppendix",
            "ImageAppendix",
            "StreamState",
            "FilenamePattern",
            "ImagesPerFile",
            "BufferFree",
            "FileWriterState",
            "ImageNbStart",
            "MonitorMode",
            "DiscardNew",
            "FileWriterMode",
        )

        # config needed to be set up for data collection
        # if values are None, use the one from the system
        self.col_config = {
            "OmegaStart": 0,
            "OmegaIncrement": 0.1,
            "BeamCenterX": None,  # length not pixel
            "BeamCenterY": None,
            "DetectorDistance": None,
            "CountTime": None,
            "NbImages": None,
            "NbTriggers": None,
            "ImagesPerFile": None,
            "RoiMode": None,
            # enable 'all' header details by default
            "HeaderDetail": "all",
            "FilenamePattern": None,
            "PhotonEnergy": None,
            "TriggerMode": "exts",
        }

        # config needed for dozor online analysis
        self.dozor_dict = {
            "beam_center_x": 0.0,
            "beam_center_y": 0.0,
            "count_time": 0.0,
            "countrate_correction_count_cutoff": 0,
            "detector_distance": 0.0,
            "omega_increment": 0.0,
            "x_pixels_in_detector": 0,
            "x_pixel_size": 0.000075,
            "y_pixels_in_detector": 0,
            "wavelength": 0.0,
        }

        # not all of the following commands are needed, for now all of them here
        # for convenience
        cmd_list = (
            "Arm",
            "Trigger",
            "Abort",
            "Cancel",
            "ClearBuffer",
            "DeleteFileFromBuffer",
            "Disarm",
            "DownloadFilesFromBuffer",
            "EnableStream",
            "DisableStream",
        )

        # we need to program timeout once in the device
        # get any of the channels for that.
        for channel_name in attr_list:
            self.add_channel(
                {
                    "type": "tango",
                    "name": channel_name,
                    "tangoname": tango_device,
                    "polling": 12000,
                },
                channel_name,
            )

        self.add_channel(
            {
                "type": "tango",
                "name": "Status",
                "tangoname": tango_device,
                "polling": 1000,
            },
            "Status",
        )
        for cmd_name in cmd_list:
            self.add_command(
                {
                    "type": "tango",
                    "name": cmd_name,
                    "timeout": 8000,
                    "tangoname": tango_device,
                },
                cmd_name,
            )
        # init the detector settings in case of detector restart
        # use bslz4 for compression ()

        # we need to call the init device before accessing the channels here
        #   otherwise the initialization is triggered by the HardwareRepository Poller
        #   that is delayed after the application starts

        try:
            self.energy_change_threshold = float(
                self.get_property("min_trigger_energy_change")
            )
        except Exception:
            self.energy_change_threshold = self.energy_change_threshold_default

        self.get_channel_object("Compression").init_device()
        self.get_channel_object("Compression").set_value("bslz4")

        self.photon_energy_channel = self.get_channel_object("PhotonEnergy")
        self.photon_energy_channel.init_device()
        photon_energy_info = self.photon_energy_channel.get_info()
        self.photon_energy_max = float(photon_energy_info.max_value)
        self.photon_energy_min = float(photon_energy_info.min_value)

        self.frame_time_channel = self.get_channel_object("FrameTime")
        self.frame_time_channel.init_device()

        frame_time_info = self.frame_time_channel.get_info()
        self.frame_time_min = float(frame_time_info.min_value)
        _status = self.get_channel_object("Status")

        _status.connect_signal("update", self.status_update)
        self.update_state(self.STATES.READY)

    #  STATUS , status can be "idle", "ready", "UNKNOWN"
    def get_status(self):
        if self.status_chan is None:
            self.status_chan = self.get_channel_object("Status")

            if self.status_chan is not None:
                self.initialized = True
            else:
                return "not_init"

        return self.status_chan.get_value().split("\n")[0]

    def status_update(*args):
        logging.getLogger("HWR").debug("eiger satus update {}".format(args))

    def is_idle(self):
        return self.get_status()[:4] == "idle"

    def is_ready(self):
        return self.get_status()[:5] == "ready"

    def is_acquire(self):
        return self.get_status() == "acquire"

    def is_preparing(self):
        return self.config_state == "config"

    def prepare_error(self):
        if self.config_state == "error":
            return True
        else:
            return False

    def wait_ready(self, timeout=20):
        with gevent.Timeout(timeout, RuntimeError("Detector not ready")):
            while not self.is_ready():
                gevent.sleep(0.1)

    def wait_ready_or_idle(self):
        with gevent.Timeout(20, RuntimeError("Detector neither ready or idle")):
            while not (self.is_ready() or self.is_idle()):
                logging.getLogger("HWR").debug(
                    "Waiting for the detector to be ready, current state: "
                    + self.get_status()
                )
                gevent.sleep(0.25)

    def wait_idle(self):
        with gevent.Timeout(20, RuntimeError("Detector not ready")):
            while not self.is_idle():
                gevent.sleep(0.25)

    def wait_acquire(self):
        with gevent.Timeout(20, RuntimeError("Detector not ready")):
            while not self.is_acquire():
                gevent.sleep(0.25)

    def wait_buffer_ready(self):
        with gevent.Timeout(
            20, RuntimeError("Detector free buffer size is lower than limit")
        ):
            while self.get_buffer_free() < self.buffer_limit:
                gevent.sleep(0.25)

    def wait_config_done(self):
        logging.getLogger("HWR").info("Waiting to configure the detector.")
        with gevent.Timeout(30, RuntimeError("Detector configuration error")):
            while self.is_preparing():
                gevent.sleep(0.1)
        if self.prepare_error():
            raise RuntimeError("Detector configuration failed")
        logging.getLogger("HWR").info("Detector configuration finished.")

    def isclose(self, a, b, rel_tol=1e-04, abs_tol=0.0):
        # implementation from PEP 485
        return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

    def wait_attribute_applied(self, att, new_val):
        with gevent.Timeout(
            10,
            RuntimeError(
                "Timeout setting attr: %s to value %s, type: %s"
                % (att, new_val, type(new_val))
            ),
        ):
            if att in [
                "FilenamePattern",
                "HeaderDetail",
                "HeaderAppendix",
                "ImageAppendix",
                "TriggerMode",
                "RoiMode",
                "MonitorMode",
                "FileWriterMode",
            ]:
                while self.get_value(att) != new_val:
                    gevent.sleep(0.1)
            elif "BeamCenter" in att:
                while not self.isclose(self.get_value(att), new_val, rel_tol=1e-02):
                    gevent.sleep(0.1)
            else:
                while not self.isclose(self.get_value(att), new_val, rel_tol=1e-04):
                    gevent.sleep(0.1)

    #  STATUS END

    #  GET INFORMATION
    def get_value(self, name):
        return self.get_channel_object(name).get_value()

    def set_value(self, name, value):
        try:
            logging.getLogger("HWR").debug(
                "[DETECTOR] Setting value: %s for attribute %s" % (value, name)
            )
            self.get_channel_object(name).set_value(value)
            self.wait_attribute_applied(name, value)
        except Exception as ex:
            logging.getLogger("HWR").error(ex)
            logging.getLogger("HWR").error(
                "Cannot set value: %s for attribute %s" % (value, name)
            )
            raise RuntimeError(
                "[DETECTOR] Cannot set value: %s for attribute %s" % (value, name)
            )

    def get_readout_time(self):
        return self.get_value("ReadoutTime")

    def get_acquisition_time(self):
        frame_time = self.get_value("FrameTime")
        readout_time = self.get_value("ReadoutTime")
        nb_images = self.get_value("NbImages")
        time = nb_images * frame_time - readout_time
        _count_time = self._config_vals.get("CountTime")
        _nb_images = self._config_vals.get("NbImages")
        logging.getLogger("HWR").debug(
            "[DETECTOR] Configuration params: CounTime: %s, NbImages: %s"
            % (_count_time, _nb_images)
        )
        logging.getLogger("HWR").debug(
            "[DETECTOR] Params applied IN the detector: FrameTime: %s, NbImages: %s"
            % (frame_time, nb_images)
        )

        if not self.isclose(
            time,
            _nb_images * (_count_time + readout_time) - readout_time,
            rel_tol=1e-04,
        ):
            logging.getLogger("HWR").error(
                "[DETECTOR] Acquisition time configuration wrong."
            )
        logging.getLogger("HWR").info("Detector acquisition time: " + str(time))
        return time

    def get_buffer_free(self):
        return self.get_value("BufferFree")

    def get_roi_mode(self):
        return self.get_value("RoiMode")

    def get_pixel_size_x(self):
        """
        return sizes of a single pixel along x-axis respectively
        unit, mm
        """
        # x_pixel_size = self.get_channel_object("XPixelSize")  # unit, m
        x_pixel_size = 0.000075
        return x_pixel_size * 1000

    def get_pixel_size_y(self):
        """
        return sizes of a single pixel along y-axis respectively
        unit, mm
        """
        # y_pixel_size = self.get_channel_object("YPixelSize")  # unit, m
        y_pixel_size = 0.000075
        return y_pixel_size * 1000

    def get_x_pixels_in_detector(self):
        """
        number of pixels along x-axis
        numbers vary depending on the RoiMode
        """
        return self.get_value("XPixelsDetector")

    def get_y_pixels_in_detector(self):
        """
        number of pixels along y-axis,
        numbers vary depending on the RoiMode
        """
        return self.get_value("YPixelsDetector")

    def get_minimum_exposure_time(self):
        return self.frame_time_min - self.get_readout_time()

    def get_sensor_thickness(self):
        return  # not available, self.get_channel_object("").get_value()

    def has_shutterless(self):
        return True

    def get_collection_uuid(self):
        return self.get_value("CollectionUUID")

    def get_header_appendix(self):
        """
        Data that is appended to the header data
        """
        return self.get_value("HeaderAppendix")

    def get_image_appendix(self):
        """
        Data that is appended to the image data
        """
        return self.get_value("ImageAppendix")

    def get_stream_state(self):
        """
        "disabled", "ready", "acquire" or "error".
        """
        return self.get_value("StreamState")

    def get_filewriter_state(self):
        """
        "disabled", "ready", "acquire" or "error".
        """
        return self.get_value("FilewriterState")

    #  GET INFORMATION END

    #  SET VALUES
    def set_photon_energy(self, energy):
        """
        set photon_energy
        Note, the readout_time will be changed
        engery, in eV
        """
        valid = self._validate_energy_value(energy)

        if valid == -1:
            return False
        elif valid == 0:
            return True  # is valid, but no need to change energy. continue
        else:
            self.set_value("PhotonEnergy", energy)
            return True

    def _validate_energy_value(self, energy):
        try:
            target_energy = float(energy)
        except Exception:
            # not a valid value
            logging.getLogger("user_level_log").info("Wrong Energy value: %s" % energy)
            return -1

        current_energy = self.get_value("PhotonEnergy")

        msg = f"target energy is: {target_energy}\n"
        msg += f"currently configured energy is: {current_energy}\n"
        msg += f" min val: {self.photon_energy_min}/ max val: {self.photon_energy_max}"
        logging.getLogger("HWR").debug(msg)

        if (
            target_energy < self.photon_energy_min
            or target_energy > self.photon_energy_max
        ):
            msg = f"Energy value out of limits: {energy}"
            logging.getLogger("HWR").debug(msg)
            logging.getLogger("user_level_log").info(msg)

            return -1

        if abs(energy - current_energy) > self.energy_change_threshold:
            logging.getLogger("HWR").debug(
                "Energy difference over threshold. program energy necessary"
            )
            return 1
        else:
            logging.getLogger("HWR").debug(
                "Energy difference below threshold. Do not need to program"
            )
            return 0

    def set_energy_threshold(self, threshold):
        """
        set energy_threshold
        Note, the readout_time will be changed
        By deafult, the value is 50% of the photon_energy and will be
        updated upon setting PhotonEnergy. If other values are needed,
        this should be set after changing PhotonEnergy.
        Eengery, in eV
        """
        self.set_value("EnergyThreshold", threshold)

    def set_collection_uuid(self, col_uuid):
        self.set_value("CollectionUUID", col_uuid)

    def set_header_appendix(self, value):
        """
        Data that is appended to the header data
        """
        self.set_value("HeaderAppendix", value)

    def set_image_appendix(self, value):
        """
        Data that is appended to the image data
        """
        self.set_value("ImageAppendix", value)

    def set_roi_mode(self, value):
        if value not in ["4M", "disabled"]:
            logging.getLogger("HWR").error("Cannot set roi mode")
            return
        return self.set_value("RoiMode", value)

    #  SET VALUES END

    def prepare_acquisition(self, config):
        """
        config is a dictionary
        OmegaStart,OmegaIncrement,
        BeamCenterX
        BeamCenterY
        OmegaStart
        OmegaIncrement
        start, osc_range, exptime, ntrigger, number_of_images, images_per_file,
        compression,ROI,wavelength):
        """

        logging.getLogger("user_level_log").info("Preparing acquisition")
        self.set_monitor()

        self.config_state = "config"

        self._config_vals = copy.copy(config)
        try:
            self._prepare_acquisition_sequence()
        except Exception as ex:
            logging.getLogger("HWR").error(
                "[DETECTOR] Could not configure detector %s" % str(ex)
            )
            self._configuration_failed()
        else:
            self._configuration_done()

        logging.getLogger("user_level_log").info(
            "setting dozor dict for online analysis"
        )
        dozor_dict = self.dozor_dict
        dozor_dict["beam_center_x"] = config["BeamCenterX"]
        dozor_dict["beam_center_y"] = config["BeamCenterY"]
        dozor_dict["count_time"] = config["CountTime"]
        dozor_dict["countrate_correction_count_cutoff"] = self.get_value(
            "CountrateCorrectionCountCutoff"
        )
        dozor_dict["detector_distance"] = config["DetectorDistance"]
        dozor_dict["omega_increment"] = config["OmegaIncrement"]
        dozor_dict["x_pixels_in_detector"] = self.get_value("XPixelsDetector")
        dozor_dict["x_pixel_size"] = self.get_value("XPixelSize")
        dozor_dict["y_pixels_in_detector"] = self.get_value("YPixelsDetector")
        dozor_dict["wavelength"] = self.get_value("Wavelength")
        return dozor_dict

    def _configuration_done(self):  # (self, gl)
        logging.getLogger("HWR").info("Detector configuration done")
        self.config_state = None

    def _configuration_failed(self):  # (self, gl)
        self.config_state = "error"
        logging.getLogger("HWR").error("Could not configure detector")
        raise RuntimeError("Could not configure detector")

    def _prepare_acquisition_sequence(self):
        if not self.is_idle():
            self.stop_acquisition()

        self.wait_idle()
        logging.getLogger("HWR").info(
            "Ok. detector is idle. Continuing with configuration"
        )
        logging.getLogger("HWR").info(self._config_vals)
        if "PhotonEnergy" in self._config_vals.keys():
            new_egy = self._config_vals["PhotonEnergy"]
            if new_egy is not None:
                if self.set_photon_energy(new_egy) is False:
                    raise Exception("Could not program energy in detector")
        if "CountTime" in self._config_vals.keys():
            self.set_value("CountTime", self._config_vals["CountTime"])
            msg = "Readout time: {} | count time: {}".format(
                self.get_readout_time(), self.get_value("CountTime")
            )
            logging.getLogger("HWR").debug(msg)
            self.set_value(
                "FrameTime", self._config_vals["CountTime"] + self.get_readout_time()
            )
            msg = "New frame time is {}".format(self.get_value("FrameTime"))
            logging.getLogger("HWR").debug(msg)
            for cfg_name, cfg_value in self._config_vals.items():
                t0 = time.time()
                if cfg_name == "PhotonEnergy" or cfg_name == "CountTime":
                    continue  # already handled above

                logging.getLogger("HWR").info(
                    "Detector: configuring %s: %s" % (cfg_name, cfg_value)
                )
                if cfg_value is None or cfg_value == "":
                    continue

                if cfg_value is not None:
                    if self.get_value(cfg_name) != cfg_value:
                        self.set_value(cfg_name, cfg_value)
                        if cfg_name == "RoiMode":
                            self.emit("roiChanged")
                    else:
                        logging.getLogger("HWR").debug(
                            "      - value does need to change"
                        )
                else:
                    logging.getLogger("HWR").error(
                        "Could not config value %s for detector. Not such channel"
                        % cfg_name
                    )
        logging.getLogger("HWR").info(
            "Detector parameter configuration took %s seconds" % (time.time() - t0)
        )

    @task
    def start_acquisition(self):
        """
        Before starting the acquisition a prepare_acquisition should be issued
        After prepare_acquisition the detector should be in "idle" state

        Otherwise you will have to send a "disarm" command by hand to be able to
        start an acquisition
        """

        self.wait_buffer_ready()

        if not self.is_idle():
            raise RuntimeError(
                "Detector should be idle before starting a new acquisition"
            )

        self.config_state = None

        logging.getLogger("user_level_log").info("Detector going to arm")

        return self.arm()

    def stop_acquisition(self):
        """
        when use external trigger, Disarm is required, otherwise the last h5 will
        not be released and not available in WebDAV.
        """

        logging.getLogger("HWR").info("[DETECTOR] Stop acquisition, waiting...")
        self.wait_ready_or_idle()

        try:
            self.cancel()
            # this is needed as disarm in tango device server does not seem to work
            # as expected. the disarm command in the simpleinterface is always working
            # when called from Tango it does not. Once bug is solved in tango server, the
            # call to "cancel()" is not necessary here
            self.disarm()
            logging.getLogger("HWR").info(
                "[DETECTOR] Stop acquisition, detector canceled and disarmed."
            )
        except Exception as ex:
            RuntimeError("[DETECTOR] Error stopping acquisition: %s" % str(ex))

    def cancel_acquisition(self):
        """Cancel acquisition"""
        logging.getLogger("HWR").info("[DETECTOR] Cancelling acquisition")
        try:
            self.cancel()
        except Exception as ex:
            RuntimeError("[DETECTOR] Error cancelling acquisition: %s" % str(ex))

        time.sleep(1)
        self.disarm()

    def arm(self):
        logging.getLogger("HWR").info("[DETECTOR] Arm command requested")
        cmd = self.get_command_object("Arm")
        cmd.set_device_timeout(10000)
        cmd()
        self.wait_ready()
        logging.getLogger("HWR").info(
            "[DETECTOR] Arm command executed, new state of the dectector: "
            + self.get_status()
        )
        logging.getLogger("user_level_log").info("Detector armed")

    def trigger(self):
        self.get_command_object("Trigger")()

    def disarm(self):
        self.get_command_object("Disarm")()

    def enable_filewriter(self):
        self.set_value("FileWriterMode", "enabled")

    def disable_filewriter(self):
        self.set_value("FileWriterMode", "disabled")

    def enable_stream(self):
        self.get_command_object("EnableStream")()

    def disable_stream(self):
        self.get_command_object("DisableStream")()

    def cancel(self):
        self.get_command_object("Cancel")()

    def abort(self):
        self.get_command_object("Abort")()

    def set_monitor(self):
        """
        make sure monitor interface is enabled and discard_new is set to false
        this is used by the beamline monitor interface
        """
        try:
            self.set_value("MonitorMode", "enabled")
            self.set_value("DiscardNew", False)
        except Exception as ex:
            logging.getLogger("HWR").error(
                "[DETECTOR] Couldn't set monitor during init with error {}".format(ex)
            )

    def get_radius(self, distance=None):
        """Get distance from the beam position to the nearest detector edge.
        Args:
            distance (float): Distance [mm]
        Returns:
            (float): Detector radius [mm]
        """
        try:
            distance = (
                distance
                if distance is not None
                else self._distance_motor_hwobj.get_value()
            )
        except AttributeError as err:
            raise RuntimeError("Cannot calculate radius, unknown distance") from err

        beam_x, beam_y = self.get_beam_position(distance)
        pixel_x, pixel_y = self.get_pixel_size()
        # Original
        # rrx = min(self.get_width() - beam_x, beam_x) * pixel_x
        # rry = min(self.get_height() - beam_y, beam_y) * pixel_y
        # radius = min(rrx, rry)

        radius = (
            min(self.get_width() - beam_x, self.get_height() - beam_y, beam_x, beam_y)
            * 0.075
        )

        return radius

    def get_image_file_name(self, path_template, suffix=None):
        # ref-Tau-natA1_1_master.h5
        file_name = f"{path_template.get_prefix()}_{path_template.run_number}_master.h5"
        return file_name

    def get_first_and_last_file(self, pt: PathTemplate) -> tuple[str, str]:
        """
        Get complete path to first and last image

        Args:
          pt (PathTempalte): Path template parameter

        Returns:
        (Tuple): Tuple containing first and last image path (first, last)
        """
        return (pt.get_image_path(), pt.get_image_path())

    def open_cover(self):
        self.cover_hwobj.open()

    def close_cover(self):
        self.cover_hwobj.close()
