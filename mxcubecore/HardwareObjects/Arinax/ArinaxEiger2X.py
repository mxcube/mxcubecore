"""
Eiger 2X Detector control hardware object.

USe SIMPLON Web Server REST API
Structure derived from BIOMAXEiger
"""
import json
import requests
import sys
import getopt
import gevent
import time
import copy
import logging

__author__ = "Bernard Lavault and Daniel Homs - ARINAX"
__credits__ = ["The MxCuBE collaboration"]

__email__ = ""
__status__ = "Beta"

from mxcubecore.TaskUtils import task, cleanup, error_cleanup
from mxcubecore.HardwareObjects.abstract.AbstractDetector import AbstractDetector
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore import HardwareRepository as HWR

class ArinaxEiger2X(AbstractDetector, HardwareObject):
    """
    Description: Eiger2X hwobj based on SIMPLON
    """

    def __init__(self, name):
        """
        Descrip. :
        """
        AbstractDetector.__init__(self, name)
        HardwareObject.__init__(self, name)

        self.device = None
        self.file_suffix = None
        self.default_exposure_time = 0.1
        self.default_compression = "bslz4"
        self.buffer_limit = None
        self.dcu = None
        self.config_state = None
        self.initialized = False
        self.status_chan = None
        self.roi_mode = "disabled"
        self.photon_energy = 12000
        self.energy_threshold = 6000
        self.distance_motor_hwobj = None
        self.energy_change_threshold = 10000
        self.energy_change_threshold_default = 20
        self.col_config = None
        self.trigger_mode = "ints" # software trigger by default
        self.det_ip_address = None
        self.URL = None
        self.api_version = "1.8.0"
        self.readout_time = 0.0000001
        self.x_pixel_size_mm = 0.000075
        self.y_pixel_size_mm = 0.000075
        self.minimum_exposure_time = 0.0000002
        self._previous_state = None

        #        cmd_list = (
    #        "Arm",
    #        "Trigger",
    #        "Abort",
    #        "Cancel",
    #        "ClearBuffer",
    #        "DeleteFileFromBuffer",
    #        "Disarm",
    #        "DownloadFilesFromBuffer",
    #        "EnableStream",
    #        "DisableStream",
    #    )

    def init(self):

        AbstractDetector.init(self)
        HardwareObject.init(self)

        self.distance_motor_hwobj = self.get_object_by_role("distance_motor")
        self.file_suffix = self.get_property("file_suffix")
        self.default_exposure_time = self.get_property("default_exposure_time")
        self.default_compression = self.get_property("default_compression")
        self.buffer_limit = self.get_property("buffer_limit")
        self.dcu = self.get_property("dcu")
        self.det_ip_address = self.get_property("det_ip_address") # 10.30.51.152
        self.api_version = self.get_property("api_version")
        self.trigger_mode = self.get_property("trigger_mode") # can be inte, ints, exte, exts
        self.URL = "http://" + self.det_ip_address + "/%s/api/" + self.api_version + "/%s"

        # config needed to be set up for data collection
        # if values are None, use the one from the system
        self.col_config = {
            "omega_start": 0,
            "omega_increment": 0.1,
            "beam_center_x": 2000,  # length not pixel
            "beam_center_y": 2000,
            "detector_distance": 0.15,
            "count_time": 0.1,
            "nimages": 100,
            "ntrigger": 1,
            "nimages_per_file": {"value": 1, "api_name": "filewriter"},
            "roi_mode": "disabled",
            "name_pattern": {"value": "test", "api_name": "filewriter"},
            "photon_energy": 12000,
            "trigger_mode": "exts",
        }

        # we need to call the init device before accessing the channels here
        #   otherwise the initialization is triggered by the HardwareRepository Poller
        #   that is delayed after the application starts

        try:
            self.energy_change_threshold = float(
                self.get_property("min_trigger_energy_change")
            )
        except Exception:
            self.energy_change_threshold = self.energy_change_threshold_default

        # Some parameters can be set only once since they never change on the fly
        self.set_config("compression", "bslz4")
        self.set_config("trigger_mode", self.trigger_mode)

        # Some parameters can be read only once since they never change
        self.readout_time = self.read_config("detector_readout_time")
        self.x_pixel_size_mm = self.read_config("x_pixel_size") * 1000
        self.y_pixel_size_mm = self.read_config("y_pixel_size") * 1000
        self.minimum_exposure_time = self.get_readout_time()  # TODO use self.read_config_min_val("frame_time") instead
        self._emit_status()
        if self.URL is not None:
            self.pollingTask = gevent.spawn(self._do_polling)

    @property
    def status(self):
        try:
            acq_status = self.get_detector_status()
        except Exception:
            acq_status = "exc"

        status = {"acq_satus": acq_status.upper()}

        return status

    def _emit_status(self):
        try:
            self.emit("statusChanged", (self.status,))
        except:
            raise("error emiting detector status")

    def poll_state(self):
        self.current_state = self.get_detector_status()
        if self.current_state == self._previous_state:
            return
        else:
            self._previous_state = self.current_state
        self._emit_status()

    def _do_polling(self):
        while True:
            try:
                self.poll_state()
            except Exception as ex:
                self.log.error("[Eiger Detector] Exception retrieving Detector status: ", ex)
            time.sleep(0.1)

    def send_data(self, url, dict_data=None):
        if dict_data is not None:
            data_json = json.dumps(dict_data)
            rep = requests.put(url, data=data_json)
        else:
            rep = requests.put(url)

        return rep

    def get_json_data(self, url):
        data_json = requests.get(url)
        return json.loads(data_json.content), data_json.status_code

    def read_value(self, full_param_name, api_name="detector"):
        url = self.URL % (api_name, full_param_name)
        r, status_code = self.get_json_data(url)
        ret_type = r['value_type']
        value = r['value']

        if status_code != 200:
            raise ValueError

        if ret_type == 'float':
            return float(value)
        elif ret_type == 'int':
            return int(value)
        else:
            return value

    def read_config(self, param_name, api_name="detector"):
        return self.read_value('config/' + param_name, api_name)

    def read_status(self, param_name, api_name="detector"):
        return self.read_value('status/' + param_name, api_name)

    def read_min_value(self, full_param_name, api_name="detector"):
        url = self.URL % (api_name, full_param_name)
        r, status_code = self.get_json_data(url)
        ret_type = r['value_type']
        value = r['min']

        if status_code != 200:
            raise ValueError

        if ret_type == 'float':
            return float(value)
        elif ret_type == 'int':
            return int(value)
        else:
            return value

    def set_config(self, param_name, value, api_name="detector"):
        url = self.URL % (api_name, "config/" + param_name)
        dict_data = {'value': value}
        r = self.send_data(url, dict_data)

        if r.status_code != 200:
            logging.getLogger("HWR").info("[DETECTOR] %s set %s=%s, return code: %s" % (
            api_name, param_name, str(value), get_ret_str(r.status_code)))
            raise ValueError

        logging.getLogger("HWR").info("[DETECTOR] %s set %s=%s" % (api_name, param_name, str(value)))


    def is_exte_enabled(self):
        return self.trigger_mode == "exte"

    def send_command(self, cmd_name, str_arg=None, api_name="detector"):
        """ Do a PUT on the REST API associated with command execution
            Args:
                str_arg None or a string with the name of the parameter
                api_name: one of the Following: "detector" , "filewriter" , "stream", "monitor", "system"
            Return: None
            Except: ValueError if the command has not been executed properly
        """
        url = self.URL % (api_name, "command/" + cmd_name)

        if str_arg is None:
            dict_data = None
        else:
            dict_data = {'value': str_arg}

        r = self.send_data(url, dict_data)

        logging.getLogger("HWR").info("[DETECTOR] command %s, return code: %s, new state: %s"
                                      % (cmd_name, get_ret_str(r.status_code), self.get_detector_status()))
        if r.status_code != 200:
            raise ValueError

    def is_software_trigger(self):
        return self.trigger_mode.find("int") >= 0  # return configuration, not detector value

    #  STATUS , status can be "idle", "ready", "UNKNOWN"
    def get_detector_status(self):
        return self.read_value('status/state')

    def is_idle(self):
        return self.get_detector_status() == "idle"

    def is_ready(self):
        return self.get_detector_status() == "ready"

    def is_acquire(self):
        return self.get_detector_status() == "acquire"

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
                gevent.sleep(0.25)

    def wait_ready_or_idle(self):
        with gevent.Timeout(20, RuntimeError("Detector neither ready or idle")):
            while not (self.is_ready() or self.is_idle()):
                logging.getLogger("HWR").debug(
                    "Waiting for the detector to be ready, current state: "
                    + self.get_detector_status()
                )
                gevent.sleep(0.25)

    def wait_idle(self):
        with gevent.Timeout(20, RuntimeError("Detector not idle")):
            while not self.is_idle():
                gevent.sleep(0.25)

    def wait_acquire(self):
        with gevent.Timeout(20, RuntimeError("Detector did not start acquisition")):
            while not self.is_acquire():
                gevent.sleep(0.25)

    def get_state(self):
        """Get the motor state.
        Returns:
            (enum HardwareObjectState): Motor state.
        """
        # return self.distance_motor_hwobj.get_state()
        return HardwareObjectState.READY

    def get_distance(self):
        """
        Descript. :
        """
        if self.distance_motor_hwobj is not None:
            return self.distance_motor_hwobj.getPosition()
        else:
            return self.default_distance

    def get_limits(self):
        """
        Descript.
        """
        return 0, 900
        # TODO Implement limits in Motor HardwareObject using A info on the PV distance
        # if self.distance_motor_hwobj is not None:
        #     return self.distance_motor_hwobj.get_limits()
        # else:
        #     return self.default_distance_limits

    def get_readout_time(self):
        return self.readout_time

    def get_acquisition_time(self):
        return self.read_config('frame_time')  # return 2

    def wait_buffer_ready(self):
        if self.buffer_limit is not None:
            with gevent.Timeout(
                20, RuntimeError("Detector free buffer size is lower than limit")
            ):
                while self.get_buffer_free() < self.buffer_limit:
                    gevent.sleep(0.25)

    def get_buffer_free(self):
        """Returns the remaining buffer space in Bytes
        """
        return self.read_status("buffer_free", "filewriter")

    def get_roi_mode(self):
        return self.roi_mode

    def set_roi_mode(self, value):
        self.roi_mode = value

    def get_pixel_size_x(self):
        """
        return sizes of a single pixel along x-axis respectively
        unit, mm
        """

        return self.x_pixel_size_mm

    def get_pixel_size_y(self):
        """
        return sizes of a single pixel along y-axis respectively
        unit, mm
        """
        return self.y_pixel_size_mm

    def get_x_pixels_in_detector(self):
        """
        number of pixels along x-axis
        numbers vary depending on the RoiMode
        """
        return self.read_config("x_pixels_in_detector")  # 4148

    def get_y_pixels_in_detector(self):
        """
        number of pixels along y-axis,
        numbers vary depending on the RoiMode
        """
        return self.read_config("y_pixels_in_detector")  # 4362

    def get_minimum_exposure_time(self):
        return self.minimum_exposure_time

    def get_sensor_thickness(self):
        return 0.45

    def has_shutterless(self):
        return True

    def get_collection_uuid(self):
        # TODO check if there is an implementation of this
        # return self.get_channel_value("CollectionUUID")
        return 'noUUID'

    def get_header_detail(self):
        """
    Detail of header data to be sent.
        """
        return self.read_config("header_detail")

    def get_header_appendix(self):
        """
        Data that is appended to the header data
        """
        return self.read_config("header_appendix")

    def get_image_appendix(self):
        """
        Data that is appended to the image data
        """
        return self.get_channel_value("ImageAppendix")

    def get_stream_state(self):
        """
        "disabled", "ready", "acquire" or "error".
        """
        return self.get_channel_value("StreamState")

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
            self.set_config('photon_energy', energy)
            return True

    def _validate_energy_value(self, energy):
        try:
            target_energy = float(energy)
        except Exception:
            # not a valid value
            logging.getLogger("user_level_log").info("Wrong Energy value: %s" % energy)
            return -1

        # TODO : get min max of photon_energy
        max_energy = energy + 100  # self.get_channel_value("PhotonEnergyMax")
        min_energy = energy - 100  # self.get_channel_value("PhotonEnergyMin")
        current_energy = self.read_config("photon_energy")

        print("   - currently configured energy is: %s" % current_energy)
        print("   -    min val: %s / max val: %s " % (min_energy, max_energy))

        if target_energy < min_energy or target_energy > max_energy:
            print("Energy value out of limits: %s" % energy)
            logging.getLogger("user_level_log").info(
                "Energy value out of limits: %s" % energy
            )
            return -1

        if abs(energy - current_energy) > self.energy_change_threshold:
            print("Energy difference over threshold. program energy necessary")
            return 1
        else:
            print("Energy difference below threshold. Do not need to program")
            return 0

    def get_latency_time(self):
        return float(self.get_property("latency_time"))

    def set_energy_threshold(self, threshold):
        """
        set energy_threshold
        Note, the readout_time will be changed
        By deafult, the value is 50% of the photon_energy and will be
        updated upon setting PhotonEnergy. If other values are needed,
        this should be set after changing PhotonEnergy.
        Eengery, in eV
        """
        self.set_config('threshold/1/energy', threshold)  # TODO : check what to do with second threshold

    def set_collection_uuid(self, col_uuid):
        # TODO check if there is equivalent  UUID with this API
        # self.set_channel_value("CollectionUUID", col_uuid)
        pass

    def set_header_detail(self, value):
        """
        Detail of header data to be sent.
        """
        if value not in ["all", "basic", "none"]:
            logging.getLogger("HWR").error("Cannot set stream header detail")
            return
        self.set_config("header_details", value, "stream")

    def set_header_appendix(self, value):
        """
        Data that is appended to the header data
        """
        self.set_config("header_appendix", value, "stream")

    def set_image_appendix(self, value):
        """
        Data that is appended to the image data
        """
        self.set_config("image_appendix", value, "stream")


    def set_roi_mode(self, value):
        if value not in ["16M", "disabled"]:
            logging.getLogger("HWR").error("Cannot set stream header detail")
            return
        self.set_config('RoiMode', value)

    #  SET VALUES END

    def wait_config_done(self):
        # TODO Method for managing the waiting for detector ready
        # is the return 200 enough ?
        pass

    def prepare_acquisition(self, config):
        """
        config is a dictionary with all parameters { param_name1 : value1, param_name2 : value2 }
        default API is "detector" . In order to force another API
        the value must be a dictionnary specifying a special interface:
        {"value":XXX, "api_name": "AAAAA"}  AAAA is "filewriter" or "detector" or "stream"
        """
        logging.getLogger("user_level_log").info("Preparing acquisition")
        self.disarm()  # to be sure that it is not waiting for another series

        for k, v in config.items():
            if isinstance(v, dict):
                self.set_config(k, v["value"], v["api_name"])
            else:
                self.set_config(k, v)

        self.read_config("wavelength")
        self.set_config("nimages_per_file", 1, "filewriter")  #  TODO remove this line to enable configuration from


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
            RuntimeError("Detector should be idle before starting a new acquisition")

        self.config_state = None

        logging.getLogger("user_level_log").info("Detector going to arm")
        self.arm()

        if self.is_software_trigger():
            logging.getLogger("user_level_log").info("Sending trigger to detector")
            self.soft_trigger()

    def stop_acquisition(self):
        """
        Stops gently the data acquisition, only after the current image is finished.
        when use external trigger, Disarm is required, otherwise the last h5 will
        not be released and not available in WebDAV.
        """

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
        except Exception:
            pass

    def cancel_acquisition(self):
        """Cancel acquisition"""
        logging.getLogger("HWR").info("[DETECTOR] Cancelling acquisition")
        try:
            self.cancel()
        except Exception:
            pass

        time.sleep(1)
        self.disarm()

    def arm(self):
        self.send_command("arm")
        self.wait_ready()
        logging.getLogger("user_level_log").info("Detector armed")

    def soft_trigger(self, count_time=-1):
        if count_time > 0:
            return self.send_command('trigger', str(count_time))
        else:
            return self.send_command('trigger')

    def get_file_list(self):
        """Returns the list of collected files
         """
        try:
            list = self.read_status("files", "filewriter")
        except ValueError:
            list = []

        return list

    def disarm(self):
        self.send_command("disarm")
        logging.getLogger("HWR").info("[DETECTOR] waiting end of acquisition...")
        self.wait_idle()   # TODO check if it should be wait_ready_or_idle()

    def enable_stream(self):
        # TODO implement self.get_command_object("EnableStream")()
        pass

    def disable_stream(self):
        # TODO implement  self.get_command_object("DisableStream")()
        pass

    def clear(self):
        self.send_command("clear", str_arg=None, api_name="filewriter")

    def cancel(self):
        """Stops the data acquisition,but only after the current image is finished.
        """
        return self.send_command("cancel")

    def abort(self):
        """Aborts all operations and resets the systemim-mediately. All data in the pipeline will be dropped.
        """
        return self.send_command("abort")

    def initialize(self):
        self.send_command("initialize")
        self.send_command("initialize", "filewriter")


