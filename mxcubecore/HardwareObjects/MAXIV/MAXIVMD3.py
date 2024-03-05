import time
import logging
import gevent
import numpy as np
from PIL import Image

try:
    import lucid_core as lucid
except ModuleNotFoundError:
    logging.getLogger("HWR").warning("[MAXIVMD3] Lucid cannot be imported.")
from mxcubecore.HardwareObjects.GenericDiffractometer import (
    GenericDiffractometer,
    DiffractometerState,
)
from mxcubecore import HardwareRepository as HWR

from gevent import monkey

monkey.patch_all(thread=False)

MONITORING_INTERVAL = 0.1
DEFAULT_TASK_TIMEOUT = 200
DEFAULT_TASK_RUNNING_TIMEOUT = 2
ARRAY_SEPARATOR = ""
# 0x001F


class MAXIVMD3(GenericDiffractometer):
    """Diffractometer calss to control motors and functoinality of MD3"""

    MOTOR_TO_EXPORTER_NAME = {
        "focus": "AlignmentX",
        "kappa": "Kappa",
        "kappa_phi": "Phi",
        "phi": "Omega",
        "phiy": "AlignmentY",
        "phiz": "AlignmentZ",
        "sampx": "CentringX",
        "sampy": "CentringY",
        "zoom": "Zoom",
    }

    AUTOMATIC_CENTRING_IMAGES = 6

    def __init__(self, name):
        """
        Description:
        """
        GenericDiffractometer.__init__(self, name=name)
        # Compatibility line
        self.C3D_MODE = GenericDiffractometer.CENTRING_METHOD_AUTO
        self.MANUAL3CLICK_MODE = "Manual 3-click"
        self.last_centered_position = None

    def init(self):

        GenericDiffractometer.init(self)

        self.front_light = self.get_object_by_role("frontlight")
        self.back_light = self.get_object_by_role("backlight")
        self.back_light_switch = self.get_object_by_role("backlightswitch")
        self.front_light_switch = self.get_object_by_role("frontlightswitch")
        self.fluodet = self.get_object_by_role("fluodet")
        self.rex = self.get_object_by_role("rex")

        self.centring_hwobj = self.get_object_by_role("centring")
        if self.centring_hwobj is None:
            logging.getLogger("HWR").debug(
                "MAXIVMinidiff: Centring math is not defined"
            )

        try:
            self.beamstop_z = self.get_object_by_role("beamstop_z")
        except:
            self.beamstop_z = None

        # to make it comaptible
        self.motors_hwobj_dict = self.motor_hwobj_dict  # making sampleView happy
        self.wait_device_ready = self.wait_ready
        self.acceptCentring = self.accept_centring
        self.startCentringMethod = self.start_centring_method

        self.phi_motor_hwobj = self.motor_hwobj_dict["phi"]
        self.phiz_motor_hwobj = self.motor_hwobj_dict["phiz"]
        self.phiy_motor_hwobj = self.motor_hwobj_dict["phiy"]
        self.zoom_motor_hwobj = self.motor_hwobj_dict["zoom"]
        self.focus_motor_hwobj = self.motor_hwobj_dict["focus"]
        self.sample_x_motor_hwobj = self.motor_hwobj_dict["sampx"]
        self.sample_y_motor_hwobj = self.motor_hwobj_dict["sampy"]
        try:
            self.kappa_motor_hwobj = self.motor_hwobj_dict["kappa"]
        except:
            self.kappa_motor_hwobj = None
        try:
            self.kappa_phi_motor_hwobj = self.motor_hwobj_dict["kappa_phi"]
        except:
            self.kappa_phi_motor_hwobj = None

        self.beam_info_hwobj = self.get_object_by_role("beam_info")

        self.cent_vertical_pseudo_motor = None
        try:
            self.cent_vertical_pseudo_motor = self.add_channel(
                {"type": "exporter", "name": "CentringTableVerticalPositionPosition"},
                "CentringTableVerticalPosition",
            )
            if self.cent_vertical_pseudo_motor is not None:
                self.connect(
                    self.cent_vertical_pseudo_motor, "update", self.centring_motor_moved
                )
        except:
            logging.getLogger("HWR").warning(
                "Cannot initialize CentringTableVerticalPosition"
            )

        try:
            self.fast_shutter_channel = self.add_channel(
                {"type": "exporter", "name": "FastShutterIsOpen"}, "FastShutterIsOpen"
            )
        except:
            logging.getLogger("HWR").exception(
                "Cannot initialize diffractometer Fast Shutter"
            )

        try:
            use_sc = self.get_property("use_sc")
            self.set_use_sc(use_sc)
        except:
            logging.getLogger("HWR").debug("Cannot set sc mode, use_sc: ", str(use_sc))

    ## ------------------------------- ##
    ##      TASK ID MANAGEMENT         ##
    ## ------------------------------- ##

    def waitTaskResult(self, task_id=-1, timeout=DEFAULT_TASK_TIMEOUT):
        logging.getLogger("HWR").info(
            "[MAXIVMD3] Waiting task result, task_id %s" % str(task_id)
        )
        if task_id < 0:
            self.wait_device_ready(timeout)
            info = self.get_last_task_info()
            exception = info[5]
            if (exception != "") and (exception != "null"):
                raise exception
            return info[4]
        else:
            with gevent.Timeout(
                timeout, Exception("Timeout waiting for task to finish")
            ):
                while self.is_task_running(task_id):
                    gevent.sleep(MONITORING_INTERVAL)
            return self.get_task_info(task_id)

    def waitTaskIsRunning(self, task_id=-1, timeout=DEFAULT_TASK_RUNNING_TIMEOUT):
        logging.getLogger("HWR").info(
            "[MAXIVMD3] Waiting task is runnning, task_id %s" % str(task_id)
        )
        # removed the none task_id code
        with gevent.Timeout(timeout, Exception("Timeout waiting for task to start")):
            while not self.is_task_running(task_id):
                # make sure task is not launched due to exception
                task_info = self.get_task_info(task_id)
                task_exception, task_result = task_info[5:7]
                if (
                    task_result != "null" and int(task_result) < 0
                ):  # failed with exception
                    raise RuntimeError(
                        "MD3 Oscillation failed: exception: %s |result: %s"
                        % (task_exception, task_result)
                    )
                gevent.sleep(MONITORING_INTERVAL)
        task_info = self.get_task_info(task_id)

        logging.getLogger("HWR").info(
            "[MAXIVMD3] Task is runnning, task_id, %s" % str(task_info)
        )
        return task_info

    def is_task_running(self, task_id):
        return self.command_dict["isTaskRunning"](task_id)

    def get_task_result(self, task_id):
        # Positive = success, Negative = failure, 0 = aborted
        result = self.command_dict["checkTaskResult"](task_id)
        return int(result)

    def get_task_info(self, task_id):
        """
        Returns an array of string containing task information
        """
        return self.command_dict["getTaskInfo"](task_id)

    def get_last_task_info(self):
        """
        Returns an array of string containing task information
        corresponding to the last task
        """
        # ['Set Transfer Phase',
        # '8',
        # '2021-05-03 14:22:23.061',
        # '2021-05-03 14:22:24.533',
        # 'true',
        # 'null',
        # '1']
        return self.channel_dict["LastTaskInfo"].get_value()

    ## ------------------------------- ##
    ##      OPERATION                  ##
    ## ------------------------------- ##

    def current_phase_changed(self, current_phase):
        """
        Descript. :
        """
        self.current_phase = current_phase
        logging.getLogger("HWR").info("MD3 phase changed to %s" % current_phase)
        self.emit("phaseChanged", (current_phase,))

    def get_transfer_mode(self):
        """
        Returns the MD3 TRANSFER MODE config
        """
        try:
            mode = self.channel_dict["TransferMode"].get_value()
        except Exception as ex:
            logging.getLogger("HWR").error("Cannot get MD3 transfer mode %s " % ex)
            raise Exception("Cannot get MD3 transfer mode %s " % ex)
        return mode

    def is_fast_shutter_open(self):
        return self.fast_shutter_channel.get_value()

    def state_changed(self, state):
        logging.getLogger("HWR").debug("State changed %s" % str(state))
        self.current_state = state
        self.emit("minidiffStateChanged", (self.current_state))

    def motor_state_changed(self, state):
        """
        Descript. :
        """
        self.emit("minidiffStateChanged", (state,))

    def open_fast_shutter(self):
        logging.getLogger("HWR").info("Openning fast shutter")
        self.fast_shutter_channel.set_value(True)

    def close_fast_shutter(self):
        logging.getLogger("HWR").info("Closing fast shutter")
        self.fast_shutter_channel.set_value(False)

    def move_fluo_in(self, wait=True):
        logging.getLogger("HWR").info("Moving Fluo detector in")
        self.wait_device_ready(3)
        self.fluodet.actuatorIn()
        time.sleep(3)  # MD3 reports long before fluo is in position
        # the next lines are irrelevant, leaving there for future use
        if wait:
            with gevent.Timeout(10, Exception("Timeout waiting for fluo detector In")):
                while self.fluodet.get_actuator_state(read=True) != "in":
                    gevent.sleep(0.1)

    def move_fluo_out(self, wait=True):
        logging.getLogger("HWR").info("Moving Fluo detector out")
        self.wait_device_ready(3)
        self.fluodet.actuatorOut()
        if wait:
            with gevent.Timeout(10, Exception("Timeout waiting for fluo detector Out")):
                while self.fluodet.get_actuator_state(read=True) != "out":
                    gevent.sleep(0.1)

    def set_scintillator_pos(self, value):
        """
        Set scintillator position
        """
        try:
            self.channel_dict["ScintillatorPosition"].set_value(value)
            self.wait_device_ready(30)
        except Exception as ex:
            logging.getLogger("HWR").exception(
                "Cannot set MD3 scintillator %s to %s " % (ex, value)
            )

    def get_capillary_vertical_pos(self):
        """
        get capillary vertical position
        """
        try:
            return self.channel_dict["CapillaryVerticalPosition"].get_value()
        except Exception as ex:
            logging.getLogger("HWR").error(
                "Cannot get MD3 capillary vertcial %s " % (ex)
            )

    def get_sample_holder_length(self):
        """
        get sample holder length
        """
        try:
            return self.channel_dict["SampleHolderLength"].get_value()
        except Exception as ex:
            logging.getLogger("HWR").error("Cannot get MD3 %s value" % (ex))

    def set_sample_holder_length(self, value):
        """
        set sample holder length
        """
        try:
            return self.channel_dict["SampleHolderLength"].set_value(value)
        except Exception as ex:
            logging.getLogger("HWR").error("Cannot set MD3 %s to %s " % (ex, value))

    ## ------------------------------- ##
    ##      SAMPLE CENTRING             ##
    ## ------------------------------- ##

    def find_loop(self):
        """
        Description:
        """

        self.camera = HWR.beamline.sample_view.camera
        img_buf, w, h = self.camera.get_image_array()

        try:
            img = img_buf.reshape(h, w, 3)
            img_rot = np.rot90(img, 1)
            info, y, x = lucid.find_loop_array(
                img_rot, IterationClosing=6
            )  # np.array(img_rot, order='C'), IterationClosing=6)
            x = w - x
        except:
            return -1, -1, 0
        if info == "Coord":
            surface_score = 10
            return x, y, surface_score
        else:
            return -1, -1, 0

    def start_3_click_centring(self):
        self.start_centring_method(self.CENTRING_METHOD_MANUAL)

    def start_auto_centring(self):
        self.start_centring_method(self.CENTRING_METHOD_AUTO)

    def get_pixels_per_mm(self):
        """
        Get the values from coaxCamScaleX and coaxCamScaleY channels diretly

        :returns: list with two floats
        """
        zoom = HWR.beamline.sample_view.camera.get_image_zoom()
        return (
            zoom / self.channel_dict["CoaxCamScaleX"].get_value(),
            1 / self.channel_dict["CoaxCamScaleY"].get_value(),
        )

    def update_zoom_calibration(self):
        """ """
        zoom = HWR.beamline.sample_view.camera.get_image_zoom()
        self.pixels_per_mm_x = zoom / self.channel_dict["CoaxCamScaleX"].get_value()
        self.pixels_per_mm_y = zoom / self.channel_dict["CoaxCamScaleY"].get_value()
        self.emit("pixelsPerMmChanged", ((self.pixels_per_mm_x, self.pixels_per_mm_y)))

    def manual_centring(self):
        """
        Descript. :
        """
        self.update_zoom_calibration()

        self.centring_hwobj.initCentringProcedure()
        for click in range(3):
            self.user_clicked_event = gevent.event.AsyncResult()
            x, y = self.user_clicked_event.get()
            self.centring_hwobj.appendCentringDataPoint(
                {
                    "X": (x - self.beam_position[0]) / self.pixels_per_mm_x,
                    "Y": (y - self.beam_position[1]) / self.pixels_per_mm_y,
                }
            )
            if self.in_plate_mode():
                dynamic_limits = self.phi_motor_hwobj.get_dynamic_limits()
                if click == 0:
                    self.phi_motor_hwobj.set_value(dynamic_limits[0])
                elif click == 1:
                    self.phi_motor_hwobj.set_value(dynamic_limits[1])
            else:
                if click < 2:
                    self.phi_motor_hwobj.set_value_relative(90)
        self.omega_reference_add_constraint()
        cpos = self.centring_hwobj.centeredPosition(return_by_name=False)
        return cpos

    def automatic_centring(self):
        self.wait_device_ready(10)
        # move MD3 to Centring phase if it's not
        if self.get_current_phase() != "Centring":
            logging.getLogger("user_level_log").info(
                "Moving Diffractometer to Centring for automatic_centring"
            )
            self.set_phase("Centring", wait=True, timeout=200)
        # wait shortly to make sure the camera exposure time is set for the right phase
        time.sleep(1)
        centred_pos = self.do_automatic_centring(2)
        self.zoom_motor_hwobj.move_to_position("Zoom 4")
        self.wait_device_ready(3)
        return centred_pos

    def do_automatic_centring(self, cycle=3):
        """Automatic centring procedure. Rotates n times and executes
        centring algorithm. Optimal scan position is detected.
        """
        time_out = 3
        # check if loop is there at the beginning
        i = 0
        while -1 in self.find_loop():
            self.phi_motor_hwobj.set_value_relative(90)
            self.wait_ready(time_out)
            i += 1
            if i > 4:
                self.emit_progress_message("No loop detected, aborting")
                return

        for k in range(cycle):
            self.emit_progress_message("Doing automatic centring")
            surface_score_list = []
            self.centring_hwobj.initCentringProcedure()
            for a in range(3):
                x, y, score = self.find_loop()
                if x < 0 or y < 0:
                    for i in range(1, 6):
                        self.phi_motor_hwobj.set_value_relative(15)
                        self.wait_ready(time_out)
                        x, y, score = self.find_loop()
                        surface_score_list.append(score)
                        if -1 in (x, y):
                            continue
                        if y >= 0:
                            if x < self.image_width / 2:
                                x = 0
                                self.centring_hwobj.appendCentringDataPoint(
                                    {
                                        "X": (x - self.beam_position[0])
                                        / self.pixels_per_mm_x,
                                        "Y": (y - self.beam_position[1])
                                        / self.pixels_per_mm_y,
                                    }
                                )
                                break
                            else:
                                x = self.image_width
                                self.centring_hwobj.appendCentringDataPoint(
                                    {
                                        "X": (x - self.beam_position[0])
                                        / self.pixels_per_mm_x,
                                        "Y": (y - self.beam_position[1])
                                        / self.pixels_per_mm_y,
                                    }
                                )
                                break
                    if -1 in (x, y):
                        raise RuntimeError("Could not centre sample automatically.")
                    self.phi_motor_hwobj.set_value_relative(-i * 15)
                    self.wait_ready(time_out)
                else:
                    self.centring_hwobj.appendCentringDataPoint(
                        {
                            "X": (x - self.beam_position[0]) / self.pixels_per_mm_x,
                            "Y": (y - self.beam_position[1]) / self.pixels_per_mm_y,
                        }
                    )
                self.phi_motor_hwobj.set_value_relative(90)
                self.wait_ready(time_out)

            self.omega_reference_add_constraint()
            centred_pos = self.centring_hwobj.centeredPosition(return_by_name=False)
            if k < 2:
                self.move_to_centred_position(centred_pos)
                self.wait_ready(time_out)
        return centred_pos

    def omega_reference_add_constraint(self):
        """
        Descript. :
        """
        if self.omega_reference_par is None or self.beam_position is None:
            return
        if self.omega_reference_par["camera_axis"].lower() == "x":
            on_beam = (
                self.beam_position[0] - self.zoom_centre["x"]
            ) * self.omega_reference_par[
                "direction"
            ] / self.pixels_per_mm_x + self.omega_reference_par[
                "position"
            ]
        else:
            on_beam = (
                self.beam_position[1] - self.zoom_centre["y"]
            ) * self.omega_reference_par[
                "direction"
            ] / self.pixels_per_mm_y + self.omega_reference_par[
                "position"
            ]
        self.centring_hwobj.appendMotorConstraint(self.omega_reference_motor, on_beam)

    def omega_reference_motor_moved(self, pos):
        """
        Descript. :
        """
        if self.omega_reference_par["camera_axis"].lower() == "x":
            pos = (
                self.omega_reference_par["direction"]
                * (pos - self.omega_reference_par["position"])
                * self.pixels_per_mm_x
                + self.zoom_centre["x"]
            )
            self.reference_pos = (pos, -10)
        else:
            pos = (
                self.omega_reference_par["direction"]
                * (pos - self.omega_reference_par["position"])
                * self.pixels_per_mm_y
                + self.zoom_centre["y"]
            )
            self.reference_pos = (-10, pos)
        self.emit("omegaReferenceChanged", (self.reference_pos,))

    def refresh_omega_reference_position(self):
        """
        Descript. :
        """
        if self.omega_reference_motor is not None:
            reference_pos = self.omega_reference_motor.getPosition()
            self.omega_reference_motor_moved(reference_pos)

    def move_cent_vertical_relative(self, value=0):
        cent_vertical_to_move = self.cent_vertical_pseudo_motor.get_value() + value
        motor_limits = self.command_dict["getMotorDynamicLimits"](
            "CentringTableVertical"
        )
        if (
            cent_vertical_to_move > motor_limits[1]
            or cent_vertical_to_move < motor_limits[0]
        ):
            msg = "Target position is beyond the centering motor limits"
            logging.getLogger("HWR").error(msg)
            raise Exception(msg)
        self.wait_device_ready(5)
        self.cent_vertical_pseudo_motor.set_value(cent_vertical_to_move)
        self.wait_device_ready(5)

    def move_to_omega_reference_pos(self):
        pos = self.omega_reference_par["position"]
        self.omega_reference_motor.move(pos)

    def set_scan_number_of_passes(self, value):
        self.wait_device_ready(5)
        self.channel_dict["ScanNumberOfPasses"].set_value(value)
        self.wait_device_ready(5)

    def set_scan_number_of_frames(self, value):
        self.wait_device_ready(5)
        self.channel_dict["ScanNumberOfFrames"].set_value(value)
        self.wait_device_ready(5)

    def zoom_position_changed(self, value):
        self.update_zoom_calibration()
        self.current_motor_positions["zoom"] = value
        self.refresh_omega_reference_position()

    def motor_positions_to_screen(self, centred_positions_dict):
        """
        Descript. :
        """
        c = centred_positions_dict
        xy = self.centring_hwobj.centringToScreen(c)
        x = xy["X"] * self.pixels_per_mm_x + self.zoom_centre["x"]
        y = xy["Y"] * self.pixels_per_mm_y + self.zoom_centre["y"]
        return x, y

    def do_oscillation_scan(self, start, end, exptime, wait=False):
        self.set_scan_number_of_frames(1)
        scan_params = "1\t%0.3f\t%0.3f\t%0.4f\t1" % (start, (end - start), exptime)
        scan = self.command_dict["startScanEx"]
        logging.getLogger("HWR").info(
            "[MAXIVMD3] MD3 oscillation requested, waiting device ready..., params "
            + str(scan_params)
        )
        self.wait_ready(200)
        logging.getLogger("HWR").info(
            "[MAXIVMD3] MD3 oscillation requested, device ready."
        )

        try:
            task_id = scan(scan_params)
        except Exception as ex:
            logging.getLogger("HWR").error(f"[MAXIVMD3] MD3 oscillation excetion {ex}")
        logging.getLogger("HWR").info(
            f"[MAXIVMD3] MD3 oscillation launched, task id: {task_id}"
        )

        if wait:
            task_info = self.waitTaskResult(
                task_id, timeout=DEFAULT_TASK_TIMEOUT + exptime
            )
            task_output, task_exception, task_result = task_info[4:7]

            if int(task_result) <= 0:  # either failed or aborted
                raise RuntimeError(
                    "MD3 Oscillation failed or aborted, output: %s | exception: %s |result: %s"
                    % (task_output, task_exception, task_result)
                )
        else:
            # we only wait until task actually started
            self.waitTaskIsRunning(task_id, timeout=DEFAULT_TASK_RUNNING_TIMEOUT)
            return

        logging.getLogger("HWR").info(
            "[MAXIVMD3] MD3 oscillation finished, task result %s." % str(task_info)
        )

    def osc_scan_4d(self, start, end, exptime, helical_pos, wait=False):
        scan_params = "%0.3f\t%0.3f\t%0.4f\t" % (start, (end - start), exptime)
        scan_params += "%0.3f\t" % helical_pos["1"]["phiy"]
        scan_params += "%0.3f\t" % helical_pos["1"]["phiz"]
        scan_params += "%0.3f\t" % helical_pos["1"]["sampx"]
        scan_params += "%0.3f\t" % helical_pos["1"]["sampy"]
        scan_params += "%0.3f\t" % helical_pos["2"]["phiy"]
        scan_params += "%0.3f\t" % helical_pos["2"]["phiz"]
        scan_params += "%0.3f\t" % helical_pos["2"]["sampx"]
        scan_params += "%0.3f\t" % helical_pos["2"]["sampy"]

        logging.getLogger("HWR").info(
            "[MAXIVMD3] MD3 helical oscillation requested, waiting device ready..., params "
            + str(scan_params)
        )
        scan = self.command_dict["startScan4DEx"]
        time.sleep(0.1)
        logging.getLogger("HWR").info(
            "[MAXIVMD3] MD3 helical oscillation requested, device ready."
        )

        try:
            task_id = scan(scan_params)
        except Exception as ex:
            logging.getLogger("HWR").error(f"[MAXIVMD3] MD3 oscillation excetion {ex}")
        logging.getLogger("HWR").info("[MAXIVMD3] MD3 Helical oscillation launched.")

        if wait:
            task_info = self.waitTaskResult(
                task_id, timeout=DEFAULT_TASK_TIMEOUT + exptime
            )
            logging.getLogger("HWR").info(
                "[MAXIVMD3] MD3 helical task info {}".format(task_info)
            )
            task_output, task_exception, task_result = task_info[4:7]
            if int(task_result) <= 0:  # either failed or aborted
                raise RuntimeError(
                    "MD3 Helical Oscillation failed or aborted, output: %s | exception: %s |result: %s"
                    % (task_output, task_exception, task_result)
                )
        else:
            # we only wait until task actually started
            self.waitTaskIsRunning(task_id, timeout=DEFAULT_TASK_RUNNING_TIMEOUT)
            return

        logging.getLogger("HWR").info(
            "[MAXIVMD3] MD3 helical oscillation finished, task result %s."
            % str(task_info)
        )

    def raster_scan(
        self,
        start,
        end,
        exptime,
        vertical_range,
        horizontal_range,
        nlines,
        nframes,
        invert_direction=1,
        wait=False,
    ):
        """
        raster_scan: snake scan by default
        start, end, exptime are the parameters per line
        Note: vertical_range and horizontal_range unit is mm, a test value could be 0.1,0.1
        example, raster_scan(20, 22, 5, 0.1, 0.1, 10, 10)
        """
        logging.getLogger("HWR").info("[MAXIVMD3] MD3 raster oscillation requested")
        msg = "[MAXIVMD3] MD3 raster scan params:"
        msg += " start: %s, end: %s, exptime: %s, range: %s, nframes: %s" % (
            start,
            end,
            exptime,
            end - start,
            nframes,
        )
        logging.getLogger("HWR").info(msg)

        self.channel_dict["ScanStartAngle"].set_value(start)
        self.channel_dict["ScanExposureTime"].set_value(exptime)
        self.channel_dict["ScanRange"].set_value(end - start)
        self.channel_dict["ScanNumberOfFrames"].set_value(nframes)

        raster_params = "%0.5f\t%0.5f\t%i\t%i\t%i" % (
            vertical_range,
            horizontal_range,
            nlines,
            nframes,
            invert_direction,
        )

        raster = self.command_dict["startRasterScan"]
        logging.getLogger("HWR").info(
            "[MAXIVMD3] MD3 raster oscillation requested, params: %s" % (raster_params)
        )
        logging.getLogger("HWR").info(
            "[MAXIVMD3] MD3 raster oscillation requested, waiting device ready"
        )

        self.wait_device_ready(200)
        logging.getLogger("HWR").info(
            "[MAXIVMD3] MD3 raster oscillation requested, device ready."
        )

        try:
            task_id = raster(raster_params)
        except Exception as ex:
            logging.getLogger("HWR").error(f"[MAXIVMD3] MD3 oscillation excetion {ex}")
        logging.getLogger("HWR").info("[MAXIVMD3] MD3 raster oscillation launched.")

        if wait:
            task_info = self.waitTaskResult(
                task_id, timeout=DEFAULT_TASK_TIMEOUT + exptime * nlines
            )
            task_output, task_exception, task_result = task_info[4:7]
            if int(task_result) <= 0:  # either failed or aborted
                raise RuntimeError(
                    "MD3 Raster Oscillation failed or aborted, output: %s | exception: %s |result: %s"
                    % (task_output, task_exception, task_result)
                )
        else:
            # we only wait until task actually started
            self.waitTaskIsRunning(task_id, timeout=DEFAULT_TASK_RUNNING_TIMEOUT)
            return

        logging.getLogger("HWR").info(
            "[MAXIVMD3] MD3 raster oscillation finished, task result %s."
            % str(task_info)
        )

    def wait_camera_exposure(self, value, timeout=10):
        logging.getLogger("HWR").info(
            "Waiting for camera exposure is set to %d" % value
        )
        with gevent.Timeout(
            timeout, Exception("Timeout waiting for camera exposure setting")
        ):
            exp_time = self.channel_dict["CameraExposure"].get_value()
            while int(exp_time) != value:
                gevent.sleep(1)

    def set_phase(self, phase, wait=False, timeout=None):
        try:
            self.wait_ready(10)
        except Exception as ex:
            logging.getLogger("HWR").error(
                "[MAXIVMD3] Cannot change phase to %s, timeout waiting for MD3 ready, %s"
                % (phase, ex)
            )
            logging.getLogger("user_log").error(
                "[MD3] Cannot change phase to %s, timeout waiting for MD3 ready" % phase
            )
        else:
            task_id = self.command_dict["startSetPhase"](phase)

            task_info = self.waitTaskResult(task_id)
            task_output, task_exception, task_result = task_info[4:7]
            if int(task_result) <= 0:  # either failed or aborted
                logging.getLogger("user_level_log").error(
                    "[MD3] Cannot change phase to %s; failed or aborted" % phase
                )
                msg = (
                    "MD3 Set Phase failed or aborted, output: %s | exception: %s |result: %s"
                    % (task_output, task_exception, task_result)
                )
                logging.getLogger("HWR").error(msg)
                raise RuntimeError(msg)

            if phase == "Centring":
                logging.getLogger("HWR").info(
                    "[MAXIVMD3] Wait for MD3 Camera exposure setting."
                )
                try:
                    self.wait_camera_exposure(value=20000, timeout=20)
                except Exception:
                    try:
                        self.wait_camera_exposure(value=20000, timeout=20)
                    except Exception as ex:
                        logging.getLogger("HWR").error(
                            "[MAXIVMD3] Timeout while setting MD3 Camera exposure %s"
                            % (ex)
                        )

    def move_to_motors_positions(self, motors_positions, wait=False):
        """ """
        try:
            motors_positions.pop("zoom")
        except:
            pass
        self.emit_progress_message("Moving to motors positions...")
        self.move_to_motors_positions_procedure = gevent.spawn(
            self.move_motors, motors_positions
        )
        self.move_to_motors_positions_procedure.link(self.move_motors_done)
        if wait:
            self.wait_ready(10)

    def move_motors(self, motor_positions, timeout=15):
        """
        Moves diffractometer motors to the requested positions

        :param motors_dict: dictionary with motor names or hwobj
                            and target values.
        :type motors_dict: dict
        """
        if self.head_type == GenericDiffractometer.HEAD_TYPE_PERMANENT:
            try:
                motor_positions.pop("kappa")
                motor_positions.pop("kappa_phi")
            except:
                pass
        for motor in motor_positions.keys():
            position = motor_positions[motor]
            logging.getLogger("HWR").debug(
                f"moving motor {motor} to position {position}"
            )
            if type(motor) is str:
                motor_role = motor
                motor = self.motor_hwobj_dict[motor_role]
                if motor is None:
                    continue
            motor.set_value(position)
        self.wait_ready(timeout)

    def move_sync_motors(self, motors_dict, wait=True, timeout=30):
        argin = ""
        logging.getLogger("HWR").debug(
            "MAXIVMD3: in move_sync_motors, wait: %s, motors: %s, tims: %s "
            % (wait, motors_dict, time.time())
        )
        for motor in motors_dict.keys():
            position = motors_dict[motor]
            if position is None:
                continue
            name = self.MOTOR_TO_EXPORTER_NAME[motor]
            argin += "%s=%0.3f;" % (name, position)
        if not argin:
            return
        self.wait_ready(2000)
        self.command_dict["startSimultaneousMoveMotors"](argin)
        if wait:
            self.wait_ready(timeout)

    def move_to_Beam(self, x, y):
        try:
            self.emit_progress_message("Move to beam...")
            self.beam_position = self.beam_info_hwobj.get_beam_position()
            beam_xc = self.beam_position[0]
            beam_yc = self.beam_position[1]
            cent_vertical_to_move = self.cent_vertical_pseudo_motor.get_value() - (
                x - beam_xc
            ) / float(self.pixelsPerMmY)
            self.emit_progress_message("")

            self.phiy_motor_hwobj.set_value_relative(
                -1 * (y - beam_yc) / float(self.pixelsPerMmZ)
            )
            self.cent_vertical_pseudo_motor.set_value(cent_vertical_to_move)
            self.wait_ready(5)
        except:
            logging.getLogger("HWR").exception("MD3: could not move to beam.")

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        """
        Descript. :
        """
        self.update_zoom_calibration()
        self.centring_hwobj.initCentringProcedure()
        self.centring_hwobj.appendCentringDataPoint(
            {
                "X": (x - self.beam_position[0]) / self.pixels_per_mm_x,
                "Y": (y - self.beam_position[1]) / self.pixels_per_mm_y,
            }
        )
        self.omega_reference_add_constraint()
        pos = self.centring_hwobj.centeredPosition()
        if return_by_names:
            pos = self.convert_from_obj_to_name(pos)
        pos.pop("zoom", None)
        return pos

    def abort(self):
        """
        Stops all the pending tasks, stops all the motors and closes all theirs control loop.
        """
        logging.getLogger("HWR").exception("MiniDiff: going to abort")
        self.command_dict["abort"]()
        logging.getLogger("HWR").exception("MiniDiff: all movements aborted")

    def move_omega_relative(self, relative_angle):
        """
        Descript. :
        """
        self.phi_motor_hwobj.set_value_relative(relative_angle, 10)

    def is_ready(self):
        """
        Detects if device is ready
        """
        return self.channel_dict["State"].get_value() == DiffractometerState.tostring(
            DiffractometerState.Ready
        )

    def get_positions(self):
        return {
            "phi": float(self.phi_motor_hwobj.get_value()),
            "focus": float(self.focus_motor_hwobj.get_value()),
            "phiy": float(self.phiy_motor_hwobj.get_value()),
            "phiz": float(self.phiz_motor_hwobj.get_value()),
            "sampx": float(self.sample_x_motor_hwobj.get_value()),
            "sampy": float(self.sample_y_motor_hwobj.get_value()),
            "kappa": float(self.kappa_motor_hwobj.get_value())
            if self.kappa_motor_hwobj
            else None,
            "kappa_phi": float(self.kappa_phi_motor_hwobj.get_value())
            if self.kappa_phi_motor_hwobj
            else None,
            "zoom": float(self.zoom_motor_hwobj.get_value().value),
        }

    def set_calculate_flux_phase(self):
        if self.head_type == GenericDiffractometer.HEAD_TYPE_MINIKAPPA:
            motors = [
                "phi",
                "focus",
                "phiz",
                "phiy",
                "sampx",
                "sampy",
                "kappa",
                "kappa_phi",
            ]
        else:
            motors = ["phi", "focus", "phiz", "phiy", "sampx", "sampy"]
        ori_motors = {}

        for motor in motors:
            try:
                ori_motors[motor] = self.motor_hwobj_dict[motor].get_value()
            except:
                pass
        ori_phase = self.current_phase
        if self.current_phase != "DataCollection":
            self.set_phase("DataCollection", wait=True, timeout=200)
        self.channel_dict["AlignmentTablePosition"].set_value("CLEAR_SCINTILLATOR")
        self.beamstop_z._set_value(85)
        self.wait_ready(10)
        return ori_motors, ori_phase

    def finish_calculate_flux(self, ori_motors, ori_phase="DataCollection"):
        self.set_phase(ori_phase, wait=True, timeout=200)
        self.wait_ready(10)
        if ori_phase == "DataCollection":
            self.channel_dict["BeamstopPosition"].set_value("BEAM")
        self.wait_ready(10)
        if ori_motors is not None:
            self.move_sync_motors(ori_motors)
            self.wait_ready(10)

    def centring_done(self, centring_procedure):
        GenericDiffractometer.centring_done(self, centring_procedure)
        self.save_centered_position()

    def save_centered_position(self):
        """
        save the current position as centered position in MD3
        """
        self.wait_ready(10)
        self.command_dict["saveCentringPositions"]()
        logging.getLogger("HWR").info("saving centered positions in MD3.")
        self.last_centered_position = self.get_positions()

    def set_camera_exposure(self, value):
        """
        Set MD3 camera exposure time
        Try maximum five times
        """
        trials = 0
        while trials < 5:
            try:
                time.sleep(1)
                self.channel_dict["CameraExposure"].set_value(int(value))
                logging.getLogger("HWR").info(
                    "camera exposure time is set to %d " % int(value)
                )
                break
            except:
                trials += 1

    def park_cryo_cooler(self, value=False, wait=True):
        """
        Set cryo cooler to park position if True, otherwise it's in
        """
        self.channel_dict["CryoIsOut"].set_value(value)
        if wait:
            self.wait_ready(2)

    def move_rex_out(self, wait=True, timeout=3):
        logging.getLogger("HWR").info("Moving REX out")
        self.wait_ready(3)
        self.rex.actuatorIn(wait=wait, timeout=timeout)

    def move_rex_in(self, wait=True, timeout=3):
        logging.getLogger("HWR").info("Moving REX in")
        self.wait_ready(3)
        self.rex.actuatorOut(wait=wait, timeout=timeout)

    def set_unmount_sample_phase(self, wait=True):
        """
        without changing the current MD3 phase, park beamstop, capillary, scintillator
        and set aperture to off position
        """
        self.wait_ready(3)
        self.command_dict["startMoveOrganDevices"]("OFF\tPARK\tPARK\tPARK")
        if wait:
            self.wait_ready(30)


