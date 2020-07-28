#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Jan Meyer"
__email__ = "jan.meyer@desy.de"
__copyright__ = "(c)2015 DESY, FS-PE, P11"
__license__ = "GPL"


import gevent
import httplib
import json
import logging

# from PyQt4.QtGui import QImage, QPixmap
from gui.utils.QtImport import QImage, QPixmap
from HardwareRepository.HardwareObjects.GenericVideoDevice import GenericVideoDevice
from HardwareRepository.ConvertUtils import string_types


class MjpgStreamVideo(GenericVideoDevice):
    """
    Hardware object to capture images using mjpg-streamer
    and it's input_avt.so plugin for AVT Prosilica cameras.
    """

    # command / control types supported by mjpg-streamer
    CTRL_TYPE_INTEGER = 1
    CTRL_TYPE_BOOLEAN = 2
    CTRL_TYPE_MENU = 3
    CTRL_TYPE_BUTTON = 4

    # command destinations
    DEST_INPUT = 0
    DEST_OUTPUT = 1
    DEST_PROGRAM = 2

    # command groups
    IN_CMD_GROUP_GENERIC = 0
    IN_CMD_GROUP_RESOLUTION = 2
    IN_CMD_GROUP_JPEG_QUALITY = 3
    IN_CMD_GROUP_AVT_MISC = 32
    IN_CMD_GROUP_AVT_INFO = 33
    IN_CMD_GROUP_AVT_EXPOSURE = 34
    IN_CMD_GROUP_AVT_GAIN = 35
    IN_CMD_GROUP_AVT_LENS_DRIVE = 36
    IN_CMD_GROUP_AVT_IRIS = 37
    IN_CMD_GROUP_AVT_WHITE_BALANCE = 38
    IN_CMD_GROUP_AVT_DSP = 39
    IN_CMD_GROUP_AVT_IMAGE_FORMAT = 40
    IN_CMD_GROUP_AVT_IO = 41
    IN_CMD_GROUP_AVT_ACQUISITION = 42
    IN_CMD_GROUP_AVT_CONFIG_FILE = 43
    IN_CMD_GROUP_AVT_NETWORK = 44
    IN_CMD_GROUP_AVT_STATS = 45
    IN_CMD_GROUP_AVT_EVENTS = 46

    # commands
    # note: not every camera supports every command
    # mjpg-streamer only supports integer values for commands
    #   float values are therefore submitted as an integer value * 1000
    #   booleans will only accept 0 or 1
    #   menus have an integer identifier for every item
    #   commands will ignore the given value
    #   strings and events are unsupported yet
    # for more information see the "AVT Camera and Driver Attributes" manual
    IN_CMD_UPDATE_CONTROLS = (1, IN_CMD_GROUP_GENERIC)
    IN_CMD_JPEG_QUALITY = (1, IN_CMD_GROUP_JPEG_QUALITY)
    IN_CMD_AVT_ACQ_END_TRIGGER_EVENT = (6, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_ACQ_END_TRIGGER_MODE = (7, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_ACQ_REC_TRIGGER_EVENT = (8, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_ACQ_REC_TRIGGER_MODE = (9, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_ACQ_START_TRIGGER_EVENT = (10, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_ACQ_START_TRIGGER_MODE = (11, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_ACQUISITION_ABORT = (5, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_ACQUISITION_FRAME_COUNT = (2, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_ACQUISITION_MODE = (1, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_ACQUISITION_START = (3, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_ACQUISITION_STOP = (4, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_BANDWIDTH_CTRL_MODE = (1, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_BINNING_X = (1, IN_CMD_GROUP_AVT_IMAGE_FORMAT)
    IN_CMD_AVT_BINNING_Y = (2, IN_CMD_GROUP_AVT_IMAGE_FORMAT)
    # String 2 IN_CMD_AVT_CAMERA_NAME = (0, IN_CMD_GROUP_AVT_INFO)
    IN_CMD_AVT_CHUNK_MODE_ACTIVE = (2, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_CONFIG_FILE_INDEX = (1, IN_CMD_GROUP_AVT_CONFIG_FILE)
    IN_CMD_AVT_CONFIG_FILE_LOAD = (3, IN_CMD_GROUP_AVT_CONFIG_FILE)
    IN_CMD_AVT_CONFIG_FILE_POWER_UP = (2, IN_CMD_GROUP_AVT_CONFIG_FILE)
    IN_CMD_AVT_CONFIG_FILE_SAVE = (4, IN_CMD_GROUP_AVT_CONFIG_FILE)
    IN_CMD_AVT_DSP_SUBREGION_BOTTOM = (4, IN_CMD_GROUP_AVT_DSP)
    IN_CMD_AVT_DSP_SUBREGION_LEFT = (1, IN_CMD_GROUP_AVT_DSP)
    IN_CMD_AVT_DSP_SUBREGION_RIGHT = (3, IN_CMD_GROUP_AVT_DSP)
    IN_CMD_AVT_DSP_SUBREGION_TOP = (2, IN_CMD_GROUP_AVT_DSP)
    IN_CMD_AVT_DEFECT_MASK_COLUMN_ENABLE = (1, IN_CMD_GROUP_AVT_MISC)
    # String 14 IN_CMD_AVT_DEVICE_ETH_ADDRESS = (0, IN_CMD_GROUP_AVT_NETWORK)
    # String 3 IN_CMD_AVT_DEVICE_FIRMWARE_VERSION = (0, IN_CMD_GROUP_AVT_INFO)
    # String 15 IN_CMD_AVT_DEVICE_IP_ADDRESS = (0, IN_CMD_GROUP_AVT_NETWORK)
    # String 4 IN_CMD_AVT_DEVICE_MODEL_NAME = (0, IN_CMD_GROUP_AVT_INFO)
    # String 5 IN_CMD_AVT_DEVICE_PART_NUMBER = (0, IN_CMD_GROUP_AVT_INFO)
    # String 6 IN_CMD_AVT_DEVICE_SCAN_TYPE = (0, IN_CMD_GROUP_AVT_INFO)
    # String 7 IN_CMD_AVT_DEVICE_SERIAL_NUMBER = (0, IN_CMD_GROUP_AVT_INFO)
    # String 8 IN_CMD_AVT_DEVICE_VENDOR_NAME = (0, IN_CMD_GROUP_AVT_INFO)
    # Event IN_CMD_AVT_EVENT_ACQUISITION_END = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_ACQUISITION_RECORD_TRIGGER = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_ACQUISITION_START = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_ERROR = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_EXPOSURE_END = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_FRAME_TRIGGER = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_NOTIFICATION = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_OVERFLOW = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_SELECTOR = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_SYNC_IN1_FALL = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_SYNC_IN1_RISE = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_SYNC_IN2_FALL = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_SYNC_IN2_RISE = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_SYNC_IN3_FALL = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_SYNC_IN3_RISE = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_SYNC_IN4_FALL = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENT_SYNC_IN4_RISE = (0, IN_CMD_GROUP_AVT_EVENTS)
    # Event IN_CMD_AVT_EVENTS_ENABLE1 = (0, IN_CMD_GROUP_AVT_EVENTS)
    IN_CMD_AVT_EXPOSURE_AUTO_ADJUST_TOL = (3, IN_CMD_GROUP_AVT_EXPOSURE)
    IN_CMD_AVT_EXPOSURE_AUTO_ALG = (4, IN_CMD_GROUP_AVT_EXPOSURE)
    IN_CMD_AVT_EXPOSURE_AUTO_MAX = (5, IN_CMD_GROUP_AVT_EXPOSURE)
    IN_CMD_AVT_EXPOSURE_AUTO_MIN = (6, IN_CMD_GROUP_AVT_EXPOSURE)
    IN_CMD_AVT_EXPOSURE_AUTO_OUTLIERS = (7, IN_CMD_GROUP_AVT_EXPOSURE)
    IN_CMD_AVT_EXPOSURE_AUTO_RATE = (8, IN_CMD_GROUP_AVT_EXPOSURE)
    IN_CMD_AVT_EXPOSURE_AUTO_TARGET = (9, IN_CMD_GROUP_AVT_EXPOSURE)
    IN_CMD_AVT_EXPOSURE_MODE = (2, IN_CMD_GROUP_AVT_EXPOSURE)
    IN_CMD_AVT_EXPOSURE_VALUE = (1, IN_CMD_GROUP_AVT_EXPOSURE)
    IN_CMD_AVT_FIRMWARE_VER_BUILD = (9, IN_CMD_GROUP_AVT_INFO)
    IN_CMD_AVT_FIRMWARE_VER_MAJOR = (10, IN_CMD_GROUP_AVT_INFO)
    IN_CMD_AVT_FIRMWARE_VER_MINOR = (11, IN_CMD_GROUP_AVT_INFO)
    IN_CMD_AVT_FRAMERATE = (12, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_FRAME_START_TRIGGER_DELAY = (14, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_FRAME_START_TRIGGER_EVENT = (15, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_FRAME_START_TRIGGER_MODE = (13, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_FRAME_START_TRIGGER_OVERLAP = (16, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_FRAME_START_TRIGGER_SOFTWARE = (17, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_GAIN_AUTO_ADJUST_TOL = (3, IN_CMD_GROUP_AVT_GAIN)
    IN_CMD_AVT_GAIN_AUTO_MAX = (4, IN_CMD_GROUP_AVT_GAIN)
    IN_CMD_AVT_GAIN_AUTO_MIN = (5, IN_CMD_GROUP_AVT_GAIN)
    IN_CMD_AVT_GAIN_AUTO_OUTLIERS = (6, IN_CMD_GROUP_AVT_GAIN)
    IN_CMD_AVT_GAIN_AUTO_RATE = (7, IN_CMD_GROUP_AVT_GAIN)
    IN_CMD_AVT_GAIN_AUTO_TARGET = (8, IN_CMD_GROUP_AVT_GAIN)
    IN_CMD_AVT_GAIN_MODE = (2, IN_CMD_GROUP_AVT_GAIN)
    IN_CMD_AVT_GAIN_VALUE = (1, IN_CMD_GROUP_AVT_GAIN)
    IN_CMD_AVT_GVSP_LOOKBACK_WINDOW = (18, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_GVSP_RESEND_PERCENT = (19, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_GVSP_RETRIES = (20, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_GVSP_SOCKET_BUFFERS_COUNT = (21, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_GVSP_TIMEOUT = (22, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_HEARTBEAT_INTERVAL = (23, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_HEARTBEAT_TIMEOUT = (24, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_HEIGHT = (6, IN_CMD_GROUP_AVT_IMAGE_FORMAT)
    # String 16 IN_CMD_AVT_HOST_ETH_ADDRESS = (0, IN_CMD_GROUP_AVT_NETWORK)
    # String 17 IN_CMD_AVT_HOST_IP_ADDRESS = (0, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_IRIS_AUTOTARGET = (1, IN_CMD_GROUP_AVT_IRIS)
    IN_CMD_AVT_IRIS_MODE = (2, IN_CMD_GROUP_AVT_IRIS)
    IN_CMD_AVT_IRIS_VIDEO_LEVEL = (3, IN_CMD_GROUP_AVT_IRIS)
    IN_CMD_AVT_IRIS_VIDEO_LEVEL_MAX = (4, IN_CMD_GROUP_AVT_IRIS)
    IN_CMD_AVT_IRIS_VIDEO_LEVEL_MIN = (5, IN_CMD_GROUP_AVT_IRIS)
    IN_CMD_AVT_LENS_DRIVE_COMMAND = (1, IN_CMD_GROUP_AVT_LENS_DRIVE)
    IN_CMD_AVT_LENS_DRIVE_DURATION = (2, IN_CMD_GROUP_AVT_LENS_DRIVE)
    IN_CMD_AVT_LENS_VOLTAGE = (3, IN_CMD_GROUP_AVT_LENS_DRIVE)
    IN_CMD_AVT_LENS_VOLTAGE_CONTROL = (4, IN_CMD_GROUP_AVT_LENS_DRIVE)
    IN_CMD_AVT_MULTICAST_ENABLE = (25, IN_CMD_GROUP_AVT_NETWORK)
    # String 26 IN_CMD_AVT_MULTICAST_IP_ADDRESS = (0, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_NON_IMAGE_PAYLOAD_SIZE = (3, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_PACKET_SIZE = (27, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_PART_CLASS = (12, IN_CMD_GROUP_AVT_INFO)
    IN_CMD_AVT_PART_NUMBER = (13, IN_CMD_GROUP_AVT_INFO)
    # String 14 IN_CMD_AVT_PART_REVISION = (0, IN_CMD_GROUP_AVT_INFO)
    # String 15 IN_CMD_AVT_PART_VERSION = (0, IN_CMD_GROUP_AVT_INFO)
    IN_CMD_AVT_PAYLOAD_SIZE = (4, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_PIXEL_FORMAT = (7, IN_CMD_GROUP_AVT_IMAGE_FORMAT)
    IN_CMD_AVT_RECORDER_PRE_EVENT_COUNT = (18, IN_CMD_GROUP_AVT_ACQUISITION)
    IN_CMD_AVT_REGION_X = (3, IN_CMD_GROUP_AVT_IMAGE_FORMAT)
    IN_CMD_AVT_REGION_Y = (4, IN_CMD_GROUP_AVT_IMAGE_FORMAT)
    IN_CMD_AVT_SENSOR_BITS = (20, IN_CMD_GROUP_AVT_INFO)
    IN_CMD_AVT_SENSOR_HEIGHT = (18, IN_CMD_GROUP_AVT_INFO)
    IN_CMD_AVT_SENSOR_TYPE = (19, IN_CMD_GROUP_AVT_INFO)
    IN_CMD_AVT_SENSOR_WIDTH = (17, IN_CMD_GROUP_AVT_INFO)
    # String 16 IN_CMD_AVT_SERIAL_NUMBER = (0, IN_CMD_GROUP_AVT_INFO)
    IN_CMD_AVT_STAT_DRIVER_TYPE = (1, IN_CMD_GROUP_AVT_STATS)
    # String 2 IN_CMD_AVT_STAT_FILTER_VERSION = (0, IN_CMD_GROUP_AVT_STATS)
    IN_CMD_AVT_STAT_FRAME_RATE = (3, IN_CMD_GROUP_AVT_STATS)
    IN_CMD_AVT_STAT_FRAMES_COMPLETED = (4, IN_CMD_GROUP_AVT_STATS)
    IN_CMD_AVT_STAT_FRAMES_DROPPED = (5, IN_CMD_GROUP_AVT_STATS)
    IN_CMD_AVT_STAT_PACKETS_ERRONEOUS = (6, IN_CMD_GROUP_AVT_STATS)
    IN_CMD_AVT_STAT_PACKETS_MISSED = (7, IN_CMD_GROUP_AVT_STATS)
    IN_CMD_AVT_STAT_PACKETS_RECEIVED = (8, IN_CMD_GROUP_AVT_STATS)
    IN_CMD_AVT_STAT_PACKETS_REQUESTED = (9, IN_CMD_GROUP_AVT_STATS)
    IN_CMD_AVT_STAT_PACKETS_RESENT = (10, IN_CMD_GROUP_AVT_STATS)
    IN_CMD_AVT_STREAM_BYTES_PER_SECOND = (6, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_STREAM_FRAME_RATE_CONSTRAIN = (5, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_STREAM_HOLD_CAPACITY = (8, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_STREAM_HOLD_ENABLE = (7, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_STROBE1_CONTROLLED_DURATION = (1, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_STROBE1_DELAY = (3, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_STROBE1_DURATION = (4, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_STROBE1_MODE = (2, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_SYNC_IN1_GLITCH_FILTER = (5, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_SYNC_IN2_GLITCH_FILTER = (6, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_SYNC_IN_LEVELS = (7, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_SYNC_OUT1_INVERT = (9, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_SYNC_OUT1_MODE = (10, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_SYNC_OUT2_INVERT = (11, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_SYNC_OUT2_MODE = (12, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_SYNC_OUT3_INVERT = (13, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_SYNC_OUT3_MODE = (14, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_SYNC_OUT4_INVERT = (15, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_SYNC_OUT4_MODE = (16, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_SYNC_OUT_GPO_LEVELS = (8, IN_CMD_GROUP_AVT_IO)
    IN_CMD_AVT_TIME_STAMP_FREQUENCY = (9, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_TIME_STAMP_RESET = (13, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_TIME_STAMP_VALUE_HI = (11, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_TIME_STAMP_VALUE_LATCH = (12, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_TIME_STAMP_VALUE_LO = (10, IN_CMD_GROUP_AVT_NETWORK)
    IN_CMD_AVT_TOTAL_BYTES_PER_FRAME = (8, IN_CMD_GROUP_AVT_IMAGE_FORMAT)
    IN_CMD_AVT_UNIQUE_ID = (1, IN_CMD_GROUP_AVT_INFO)
    IN_CMD_AVT_VSUB_VALUE = (2, IN_CMD_GROUP_AVT_MISC)
    IN_CMD_AVT_WHITEBAL_AUTO_ADJUST_TOL = (4, IN_CMD_GROUP_AVT_WHITE_BALANCE)
    IN_CMD_AVT_WHITEBAL_AUTO_RATE = (5, IN_CMD_GROUP_AVT_WHITE_BALANCE)
    IN_CMD_AVT_WHITEBAL_MODE = (3, IN_CMD_GROUP_AVT_WHITE_BALANCE)
    IN_CMD_AVT_WHITEBAL_VALUE_BLUE = (2, IN_CMD_GROUP_AVT_WHITE_BALANCE)
    IN_CMD_AVT_WHITEBAL_VALUE_RED = (1, IN_CMD_GROUP_AVT_WHITE_BALANCE)
    IN_CMD_AVT_WIDTH = (5, IN_CMD_GROUP_AVT_IMAGE_FORMAT)

    def __init__(self, name):
        """
        Descript. :
        """
        GenericVideoDevice.__init__(self, name)
        self.force_update = None
        self.sensor_dimensions = None
        self.image_dimensions = None
        self.image_polling = None
        self.image_type = None
        self.image = None
        self.sleep_time = 1
        self.flip = {"h": False, "v": False}
        self.host = None
        self.port = None
        self.path = "/"
        self.plugin = 0
        self.update_controls = None
        self.input_avt = None

    def init(self):
        """
        Descript. :
        """
        self.sleep_time = self.get_property("interval")
        width = self.get_property("width")
        height = self.get_property("height")
        self.image_dimensions = (width, height)
        self.flip["h"] = bool(self.get_property("fliph"))
        self.flip["v"] = bool(self.get_property("flipv"))
        self.host = self.get_property("host")
        self.port = int(self.get_property("port"))
        self.path = "/"
        self.plugin = 0
        self.update_controls = self.has_update_controls()
        self.input_avt = self.is_input_avt()
        self.image = self.get_new_image()
        if self.input_avt:
            sensor_info = self.get_cmd_info(self.IN_CMD_AVT_SENSOR_WIDTH)
            if sensor_info:
                sensor_width = int(sensor_info["value"])
            sensor_info = self.get_cmd_info(self.IN_CMD_AVT_SENSOR_HEIGHT)
            if sensor_info:
                sensor_height = int(sensor_info["value"])
            self.sensor_dimensions = (sensor_width, sensor_height)
        self.setIsReady(True)

    def http_get(self, query, host=None, port=None, path=None):
        """Sends HTTP GET requests and returns the answer.

        Keyword arguments:
        query -- string appended to the end of the requested URL
        host -- queried IP or hostname (default host of the MjpgStream instance)
        port -- queried port number (default port of the MjpgStream instance)
        path -- queried path (default path of the MjpgStream instance)

        Return value:
        the HTTP answer content or None on error

        """
        if host is None:
            host = self.host
        if port is None:
            port = self.port
        if path is None:
            path = self.path
        # send get request and return response
        http = httplib.HTTPConnection(host, port, timeout=3)
        try:
            http.request("GET", path + query)
            response = http.getresponse()
        except BaseException:
            logging.getLogger().error(
                "MjpgStreamVideo: Connection to http://{0}:{1}{2}{3} refused".format(
                    host, port, path, query
                )
            )
            return None
        if response.status != 200:
            logging.getLogger().error(
                "MjpgStreamVideo: Error {0}, {1}".format(
                    response.status, response.reason
                )
            )
            return None
        data = response.read()
        http.close()
        return data

    def send_cmd(self, value, cmd, group=None, plugin=None, dest=None):
        """Sends a command to mjpg-streamer.

        Keyword arguments:
        value -- command parameter as integer or item name as string if the command is of enumeration type
        cmd -- command id number or tuple constant
        group -- command group number, leave it at None if a tuple is given as cmd (default None)
        plugin -- plugin number (default plugin of the MjpgStream instance)
        dest -- command destination  (default MjpgStream.DEST_INPUT)

        """
        if isinstance(cmd, tuple) and group is None:
            group = cmd[1]
            cmd = cmd[0]
        elif isinstance(cmd, tuple):
            cmd = cmd[0]
        if group is None:
            return None
        cmd = str(int(cmd))
        group = str(int(group))
        try:
            value = str(int(value))
        except BaseException:
            option = value
            value = None
            if isinstance(option, string_types):
                info = self.get_cmd_info(cmd, group)
                if info and "menu" in info and option in info["menu"].values():
                    value = str(
                        [k for k, v in info["menu"].items() if (v == option)][0]
                    )
            if value is None:
                return None
        if plugin is None:
            plugin = str(self.plugin)
        else:
            plugin = str(int(plugin))
        if dest is None:
            dest = str(self.DEST_INPUT)
        else:
            dest = str(int(dest))
        # send request
        self.http_get(
            "?action=command&id="
            + cmd
            + "&dest="
            + dest
            + "&group="
            + group
            + "&value="
            + value
            + "&plugin="
            + plugin
        )

    def has_cmd(self, cmd, group=None, plugin=None, dest=None):
        """Checks whether a command with the given id and group is known by the specified plugin.

        Keyword arguments:
        cmd -- command id number or tuple constant
        group -- command group number, leave it at None if a tuple is given as cmd (default None)
        plugin -- plugin number (default plugin of the MjpgStream instance)
        dest -- command destination  (default MjpgStream.DEST_INPUT)

        Return value:
        True if so, False if not or the connection was refused

        """
        data = self.get_cmd_info(cmd, group, plugin, dest)
        if not data is None:
            return True
        return False

    def get_cmd_info(self, cmd, group=None, plugin=None, dest=None):
        """Returns a dictionary with informations on the queried command.

        Keyword arguments:
        cmd -- command id number or tuple constant
        group -- command group number, leave it at None if a tuple is given as cmd (default None)
        plugin -- plugin number (default plugin of the MjpgStream instance)
        dest -- command destination  (default MjpgStream.DEST_INPUT)

        Return value:
        dictionary containing the following items ("menu" only for menu commands):
        "name", "id", "type", "min", "max", "step", "default", "value", "dest", "flags", "group", "menu"
        or None on error

        """
        if isinstance(cmd, tuple) and group is None:
            group = cmd[1]
            cmd = cmd[0]
        elif isinstance(cmd, tuple):
            cmd = cmd[0]
        if group is None:
            return None
        if plugin is None:
            plugin = self.plugin
        else:
            plugin = str(int(plugin))
        if dest is None or (dest != self.DEST_INPUT and dest != self.DEST_OUTPUT):
            dest = self.DEST_INPUT
        if self.update_controls:
            self.send_cmd(group, self.IN_CMD_UPDATE_CONTROLS, plugin, dest)
        # get list of controls and search for the matching one
        data = self.get_controls(plugin, dest)
        if data is not None:
            for info in data:
                if int(info["group"]) == int(group) and int(info["id"]) == int(cmd):
                    return info
        return None

    def get_controls(self, plugin=None, dest=None):
        """Returns a list with information on all commands supported by the
        plugin. If DEST_PROGRAM is given for dest, a list with information on
        all loaded plugins is returned.

        Keyword arguments:
        plugin -- plugin number (default plugin of the MjpgStream instance)
        dest -- command destination  (default MjpgStream.DEST_INPUT)

        Return value:
        depends on destination plugin. For input_avt.so a list with all commands
        supported by the connected camera is returned - q.v. get_cmd_info().

        """
        if plugin is None:
            plugin = str(self.plugin)
        else:
            plugin = str(int(plugin))
        if dest is None:
            dest = self.DEST_INPUT
        else:
            dest = int(dest)
        query = None
        if dest == self.DEST_INPUT:
            query = "input_" + plugin + ".json"
        elif dest == self.DEST_OUTPUT:
            query = "output_" + plugin + ".json"
        elif dest == self.DEST_PROGRAM:
            query = "program.json"
        # fetch json from server, decode it into a python object and return it
        if query is not None:
            data = self.http_get(query)
            if data is not None:
                data = json.loads(data)
                if dest != self.DEST_PROGRAM and "controls" in data:
                    data = data["controls"]
                return data
        return None

    def has_update_controls(self):
        """Checks if the default plugin for this instance knows the UpdateControls command.

        Return value:
        True if so, False if not and None if the connection was refused

        """
        data = self.get_cmd_info(self.IN_CMD_UPDATE_CONTROLS)
        if data is None:
            return None
        if data["name"] == "UpdateControls":
            return True
        return False

    def is_input_avt(self):
        """Checks if the default plugin for this instance is input_avt.so.

        Return value:
        True if so, False if not and None if the connection was refused

        """
        data = self.get_controls(0, self.DEST_PROGRAM)
        if data is None:
            return None
        if "inputs" in data:
            for info in data["inputs"]:
                if info["name"][-12:] == "input_avt.so":
                    return True
        return False

    def start_camera(self):
        if self.image_polling is None:
            self.image_polling = gevent.spawn(
                self._do_imagePolling, 1.0 / self.sleep_time
            )

    def get_image_dimensions(self):
        return self.image_dimensions

    def imageType(self):
        """
        Descript. :
        """
        return

    def contrast_exists(self):
        """
        Descript. :
        """
        return

    def set_contrast(self, contrast):
        """
        Descript. :
        """
        return

    def get_contrast(self):
        """
        Descript. :
        """
        return

    def set_contrast_auto(self, state=True):
        """
        Descript. :
        """
        return

    def get_contrast_auto(self):
        """
        Descript. :
        """
        return

    def get_contrast_min_max(self):
        """
        Descript. :
        """
        return

    def brightnessExists(self):
        """
        Descript. :
        """
        return

    def set_brightness(self, brightness):
        """
        Descript. :
        """
        return

    def get_brightness(self):
        """
        Descript. :
        """
        return

    def set_brightness_auto(self, state=True):
        """
        Descript. :
        """
        return

    def get_brightness_auto(self):
        """
        Descript. :
        """
        return

    def get_brightness_min_max(self):
        """
        Descript. :
        """
        return

    def gain_exists(self):
        """
        Descript. :
        """
        return self.has_cmd(self.IN_CMD_AVT_GAIN_VALUE)

    def set_gain(self, gain):
        """
        Descript. :
        """
        # self.send_cmd("Manual", self.IN_CMD_AVT_GAIN_MODE) # gain mode manual
        self.send_cmd(gain, self.IN_CMD_AVT_GAIN_VALUE)

    def get_gain(self):
        """
        Descript. :
        """
        info = self.get_cmd_info(self.IN_CMD_AVT_GAIN_VALUE)
        if info is not None:
            return float(info["value"])
        return

    def set_gain_auto(self, state=True):
        """
        Descript. :
        """
        if bool(state):
            self.send_cmd("Auto", self.IN_CMD_AVT_GAIN_MODE)
        else:
            self.send_cmd("Manual", self.IN_CMD_AVT_GAIN_MODE)

    def get_gain_auto(self):
        """
        Descript. :
        """
        value = None
        info = self.get_cmd_info(self.IN_CMD_AVT_GAIN_MODE)
        if info is not None:
            value = info["menu"][info["value"]] == "Auto"
        return value

    def get_gain_min_max(self):
        """
        Descript. :
        """
        info = self.get_cmd_info(self.IN_CMD_AVT_GAIN_VALUE)
        if info is not None:
            return (float(info["min"]), float(info["max"]))
        return

    def gamma_exists(self):
        """
        Descript. :
        """
        return

    def set_gamma(self, gamma):
        """
        Descript. :
        """
        return

    def get_gamma(self):
        """
        Descript. :
        """
        return

    def set_gamma_auto(self, state=True):
        """
        Descript. :
        """
        return

    def get_gamma_auto(self):
        """
        Descript. :
        """
        return

    def get_gamma_min_max(self):
        """
        Descript. :
        """
        return (0, 1)

    def exposure_time_exists(self):
        """
        Descript. :
        """
        return self.has_cmd(self.IN_CMD_AVT_EXPOSURE_VALUE)

    def set_exposure_time(self, gain):
        """
        Descript. :
        """
        # self.send_cmd("Manual", self.IN_CMD_AVT_EXPOSURE_MODE) # gain mode manual
        self.send_cmd(gain, self.IN_CMD_AVT_EXPOSURE_VALUE)

    def get_exposure_time(self):
        """
        Descript. :
        """
        info = self.get_cmd_info(self.IN_CMD_AVT_EXPOSURE_VALUE)
        if info is not None:
            return float(info["value"])
        return

    def set_exposure_time_auto(self, state=True):
        """
        Descript. :
        """
        if bool(state):
            self.send_cmd("Auto", self.IN_CMD_AVT_EXPOSURE_MODE)
        else:
            self.send_cmd("Manual", self.IN_CMD_AVT_EXPOSURE_MODE)

    def get_exposure_time_auto(self):
        """
        Descript. :
        """
        value = None
        info = self.get_cmd_info(self.IN_CMD_AVT_EXPOSURE_MODE)
        if info is not None:
            value = info["menu"][info["value"]] == "Auto"
        return value

    def get_exposure_time_min_max(self):
        """
        Descript. :
        """
        info = self.get_cmd_info(self.IN_CMD_AVT_EXPOSURE_VALUE)
        if info is not None:
            return (float(info["min"]), float(info["max"]))
        return

    def zoom_exists(self):
        """
        Descript. : True if the device supports digital zooming.
        """
        return self.input_avt and self.sensor_dimensions is not None

    def set_zoom(self, zoom):
        """
        Descript. : Sets digital zoom factor.
        """
        limits = self.get_zoom_min_max()
        if zoom < limits[0] or zoom > limits[1]:
            return
        width = self.image_dimensions[0] / zoom
        height = self.image_dimensions[1] / zoom
        pos_x = (self.sensor_dimensions[0] - width) / 2
        pos_y = (self.sensor_dimensions[1] - height) / 2
        self.send_cmd(1, self.IN_CMD_AVT_BINNING_X)
        self.send_cmd(1, self.IN_CMD_AVT_BINNING_Y)
        self.send_cmd(int(pos_x), self.IN_CMD_AVT_REGION_X)
        self.send_cmd(int(pos_y), self.IN_CMD_AVT_REGION_Y)
        self.send_cmd(int(width), self.IN_CMD_AVT_WIDTH)
        self.send_cmd(int(height), self.IN_CMD_AVT_HEIGHT)

    def get_zoom(self):
        """
        Descript. : Returns the digital zoom factor.
        """
        info = self.get_cmd_info(self.IN_CMD_AVT_WIDTH)
        if info is not None:
            return self.image_dimensions[0] / float(info["value"])
        return

    def get_zoom_min_max(self):
        """
        Descript. : Returns the limits for the digital zoom factor.
                    The upper limit is arbitrarily defined.
        """
        return (self.image_dimensions[0] / float(self.sensor_dimensions[0]), 2)

    def setLive(self, mode):
        """
        Descript. :
        """
        return

    def getWidth(self):
        """
        Descript. :
        """
        return self.image_dimensions[0]

    def getHeight(self):
        """
        Descript. :
        """
        return self.image_dimensions[1]

    def get_new_image(self):
        """
        Descript. : reads new image, flips it if necessary and returns the
                    result or None on error
        """
        image = self.http_get("?action=snapshot")
        if image is not None:
            return QImage.fromData(image).mirrored(self.flip["h"], self.flip["v"])
        return None

    def refresh_video(self):
        """
        Descript. : reads new image into member variable, scales it and emits
                    imageReceived event. Added for compatibility.
        """
        image = self.get_new_image()
        if image is not None:
            self.image = QPixmap.fromImage(image.scaled(self.width, self.height))
            self.emit("imageReceived", self.image)

    def take_snapshot(self, filename, bw=False):
        """
        Descript. : calls get_new_image() and saves the result
        """
        try:
            qimage = self.get_new_image()
            # TODO convert to grayscale
            # if bw:
            #    qimage.setNumColors(0)
            qimage.save(filename, "PNG")
        except BaseException:
            logging.getLogger().error(
                "MjpgStreamVideo: unable to save snapshot: %s" % filename
            )

    def _do_imagePolling(self, sleep_time):
        """
        Descript. : worker method
        """
        while True:
            image = self.get_new_image()
            if image is not None:
                self.image = QPixmap.fromImage(image.scaled(self.width, self.height))
                self.emit("imageReceived", self.image)
            gevent.sleep(sleep_time)