def get_ret_str(status_code):
    """Convert the REST API return code into a string for traces purpose
    """
    if status_code == 200:
        return "OK"
    else:
        return "failed (err %d)" % status_code

# Method used by mxcube_test to test the hardware object, it receives a hardware object to test (hwo)
def test_hwo(hwo):
    hwo.clear()
    hwo.stop_acquisition()
    hwo.get_detector_status()
    hwo.read_min_value("config/frame_time")
    config = {
        "counting_mode": "normal",
        "frame_time": 1.2,
        "nimages": 1,
        "ntrigger": 1,
        "count_time": 0.99,
        "mode": {"value": "enabled", "api_name": "filewriter"},
        "name_pattern": {"value": "arinax_test", "api_name": "filewriter"},
        "compression_enabled": {"value": "True", "api_name": "filewriter"},
        "image_nr_start": {"value": 1, "api_name": "filewriter"},
        "nimages_per_file": {"value": 1, "api_name": "filewriter"},
    }
    # hwo.prepare_acquisition(config)
    hwo.get_acquisition_time()
    hwo.get_buffer_free()
    hwo.get_x_pixels_in_detector()
    hwo.get_y_pixels_in_detector()
    #hwo.start_acquisition()
    #time.sleep(30)
    #hwo.disarm()
    collected_images = (hwo.get_file_list())
