#
#  Project: MXCuBE
#  https://github.com/mxcube
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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""
GenericDiffractometer
"""

import copy
import time
import gevent
import logging
import math
import numpy
from mxcubecore.HardwareObjects import sample_centring
from mxcubecore.HardwareObjects import queue_model_objects
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR

try:
    unicode
except Exception:
    # A quick fix for python3
    unicode = str


__credits__ = ["MXCuBE collaboration"]

__version__ = "2.2."
__status__ = "Draft"


class DiffractometerState:
    """
    Enumeration of diffractometer states
    """

    Created = 0
    Initializing = 1
    On = 2
    Off = 3
    Closed = 4
    Open = 5
    Ready = 6
    Busy = 7
    Moving = 8
    Standby = 9
    Running = 10
    Started = 11
    Stopped = 12
    Paused = 13
    Remote = 14
    Reset = 15
    Closing = 16
    Disable = 17
    Waiting = 18
    Positioned = 19
    Starting = 20
    Loading = 21
    Unknown = 22
    Alarm = 23
    Fault = 24
    Invalid = 25
    Offline = 26

    STATE_DESC = {
        Created: "Created",
        Initializing: "Initializing",
        On: "On",
        Off: "Off",
        Closed: "Closed",
        Open: "Open",
        Ready: "Ready",
        Busy: "Busy",
        Moving: "Moving",
        Standby: "Standby",
        Running: "Running",
        Started: "Started",
        Stopped: "Stopped",
        Paused: "Paused",
        Remote: "Remote",
        Reset: "Reset",
        Closing: "Closing",
        Disable: "Disable",
        Waiting: "Waiting",
        Positioned: " Positioned",
        Starting: "Starting",
        Loading: "Loading",
        Unknown: "Unknown",
        Alarm: "Alarm",
        Fault: "Fault",
        Invalid: "Invalid",
        Offline: "Offline",
    }

    @staticmethod
    def tostring(state):
        return DiffractometerState.STATE_DESC.get(state, "Unknown")


class GenericDiffractometer(HardwareObject):
    """
    Abstract base class for diffractometers
    """

    CENTRING_MOTORS_NAME = [
        "phi",
        "phiz",
        "phiy",
        "sampx",
        "sampy",
        "kappa",
        "kappa_phi",
        "beam_x",
        "beam_y",
    ]

    STATE_CHANGED_EVENT = "stateChanged"
    STATUS_CHANGED_EVENT = "statusChanged"
    MOTOR_POSITION_CHANGED_EVENT = "motorPositionsChanged"
    MOTOR_STATUS_CHANGED_EVENT = "motorStatusChanged"

    HEAD_TYPE_MINIKAPPA = "MiniKappa"
    HEAD_TYPE_SMARTMAGNET = "SmartMagnet"
    HEAD_TYPE_PLATE = "Plate"
    HEAD_TYPE_PERMANENT = "Permanent"

    CENTRING_METHOD_MANUAL = "Manual 3-click"
    CENTRING_METHOD_AUTO = "Computer automatic"
    CENTRING_METHOD_MOVE_TO_BEAM = "Move to beam"

    # TODO NBNB FIX THIS CONFUSION!!!
    MANUAL3CLICK_MODE = CENTRING_METHOD_MANUAL
    C3D_MODE = CENTRING_METHOD_AUTO

    PHASE_TRANSFER = "Transfer"
    PHASE_CENTRING = "Centring"
    PHASE_COLLECTION = "DataCollection"
    PHASE_BEAM = "BeamLocation"
    PHASE_UNKNOWN = "Unknown"

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        # Hardware objects ----------------------------------------------------
        self.motor_hwobj_dict = {}
        self.centring_motors_list = None
        self.front_light_switch = None
        self.back_light_switch = None
        self.aperture = None
        self.beamstop = None
        self.cryo = None
        self.capillary = None
        self.use_sc = False

        # Channels and commands -----------------------------------------------
        self.channel_dict = {}
        self.used_channels_list = []
        self.command_dict = {}
        self.used_commands_list = []

        # flag for using sample_centring hwobj or not
        self.use_sample_centring = None

        # time to delay for state polling for controllers
        # not updating state inmediately after cmd started
        self.delay_state_polling = None

        self.delay_state_polling = (
            None  # time to delay for state polling for controllers
        )
        # not updating state inmediately after cmd started

        # Internal values -----------------------------------------------------
        self.ready_event = None
        self.head_type = GenericDiffractometer.HEAD_TYPE_MINIKAPPA
        self.phase_list = []
        self.grid_direction = None
        self.reversing_rotation = None

        self.beam_position = None
        self.zoom_centre = None
        self.pixels_per_mm_x = None
        self.pixels_per_mm_y = None

        self.current_state = None
        self.current_phase = None
        self.transfer_mode = None
        self.current_centring_procedure = None
        self.current_centring_method = None
        self.current_motor_positions = {}
        self.current_motor_states = {}

        self.fast_shutter_is_open = None
        self.centring_status = {"valid": False}
        self.centring_time = 0
        self.user_confirms_centring = None
        self.user_clicked_event = None
        self.automatic_centring_try_count = 1
        self.omega_reference_par = None
        self.move_to_motors_positions_task = None
        self.move_to_motors_positions_procedure = None

        self.centring_methods = {
            GenericDiffractometer.CENTRING_METHOD_MANUAL: self.start_manual_centring,
            GenericDiffractometer.CENTRING_METHOD_AUTO: self.start_automatic_centring,
            GenericDiffractometer.CENTRING_METHOD_MOVE_TO_BEAM: self.start_move_to_beam,
        }

        self.connect(self, "equipmentReady", self.equipment_ready)
        self.connect(self, "equipmentNotReady", self.equipment_not_ready)

    def init(self):
        # Internal values -----------------------------------------------------
        self.ready_event = gevent.event.Event()
        self.user_clicked_event = gevent.event.AsyncResult()
        self.user_confirms_centring = True

        self.beamstop = self.get_object_by_role("beamstop")
        self.aperture = self.get_object_by_role("aperture")
        self.capillary = self.get_object_by_role("capillary")
        self.cryo = self.get_object_by_role("cryo")

        # Hardware objects ----------------------------------------------------
        # if HWR.beamline.sample_view.camera is not None:
        #     self.image_height = HWR.beamline.sample_view.camera.get_height()
        #     self.image_width = HWR.beamline.sample_view.camera.get_width()
        # else:
        #     logging.getLogger("HWR").debug(
        #         "Diffractometer: " + "Camera hwobj is not defined"
        #     )

        if HWR.beamline.beam is not None:
            self.beam_position = HWR.beamline.beam.get_beam_position_on_screen()
            self.connect(
                HWR.beamline.beam, "beamPosChanged", self.beam_position_changed
            )
        else:
            self.beam_position = [0, 0]
            logging.getLogger("HWR").warning(
                "Diffractometer: " + "BeamInfo hwobj is not defined"
            )

        self.front_light_swtich = self.get_object_by_role("frontlightswtich")
        self.back_light_swtich = self.get_object_by_role("backlightswtich")

        # Channels -----------------------------------------------------------
        ss0 = self.get_property("used_channels")
        if ss0:
            try:
                self.used_channels_list = eval(ss0)
            except Exception:
                pass  # used the default value

        for channel_name in self.used_channels_list:
            self.channel_dict[channel_name] = self.get_channel_object(channel_name)
            if self.channel_dict[channel_name] is None:
                continue
            if channel_name == "TransferMode":
                self.connect(
                    self.channel_dict["TransferMode"],
                    "update",
                    self.transfer_mode_changed,
                )
            elif channel_name == "CurrentPhase":
                self.connect(
                    self.channel_dict["CurrentPhase"],
                    "update",
                    self.current_phase_changed,
                )
            elif channel_name == "HeadType":
                self.connect(
                    self.channel_dict["HeadType"], "update", self.head_type_changed
                )
            elif channel_name == "State":
                self.connect(self.channel_dict["State"], "update", self.state_changed)

        # Commands -----------------------------------------------------------
        try:
            self.used_commands_list = eval(self.get_property("used_commands", "[]"))
        except Exception:
            pass  # used the default value
        for command_name in self.used_commands_list:
            self.command_dict[command_name] = self.get_command_object(command_name)

        # Centring motors ----------------------------------------------------
        try:
            self.centring_motors_list = eval(self.get_property("centring_motors"))
        except Exception:
            self.centring_motors_list = GenericDiffractometer.CENTRING_MOTORS_NAME

        queue_model_objects.CentredPosition.set_diffractometer_motor_names(
            *self.centring_motors_list
        )

        for motor_name in self.centring_motors_list:
            # NBNB TODO refactor configuration, and set properties directly (see below)
            temp_motor_hwobj = self.get_object_by_role(motor_name)
            if temp_motor_hwobj is not None:
                logging.getLogger("HWR").debug(
                    "Diffractometer: Adding "
                    + "%s motor to centring motors" % motor_name
                )

                self.motor_hwobj_dict[motor_name] = temp_motor_hwobj
                self.connect(temp_motor_hwobj, "stateChanged", self.motor_state_changed)
                self.connect(
                    temp_motor_hwobj, "valueChanged", self.centring_motor_moved
                )

                if motor_name == "phi":
                    self.connect(
                        temp_motor_hwobj,
                        "valueChanged",
                        self.emit_diffractometer_moved,
                    )
                elif motor_name == "zoom":
                    self.connect(
                        temp_motor_hwobj,
                        "predefinedPositionChanged",
                        self.zoom_motor_predefined_position_changed,
                    )
                    self.connect(
                        temp_motor_hwobj, "stateChanged", self.zoom_motor_state_changed
                    )
            else:
                logging.getLogger("HWR").warning(
                    "Diffractometer: Motor "
                    + "%s listed in the centring motor list, but not initalized"
                    % motor_name
                )

        # sample changer -----------------------------------------------------
        if HWR.beamline.sample_changer is None:
            logging.getLogger("HWR").warning(
                "Diffractometer: Sample Changer is not defined"
            )
        else:
            # By default use sample changer if it's defined and transfer_mode
            # is set to SAMPLE_CHANGER.
            # if not defined, set use_sc to True
            if self.transfer_mode is None or self.transfer_mode == "SAMPLE_CHANGER":
                self.use_sc = True

        try:
            self.use_sample_centring = self.get_property("sample_centring")
            if self.use_sample_centring:
                self.centring_phi = sample_centring.CentringMotor(
                    self.motor_hwobj_dict["phi"], direction=-1
                )
                self.centring_phiz = sample_centring.CentringMotor(
                    self.motor_hwobj_dict["phiz"]
                )
                self.centring_phiy = sample_centring.CentringMotor(
                    self.motor_hwobj_dict["phiy"], direction=-1
                )
                self.centring_sampx = sample_centring.CentringMotor(
                    self.motor_hwobj_dict["sampx"]
                )
                self.centring_sampy = sample_centring.CentringMotor(
                    self.motor_hwobj_dict["sampy"]
                )
        except Exception:
            pass  # used the default value

        try:
            self.delay_state_polling = self.get_property("delay_state_polling")
        except Exception:
            pass

        # Other parameters ---------------------------------------------------
        try:
            self.zoom_centre = eval(self.get_property("zoom_centre"))
        except Exception:
            self.zoom_centre = {"x": 0, "y": 0}
            logging.getLogger("HWR").warning(
                "Diffractometer: " + "zoom centre not configured"
            )

        self.reversing_rotation = self.get_property("reversing_rotation")
        try:
            # grid_direction describes how a grid is collected
            # 'fast' is collection direction and 'slow' describes
            # move to the next collection line
            self.grid_direction = eval(self.get_property("grid_direction"))
        except Exception:
            self.grid_direction = {"fast": (0, 1), "slow": (1, 0), "omega_ref": 0}
            logging.getLogger("HWR").warning(
                "Diffractometer: Grid " + "direction is not defined. Using default."
            )

        try:
            self.phase_list = eval(self.get_property("phase_list"))
        except Exception:
            self.phase_list = [
                GenericDiffractometer.PHASE_TRANSFER,
                GenericDiffractometer.PHASE_CENTRING,
                GenericDiffractometer.PHASE_COLLECTION,
                GenericDiffractometer.PHASE_BEAM,
            ]

    # to make it compatibile
    def __getattr__(self, attr):
        if attr.startswith("__"):
            raise AttributeError(attr)
        else:
            if attr == "currentCentringProcedure":
                return self.current_centring_procedure
            if attr == "centringStatus":
                return self.centring_status
            if attr == "imageClicked":
                return self.image_clicked
            if attr == "cancelCentringMethod":
                return self.cancel_centring_method
            if attr == "pixelsPerMmY":
                return self.pixels_per_mm_x
            if attr == "pixelsPerMmZ":
                return self.pixels_per_mm_y
            return HardwareObject.__getattr__(self, attr)

    # Contained Objects
    # NBNB Temp[orary hack - should be cleaned up together with configuration
    @property
    def omega(self):
        """omega motor object

        Returns:
            AbstractActuator
        """
        return self.motor_hwobj_dict.get("phi")

    @property
    def kappa(self):
        """kappa motor object

        Returns:
            AbstractActuator
        """
        return self.motor_hwobj_dict.get("kappa")

    @property
    def kappa_phi(self):
        """kappa_phi motor object

        Returns:
            AbstractActuator
        """
        return self.motor_hwobj_dict.get("kappa_phi")

    @property
    def centring_x(self):
        """centring_x motor object

        Returns:
            AbstractActuator
        """
        return self.motor_hwobj_dict.get("sampx")

    @property
    def centring_y(self):
        """centring_y motor object

        Returns:
            AbstractActuator
        """
        return self.motor_hwobj_dict.get("sampy")

    @property
    def alignment_x(self):
        """alignment_x motor object (also used as graphics.focus)

        Returns:
            AbstractActuator
        """
        return self.motor_hwobj_dict.get("focus")

    @property
    def alignment_y(self):
        """alignment_y motor object

        Returns:
            AbstractActuator
        """
        return self.motor_hwobj_dict.get("phiy")

    @property
    def alignment_z(self):
        """alignment_z motor object

        Returns:
            AbstractActuator
        """
        return self.motor_hwobj_dict.get("phiz")

    @property
    def zoom(self):
        """zoom motor object

        NBNB HACK TODO - ocnfigure this in graphics object
        (which now calls this property)

        Returns:
            AbstractActuator
        """
        return self.motor_hwobj_dict.get("zoom")

    def is_ready(self):
        """
        Detects if device is ready
        """
        return self.current_state == DiffractometerState.tostring(
            DiffractometerState.Ready
        )

    def wait_device_not_ready(self, timeout=5):
        with gevent.Timeout(timeout, Exception("Timeout waiting for device not ready")):
            while self.is_ready():
                time.sleep(0.01)

    def wait_device_ready(self, timeout=30):
        """ Waits when diffractometer status is ready:

        :param timeout: timeout in second
        :type timeout: int
        """
        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while not self.is_ready():
                time.sleep(0.01)

    def execute_server_task(self, method, timeout=30, *args):
        """Method is used to execute commands and wait till
           diffractometer is in ready state

        :param method: method to be executed
        :type method: instance
        :param timeout: timeout in seconds
        :type timeout: seconds
        """
        # self.ready_event.clear()
        self.current_state = DiffractometerState.tostring(DiffractometerState.Busy)
        method(*args)
        time.sleep(5)
        # gevent.sleep(2)
        self.wait_device_ready(timeout)
        self.ready_event.set()

    def in_plate_mode(self):
        """Returns True if diffractometer in plate mod

        :returns: boolean
        """
        return self.head_type == GenericDiffractometer.HEAD_TYPE_PLATE

    def get_head_type(self):
        """Returns head type

        :returns: string
        """
        return self.head_type

    def use_sample_changer(self):
        """Returns True if sample changer is in use

        :returns: boolean
        """
        return self.use_sc

    def set_use_sc(self, flag):
        """Sets use_sc flag, that indicates if sample changer is used

        :param flag: use sample changer flag
        :type flag: boolean
        """
        if flag:
            # check both transfer_mode and sample_Changer
            if HWR.beamline.sample_changer is None:
                logging.getLogger("HWR").error(
                    "Diffractometer: Sample " + "Changer is not available"
                )
                return False

            if (
                self.transfer_mode is None
                or self.channel_dict["TransferMode"].get_value() == "SAMPLE_CHANGER"
            ):
                # if transferMode is not defined, ignore the checkup
                self.use_sc = True
            else:
                logging.getLogger("HWR").error(
                    "Diffractometer: Set the "
                    + "diffractometer TransferMode to SAMPLE_CHANGER first!!"
                )
                return False
        else:
            self.use_sc = False
        return True

    def transfer_mode_changed(self, transfer_mode):
        """
        Descript. :
        """
        logging.getLogger("HWR").info(
            "current_transfer_mode is set to %s" % transfer_mode
        )
        self.transfer_mode = transfer_mode
        if transfer_mode != "SAMPLE_CHANGER":
            self.use_sc = False
        self.emit("minidiffTransferModeChanged", (transfer_mode,))

    def get_transfer_mode(self):
        """
        """
        return self.transfer_mode

    def get_current_phase(self):
        """
        Descript. :
        """
        return self.current_phase

    def get_grid_direction(self):
        """
        Descript. :
        """
        return self.grid_direction

    def get_available_centring_methods(self):
        """
        Descript. :
        """
        return self.centring_methods.keys()

    def get_current_centring_method(self):
        """
        Descript. :
        """
        return self.current_centring_method

    def is_reversing_rotation(self):
        """
        """
        return self.reversing_rotation is True

    def beam_position_changed(self, value):
        """
        Descript. :
        """
        self.beam_position = list(value)

    # def get_motor_positions(self):
    #    return

    # TODO rename to get_motor_positions
    def get_positions(self):
        """
        Descript. :
        """

        self.current_motor_positions["beam_x"] = (
            self.beam_position[0] - self.zoom_centre["x"]
        ) / self.pixels_per_mm_y
        self.current_motor_positions["beam_y"] = (
            self.beam_position[1] - self.zoom_centre["y"]
        ) / self.pixels_per_mm_x

        return self.current_motor_positions

    # def get_omega_position(self):
    #     """
    #     Descript. :
    #     """
    #     return self.current_positions_dict.get("phi")

    def get_snapshot(self):
        if HWR.beamline.sample_view:
            return HWR.beamline.sample_view.take_snapshot()

    def save_snapshot(self, filename):
        """
        """
        if HWR.beamline.sample_view:
            return HWR.beamline.sample_view.save_snapshot(filename)

    def get_pixels_per_mm(self):
        """
        Returns tuple with pixels_per_mm_x and pixels_per_mm_y

        :returns: list with two floats
        """
        return (self.pixels_per_mm_x, self.pixels_per_mm_y)

    def get_phase_list(self):
        """
        Returns list of available phases

        :returns: list with str
        """
        return self.phase_list

    def start_centring_method(self, method, sample_info=None, wait=False):
        """
        """

        if self.current_centring_method is not None:
            logging.getLogger("HWR").error(
                "Diffractometer: already in centring method %s"
                % self.current_centring_method
            )
            return
        curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.centring_status = {
            "valid": False,
            "startTime": curr_time,
            "angleLimit": None,
        }
        self.emit_centring_started(method)

        try:
            centring_method = self.centring_methods[method]
        except KeyError as diag:
            logging.getLogger("HWR").error(
                "Diffractometer: unknown centring method (%s)" % str(diag)
            )
            self.emit_centring_failed()
        else:
            try:
                centring_method(sample_info, wait_result=wait)
            except Exception:
                logging.getLogger("HWR").exception(
                    "Diffractometer: problem while centring"
                )
                self.emit_centring_failed()

    def cancel_centring_method(self, reject=False):
        """
        """

        if self.current_centring_procedure is not None:
            try:
                self.current_centring_procedure.kill()
            except Exception:
                logging.getLogger("HWR").exception(
                    "Diffractometer: problem aborting the centring method"
                )
            try:
                # TODO... do we need this at all?
                # fun = self.cancel_centring_methods[self.current_centring_method]
                pass
            except KeyError:
                self.emit_centring_failed()
            else:
                try:
                    fun()
                except Exception:
                    self.emit_centring_failed()
        else:
            self.emit_centring_failed()
        self.emit_progress_message("")
        if reject:
            self.reject_centring()

    def start_manual_centring(self, sample_info=None, wait_result=None):
        """
        """
        self.emit_progress_message("Manual 3 click centring...")
        if self.use_sample_centring:
            self.current_centring_procedure = sample_centring.start(
                {
                    "phi": self.centring_phi,
                    "phiy": self.centring_phiy,
                    "sampx": self.centring_sampx,
                    "sampy": self.centring_sampy,
                    "phiz": self.centring_phiz,
                },
                self.pixels_per_mm_x,
                self.pixels_per_mm_y,
                self.beam_position[0],
                self.beam_position[1],
            )
        else:
            self.current_centring_procedure = gevent.spawn(self.manual_centring)
        self.current_centring_procedure.link(self.centring_done)

    def start_automatic_centring(
        self, sample_info=None, loop_only=False, wait_result=None
    ):
        """
        """
        self.emit_progress_message("Automatic centring...")

        while self.automatic_centring_try_count > 0:
            if self.use_sample_centring:
                self.current_centring_procedure = sample_centring.start_auto(
                    HWR.beamline.sample_view.camera,
                    {
                        "phi": self.centring_phi,
                        "phiy": self.centring_phiy,
                        "sampx": self.centring_sampx,
                        "sampy": self.centring_sampy,
                        "phiz": self.centring_phiz,
                    },
                    self.pixels_per_mm_x,
                    self.pixels_per_mm_y,
                    self.beam_position[0],
                    self.beam_position[1],
                    msg_cb=self.emit_progress_message,
                    new_point_cb=lambda point: self.emit(
                        "newAutomaticCentringPoint", (point,)
                    ),
                )
            else:
                self.current_centring_procedure = gevent.spawn(self.automatic_centring)
            self.current_centring_procedure.link(self.centring_done)

            if wait_result:
                self.ready_event.wait()
                self.ready_event.clear()

            self.automatic_centring_try_count -= 1
        self.automatic_centring_try_count = 1

    def start_move_to_beam(
        self, coord_x=None, coord_y=None, omega=None, wait_result=None
    ):
        """
        Descript. :
        """
        try:
            self.emit_progress_message("Move to beam...")
            self.centring_time = time.time()
            curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.centring_status = {
                "valid": True,
                "startTime": curr_time,
                "endTime": curr_time,
            }
            if coord_x is None and coord_y is None:
                coord_x = self.beam_position[0]
                coord_y = self.beam_position[1]

            motors = self.get_centred_point_from_coord(
                coord_x, coord_y, return_by_names=True
            )
            if omega is not None:
                motors["phi"] = omega

            self.centring_status["motors"] = motors
            self.centring_status["valid"] = True
            self.centring_status["angleLimit"] = True
            self.emit_progress_message("")
            self.accept_centring()
            self.current_centring_method = None
            self.current_centring_procedure = None
        except Exception:
            logging.exception("Diffractometer: Could not complete 2D centring")

    def centring_done(self, centring_procedure):
        """
        Descript. :
        """
        try:
            motor_pos = centring_procedure.get()
            if isinstance(motor_pos, gevent.GreenletExit):
                raise motor_pos
        except Exception:
            logging.exception("Could not complete centring")
            self.emit_centring_failed()
        else:
            self.emit_progress_message("Moving sample to centred position...")
            self.emit_centring_moving()

            try:
                logging.getLogger("HWR").debug(
                    "Centring finished. Moving motoros to position %s" % str(motor_pos)
                )
                self.move_to_motors_positions(motor_pos, wait=True)
            except Exception:
                logging.exception("Could not move to centred position")
                self.emit_centring_failed()
            else:
                # if 3 click centring move -180. well. dont, in principle the calculated
                # centred positions include omega to initial position
                pass
                # if not self.in_plate_mode():
                #    logging.getLogger("HWR").debug("Centring finished. Moving omega back to initial position")
                #    self.motor_hwobj_dict['phi'].set_value_relative(-180, timeout=None)
                #    logging.getLogger("HWR").debug("         Moving omega done")

            if (
                self.current_centring_method
                == GenericDiffractometer.CENTRING_METHOD_AUTO
            ):
                self.emit("newAutomaticCentringPoint", motor_pos)
            self.ready_event.set()
            self.centring_time = time.time()
            self.emit_centring_successful()
            self.emit_progress_message("")

    def manual_centring(self):
        """
        """
        raise NotImplementedError

    def automatic_centring(self):
        """
        """
        raise NotImplementedError

    def centring_motor_moved(self, pos):
        """
        """
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def invalidate_centring(self):
        """
        """
        if self.current_centring_procedure is None and self.centring_status["valid"]:
            self.centring_status = {"valid": False}
            self.emit_progress_message("")
            self.emit("centringInvalid", ())

    def emit_diffractometer_moved(self, *args):
        """
        """
        self.emit("diffractometerMoved", ())

    def motor_positions_to_screen(self, centred_positions_dict):
        """
        """
        if self.use_sample_centring:
            self.update_zoom_calibration()
            if None in (self.pixels_per_mm_x, self.pixels_per_mm_y):
                return 0, 0
            phi_angle = math.radians(
                self.centring_phi.direction * self.centring_phi.get_value()
            )
            sampx = self.centring_sampx.direction * (
                centred_positions_dict["sampx"] - self.centring_sampx.get_value()
            )
            sampy = self.centring_sampy.direction * (
                centred_positions_dict["sampy"] - self.centring_sampy.get_value()
            )
            phiy = self.centring_phiy.direction * (
                centred_positions_dict["phiy"] - self.centring_phiy.get_value()
            )
            phiz = self.centring_phiz.direction * (
                centred_positions_dict["phiz"] - self.centring_phiz.get_value()
            )
            rot_matrix = numpy.matrix(
                [
                    math.cos(phi_angle),
                    -math.sin(phi_angle),
                    math.sin(phi_angle),
                    math.cos(phi_angle),
                ]
            )
            rot_matrix.shape = (2, 2)
            inv_rot_matrix = numpy.array(rot_matrix.I)
            dx, dy = (
                numpy.dot(numpy.array([sampx, sampy]), inv_rot_matrix)
                * self.pixels_per_mm_x
            )

            x = (phiy * self.pixels_per_mm_x) + self.beam_position[0]
            y = dy + (phiz * self.pixels_per_mm_y) + self.beam_position[1]

            return x, y
        else:
            raise NotImplementedError

    def move_to_centred_position(self, centred_position):
        """
        """
        self.move_motors(centred_position)

    def move_to_motors_positions(self, motors_positions, wait=False):
        """
        """
        self.emit_progress_message("Moving to motors positions...")
        self.move_to_motors_positions_procedure = gevent.spawn(
            self.move_motors, motors_positions
        )
        self.move_to_motors_positions_procedure.link(self.move_motors_done)
        if wait:
            self.wait_device_ready(10)

    def move_motors(self, motor_positions, timeout=15):
        """
        Moves diffractometer motors to the requested positions

        :param motors_dict: dictionary with motor names or hwobj
                            and target values.
        :type motors_dict: dict
        """
        if not isinstance(motor_positions, dict):
            motor_positions = motor_positions.as_dict()

        self.wait_device_ready(timeout)

        for motor in motor_positions.keys():
            position = motor_positions[motor]
            """
            if isinstance(motor, (str, unicode)):
                logging.getLogger("HWR").debug(" Moving %s to %s" % (motor, position))
            else:
                logging.getLogger("HWR").debug(
                    " Moving %s to %s" % (str(motor.name()), position)
                )
            """
            if isinstance(motor, (str, unicode)):
                motor_role = motor
                motor = self.motor_hwobj_dict.get(motor_role)
                # del motor_positions[motor_role]
                if None in (motor, position):
                    continue
                # motor_positions[motor] = position
            motor.set_value(position)
        self.wait_device_ready(timeout)

        if self.delay_state_polling is not None and self.delay_state_polling > 0:
            # delay polling for state in the
            # case of controller not reporting MOVING inmediately after cmd
            gevent.sleep(self.delay_state_polling)

        self.wait_device_ready(timeout)

    def move_motors_done(self, move_motors_procedure):
        """
        Descript. :
        """
        self.move_to_motors_positions_procedure = None
        self.emit_progress_message("")

    def move_to_beam(self, x, y, omega=None):
        """
        Descript. : function to create a centring point based on all motors
                    positions.
        """
        try:
            pos = self.get_centred_point_from_coord(x, y, return_by_names=False)
            if omega is not None:
                pos["phiMotor"] = omega
            self.move_to_motors_positions(pos)
        except Exception:
            logging.getLogger("HWR").exception(
                "Diffractometer: could not center to beam, aborting"
            )

    def image_clicked(self, x, y, xi=None, yi=None):
        """
        Descript. :
        """
        if self.use_sample_centring:
            sample_centring.user_click(x, y)
        else:
            self.user_clicked_event.set((x, y))

    def accept_centring(self):
        """
        Descript. :
        Arg.      " fully_centred_point. True if 3 click centring
                    else False
        """
        self.centring_status["valid"] = True
        self.centring_status["accepted"] = True
        centring_status = self.get_centring_status()
        if "motors" not in centring_status:
            centring_status["motors"] = self.get_positions()
        self.emit("centringAccepted", (True, centring_status))
        self.emit("fsmConditionChanged", "centering_position_accepted", True)

    def reject_centring(self):
        """
        Descript. :
        """
        if self.current_centring_procedure:
            self.current_centring_procedure.kill()
        self.centring_status = {"valid": False}
        self.emit_progress_message("")
        self.emit("centringAccepted", (False, self.get_centring_status()))
        self.emit("fsmConditionChanged", "centering_position_accepted", False)

    def emit_centring_started(self, method):
        """
        Descript. :
        """
        self.current_centring_method = method
        self.emit("centringStarted", (method, False))

    def emit_centring_moving(self):
        """
        Descript. :
        """
        self.emit("centringMoving", ())

    def emit_centring_failed(self):
        """
        Descript. :
        """
        self.centring_status = {"valid": False}
        method = self.current_centring_method
        self.current_centring_method = None
        self.current_centring_procedure = None
        self.emit("centringFailed", (method, self.get_centring_status()))

    def emit_centring_successful(self):
        """
        Descript. :
        """
        if self.current_centring_procedure is not None:
            curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.centring_status["endTime"] = curr_time

            motor_pos = self.current_centring_procedure.get()
            self.centring_status["motors"] = self.convert_from_obj_to_name(motor_pos)
            self.centring_status["method"] = self.current_centring_method
            self.centring_status["valid"] = True

            method = self.current_centring_method
            self.emit("centringSuccessful", (method, self.get_centring_status()))
            self.current_centring_method = None
            self.current_centring_procedure = None
        else:
            logging.getLogger("HWR").debug(
                "Diffractometer: Trying to emit "
                + "centringSuccessful outside of a centring"
            )

    def emit_progress_message(self, msg=None):
        """
        Descript. :
        """
        self.emit("progressMessage", (msg,))

    def get_centring_status(self):
        """
        Descript. :
        """
        return copy.deepcopy(self.centring_status)

    def get_centred_point_from_coord(self):
        """
        """
        raise NotImplementedError

    def get_point_between_two_points(
        self, point_one, point_two, frame_num, frame_total
    ):
        """
        Method returns a centring point between two centring points
        It is used to get a position on a helical line based on
        frame number and total frame number
        """
        new_point = {}
        point_one = point_one.as_dict()
        point_two = point_two.as_dict()
        for motor in point_one.keys():
            new_motor_pos = (
                frame_num
                / float(frame_total)
                * abs(point_one[motor] - point_two[motor])
                + point_one[motor]
            )
            new_motor_pos += 0.5 * (point_two[motor] - point_one[motor]) / frame_total
            new_point[motor] = new_motor_pos
        return new_point

    def convert_from_obj_to_name(self, motor_pos):
        """
        """
        motors = {}
        for motor_role in self.centring_motors_list:
            motor_obj = self.get_object_by_role(motor_role)
            try:
                motors[motor_role] = motor_pos[motor_obj]
            except KeyError:
                if motor_obj:
                    motors[motor_role] = motor_obj.get_value()
        motors["beam_x"] = (
            self.beam_position[0] - self.zoom_centre["x"]
        ) / self.pixels_per_mm_y
        motors["beam_y"] = (
            self.beam_position[1] - self.zoom_centre["y"]
        ) / self.pixels_per_mm_x
        return motors

    def visual_align(self, point_1, point_2):
        """
        Descript. :
        """
        return

    def move_omega_relative(self, relative_angle):
        """
        Descript. :
        """
        return

    def get_osc_limits(self):
        """Returns osc limits"""
        return

    def get_osc_max_speed(self):
        return

    def get_scan_limits(self, speed=None, num_images=None, exp_time=None):
        """
        Gets scan limits. Necessary for example in the plate mode
        where osc range is limited
        """
        return

    def set_phase(self, phase, timeout=None):
        """Sets diffractometer to selected phase
           By default available phase is Centring, BeamLocation,
           DataCollection, Transfer

        :param phase: phase
        :type phase: string
        :param timeout: timeout in sec
        :type timeout: int
        """
        if timeout:
            self.ready_event.clear()
            set_phase_task = gevent.spawn(
                self.execute_server_task,
                self.command_dict["startSetPhase"],
                timeout,
                phase,
            )
            self.ready_event.wait()
            self.ready_event.clear()
        else:
            self.command_dict["startSetPhase"](phase)

    def update_zoom_calibration(self):
        """
        """
        self.pixels_per_mm_x = 1.0 / self.channel_dict["CoaxCamScaleX"].get_value()
        self.pixels_per_mm_y = 1.0 / self.channel_dict["CoaxCamScaleY"].get_value()
        self.emit("pixelsPerMmChanged", ((self.pixels_per_mm_x, self.pixels_per_mm_y)))

    def zoom_motor_state_changed(self, state):
        """
        """
        self.emit("zoomMotorStateChanged", (state,))
        self.emit("minidiffStateChanged", (state,))

    def zoom_motor_predefined_position_changed(self, position_name, offset):
        """
        """
        self.update_zoom_calibration()
        self.emit("zoomMotorPredefinedPositionChanged", (position_name, offset))

    def equipment_ready(self):
        """
        """
        self.emit("minidiffReady", ())

    def equipment_not_ready(self):
        """
        """
        self.emit("minidiffNotReady", ())

    """
    def state_changed(self, state):
        logging.getLogger("HWR").debug("State changed %s" % str(state))
        self.current_state = state
        self.emit("minidiffStateChanged", (self.current_state))
    """

    def motor_state_changed(self, state):
        """
        Descript. :
        """
        self.emit("minidiffStateChanged", (state,))

    def current_phase_changed(self, current_phase):
        """
        Descript. :
        """
        self.current_phase = current_phase
        if current_phase != GenericDiffractometer.PHASE_UNKNOWN:
            logging.getLogger("GUI").info(
                "Diffractometer: Current phase changed to %s" % current_phase
            )
        self.emit("minidiffPhaseChanged", (current_phase,))

    def sample_is_loaded_changed(self, sample_is_loaded):
        """
        Descript. :
        """
        self.sample_is_loaded = sample_is_loaded
        # logging.getLogger("HWR").info("sample is loaded changed %s" % sample_is_loaded)
        self.emit("minidiffSampleIsLoadedChanged", (sample_is_loaded,))

    def head_type_changed(self, head_type):
        """
        Descript. :
        """
        self.head_type = head_type
        # logging.getLogger("HWR").info("new head type is %s" % head_type)
        self.emit("minidiffHeadTypeChanged", (head_type,))

        if "SampleIsLoaded" not in str(self.used_channels_list):
            return
        try:
            self.disconnect(
                self.channel_dict["SampleIsLoaded"],
                "update",
                self.sample_is_loaded_changed,
            )
        except Exception:
            pass

        if (
            head_type == GenericDiffractometer.HEAD_TYPE_MINIKAPPA
            or head_type == GenericDiffractometer.HEAD_TYPE_SMARTMAGNET
        ):
            self.connect(
                self.channel_dict["SampleIsLoaded"],
                "update",
                self.sample_is_loaded_changed,
            )
        else:
            logging.getLogger("HWR").info(
                "Diffractometer: SmartMagnet "
                + "is not available, only works for Minikappa and SmartMagnet head"
            )

    def move_kappa_and_phi(self, kappa, kappa_phi):
        return

    def close_kappa(self):
        """
        Descript. :
        """
        return

    def get_osc_dynamic_limits(self):
        return (-10000, 10000)

    def get_osc_max_speed(self):
        """
        """
        return None
        # raise NotImplementedError

    def zoom_in(self):
        return

    def zoom_out(self):
        return

    def save_centring_positions(self):
        pass