def test():
    """

    To run the test in ipython:
    Go to mxcubecore folder
    then: "run mxcubecore/HardwareObjects/MAXIV/MAXIVMD3.py"
    pay attention to "hwr_dir"

    """
    from mxcubecore import HardwareRepository as HWR

    hwr_dir = "../mxcubecore/mxcubecore/configuration/MAXIV"
    HWR.init_hardware_repository(hwr_dir)
    hwr = HWR.get_hardware_repository()
    hwr_diff = hwr.get_hardware_object("md3/minidiff")

    print("    ")
    print("*****************************************************")
    print("    ")
    print("Testing MAXIVMD3.py---------------------------------")
    print("    ")
    print(
        "| Omega motor_hwobj value before move: ", hwr_diff.phi_motor_hwobj.get_value()
    )
    print("    ")
    print("| Omega motor_hwobj move to 77: ")
    hwr_diff.phi_motor_hwobj.set_value(77)
    time.sleep(2)
    print(
        "| Omega motor_hwobj value after move: ", hwr_diff.phi_motor_hwobj.get_value()
    )
    dynamic_limits = hwr_diff.phi_motor_hwobj.get_dynamic_limits()
    print("| Omega motor_hwobj dynamic_limits: ", dynamic_limits)
    print("| Omega motor_hwobj move relative 5 Deg.: ")
    hwr_diff.phi_motor_hwobj.set_value_relative(5)
    time.sleep(2)
    print(
        "| Omega motor_hwobj value after move: ", hwr_diff.phi_motor_hwobj.get_value()
    )
    print("    ")
    print("    ")
    print("| phiz_motor_hwobj value: ", hwr_diff.phiz_motor_hwobj.get_value())
    print("| phiy_motor_hwobj value: ", hwr_diff.phiy_motor_hwobj.get_value())
    print("| zoom_motor_hwobj value: ", hwr_diff.zoom_motor_hwobj.get_value())
    print("| focus_motor_hwobj value: ", hwr_diff.focus_motor_hwobj.get_value())
    print("| sample_x_motor_hwobj value: ", hwr_diff.sample_x_motor_hwobj.get_value())
    print("| sample_y_motor_hwobj value: ", hwr_diff.sample_y_motor_hwobj.get_value())
    print(
        "| beam_info_hwobj beam position: ",
        hwr_diff.beam_info_hwobj.get_beam_position(),
    )
    print("    ")
    print("    ")
    print("| Open fast shutter: ")
    hwr_diff.open_fast_shutter()
    print("| Is fast shutter open?: ", hwr_diff.is_fast_shutter_open())
    print("| Close fast shutter: ")
    hwr_diff.close_fast_shutter()
    print("| Is fast shutter open?: ", hwr_diff.is_fast_shutter_open())
    print("    ")
    print("    ")
    print("| fluodet hwrobj move In: ")
    hwr_diff.fluodet.actuatorIn()
    print(
        "| fluodet hwrobj actuator state: ",
        hwr_diff.fluodet.get_actuator_state(read=True),
    )
    print("| fluodet hwrobj move out: ")
    hwr_diff.fluodet.actuatorOut()
    print(
        "| fluodet hwrobj actuator state: ",
        hwr_diff.fluodet.get_actuator_state(read=True),
    )
    print("    ")
    print("    ")
    print("| Phase of MD3: ", hwr_diff.get_current_phase())
    print("    ")
    print("    ")
    print("| Osc scan: ")
    hwr_diff.osc_scan(8, 18, 0.5, wait=False)
    print("    ")
    print("    ")
    print("| rex hwobj actuator state: ", hwr_diff.rex.get_actuator_state(read=True))
    print("| centring_hwobj: ", hwr_diff.centring_hwobj)
    print("| beamstop_z hwobj value: ", hwr_diff.beamstop_z.get_value())
    print("    ")
    print("| cmera hwobj: ", hwr_diff.camera)
    print("| Image width: ", hwr_diff.camera.get_width())
    print("| Image height: ", hwr_diff.camera.get_height())
    print("    ")
    print("    ")
    print("*****************************************************")


if __name__ == "__main__":
    test()
