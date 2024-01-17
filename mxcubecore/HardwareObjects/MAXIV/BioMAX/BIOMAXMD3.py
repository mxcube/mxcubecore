import time
import logging
import gevent
import numpy as np
from PIL import Image
import cv2
import math
import os
from mxcubecore.HardwareObjects.GenericDiffractometer import (
    GenericDiffractometer,
    DiffractometerState,
)
from mxcubecore.HardwareObjects.MAXIV.MAXIVMD3 import MAXIVMD3
from mxcubecore import HardwareRepository as HWR

from gevent import monkey

monkey.patch_all(thread=False)


class BIOMAXMD3(MAXIVMD3):
    def __init__(self, *args):
        """
        Description:
        """
        super().__init__(self, *args)

    def init(self):
        super().init()

        try:
            self.zoom_centre = eval(self.get_property("zoom_centre"))
            zoom = self.camera.get_image_zoom()
            if zoom is not None:
                self.zoom_centre["x"] = self.zoom_centre["x"] * zoom
                self.zoom_centre["y"] = self.zoom_centre["y"] * zoom
            self.beam_position = [self.zoom_centre["x"], self.zoom_centre["y"]]
            self.beam_info_hwobj.beam_position = self.beam_position
        except:
            if self.image_width is not None and self.image_height is not None:
                self.zoom_centre = {
                    "x": self.image_width / 2,
                    "y": self.image_height / 2,
                }
                self.beam_position = [self.image_width / 2, self.image_height / 2]
                logging.getLogger("HWR").warning(
                    "Diffractometer: Zoom center is ' +\
                       'not defined. Continuing with the middle: %s"
                    % self.zoom_centre
                )
            else:
                logging.getLogger("HWR").warning(
                    "Diffractometer: Neither zoom centre nor camera size are defined"
                )

        """
        init CameraExposure channel seperately, also try it several times
        due to the frequent TimeoutError when connecting to this channel
        Note, this is a temporary fix until Arinax has a solution
        """
        init_trials = 0
        camera_exposure = None
        while init_trials < 5 and camera_exposure is None:
            if init_trials > 0:
                time.sleep(1)
                logging.getLogger("HWR").warning(
                    "Initializing MD3 CameraExposure Channel Failed, trying again."
                )
            camera_exposure = self.add_channel(
                {"type": "exporter", "name": "CameraExposure"}, "CameraExposure"
            )
            init_trials += 1
        self.channel_dict["CameraExposure"] = camera_exposure

    def wait_stable_loop(self, wait_time):
        logging.getLogger("user_level_log").info("Waiting loop to be stable...")
        img_bef = self._get_image_array()
        timer = 0
        wait_int = 2
        while timer < wait_time:
            time.sleep(wait_int)
            img_after = self._get_image_array()
            diff = cv2.absdiff(img_bef, img_after)
            if diff.max() < 100:
                logging.getLogger("user_level_log").info(
                    "No obvious drift, loop is relatively stable"
                )
        self.update_zoom_calibration()

    def current_phase_changed(self, current_phase):
        """
        Descript. :
        """
        self.current_phase = current_phase
        logging.getLogger("HWR").info("MD3 phase changed to %s" % current_phase)
        self.emit("phaseChanged", (current_phase,))

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

    def start_3_click_centring(self):
        self.start_centring_method(self.CENTRING_METHOD_MANUAL)

    def start_auto_centring(self):
        self.start_centring_method(self.CENTRING_METHOD_AUTO)

    def get_pixels_per_mm(self):
        """
        Get the values from coaxCamScaleX and coaxCamScaleY channels diretly

        :returns: list with two floats
        """
        zoom = self.camera.get_image_zoom()
        return (
            zoom / self.channel_dict["CoaxCamScaleX"].get_value(),
            1 / self.channel_dict["CoaxCamScaleY"].get_value(),
        )

    def update_zoom_calibration(self):
        """ """
        zoom = self.camera.get_image_zoom()
        self.pixels_per_mm_x = zoom / self.channel_dict["CoaxCamScaleX"].get_value()
        self.pixels_per_mm_y = zoom / self.channel_dict["CoaxCamScaleY"].get_value()
        self.emit("pixelsPerMmChanged", ((self.pixels_per_mm_x, self.pixels_per_mm_y)))

    def manual_centring(self):
        """
        Descript. :
        """
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
        return self.centring_hwobj.centeredPosition(return_by_name=False)

    def automatic_centring_old(self):
        """Automatic centring procedure. Rotates n times and executes
        centring algorithm. Optimal scan position is detected.
        """

        surface_score_list = []
        self.zoom_motor_hwobj.move_to_position("Zoom 1")
        self.wait_device_ready(3)
        self.centring_hwobj.initCentringProcedure()
        for image in range(BIOMAXMD3.AUTOMATIC_CENTRING_IMAGES):
            x, y, score = self.find_loop()
            if x > -1 and y > -1:
                self.centring_hwobj.appendCentringDataPoint(
                    {
                        "X": (x - self.beam_position[0]) / self.pixels_per_mm_x,
                        "Y": (y - self.beam_position[1]) / self.pixels_per_mm_y,
                    }
                )
                return
            img_bef = img_after
            timer += wait_int
        logging.getLogger("user_level_log").info(
            "Loop is still drifting, have waited {}s, give up and continue with collection".format(
                wait_time
            )
        )
        logging.getLogger("user_level_log").info(
            "Loop is still drifting, have waited {}s, give up and continue with collection".format(
                wait_time
            )
        )

    def automatic_centring(self):
        self.wait_device_ready(10)
        # move MD3 to Centring phase if it's not
        if self.get_current_phase() != "Centring":
            logging.getLogger("user_level_log").info(
                "Moving Diffractometer to Centring for automatic_centring"
            )
            self.set_phase("Centring", wait=True, timeout=200)
        # make sure the back light factor is 1, zoom level is 1, before loop centering
        self.zoom_motor_hwobj.moveToPosition("Zoom 1")
        self.wait_device_ready(20)
        self.back_light.move(1)
        self.wait_device_ready(2)
        self.omega_reference_motor.move(self.omega_reference_par["position"])
        self.wait_device_ready(2)
        centred_pos = self.pre_align_loop()

        # temporary implementation for testing the drift issue
        # Note, we also need to increase the cent result timeout, scutils.py, line 179
        # centring_result = async_result.get(timeout=300)
        """
        try:
            dir_name = "/data/staff/ispybstorage/staff/jienan/drift_test"
            counter = 0
            while(counter < 120):
                timestr = time.strftime("%Y%m%d-%H%M%S")
                file_name = os.path.join(dir_name, "{}.jpg".format(timestr))
                self.camera_hwobj.save_snapshot(file_name)
                time.sleep(2)
                counter += 2
        except Exception as ex:
           logging.error("MD3 exception while saving snapshots {}".format(ex))
           pass
        """

        # now it runs lucid always, but should skip it if the pre_align_loop works well
        self.wait_stable_loop(60)
        # logging.info("start lucid auto loop centring...")
        # centred_pos = self.do_automatic_centring(1)
        return centred_pos

    def pre_align_loop(self):
        cycle = 5
        DIS_TO_CENTER_VERT = 0
        DIS_TO_CENTER_HOR = 0
        # temporary implementation for evalating the loop centring
        self.take_snapshots_loop("before")
        logging.getLogger("HWR").info("Start to pre-align the loop...")
        logging.getLogger("user_level_log").info("Start to pre-align the loop...")
        for i in range(cycle):
            dis_to_center_hor, dis_to_center_vert = self.locate_loop()
            if dis_to_center_hor == 0 and dis_to_center_vert == 0:
                if i == cycle - 1:
                    # still no loop detected with the last trial
                    return None
                dis_to_center_vert = self.zoom_centre["y"]

            if abs(dis_to_center_vert) >= DIS_TO_CENTER_VERT:
                self.move_loop_vert_relative(dis_to_center_vert)
                dis_to_center_hor, dis_to_center_vert = self.locate_loop(loop_tip=True)
                # return False
            if abs(dis_to_center_hor) >= DIS_TO_CENTER_HOR:
                self.move_loop_hor_relative(dis_to_center_hor)
            self.phi_motor_hwobj.moveRelative(360.0 / cycle)
            self.wait_device_ready(5)
        # temporary implementation for evalating the loop centring
        self.take_snapshots_loop("after")
        cpos = self.get_positions()
        cpos.pop("zoom", None)
        return cpos

    def locate_loop(self, loop_tip=False):
        """
        align the loop to within 200 pixels of the beam center
        """
        loop_int_threshold = 6000
        if self.ref_img is None:
            logging.warning(
                "Reference image for the sample video is missing, skip the initial loop alignment!"
            )
            return
        img_buf, w, h = self.camera_hwobj.get_image_array()
        img = img_buf.reshape(h, w, 3)
        gray_img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        diff = self.ref_img - gray_img
        diff_ver = np.sum(diff, axis=1)
        diff_ver_threshold = np.where(diff_ver > loop_int_threshold)
        diff_ver_max = -1
        if diff_ver_threshold[0].size < 1:
            dis_to_center_vert = 0
        else:
            diff_ver_max = diff_ver_threshold[0].max()
            dis_to_center_vert = self.zoom_centre["y"] - diff_ver_max
        if loop_tip and diff_ver_max > 0:
            # only use the tip of the loop
            diff_hor = np.sum(diff[max(0, diff_ver_max - 5) : diff_ver_max, :], axis=0)
            diff_hor_threshold = np.where(diff_hor > 100)
        else:
            # use the full range
            diff_hor = np.sum(diff, axis=0)
            diff_hor_threshold = np.where(diff_hor > loop_int_threshold)

        if diff_hor_threshold[0].size < 1:
            dis_to_center_hor = 0
        else:
            if diff_ver_threshold[0].size < 1:
                # if detected horizontally, move the sample down
                dis_to_center_vert = self.zoom_centre["y"]
            dis_to_center_hor = (
                self.zoom_centre["x"]
                - (diff_hor_threshold[0].min() + diff_hor_threshold[0].max()) / 2.0
            )
        return dis_to_center_hor, dis_to_center_vert

    def move_loop_vert_relative(self, dis):
        move_relative = dis / float(self.pixelsPerMmZ)
        target_pos = self.phiy_motor_hwobj.getPosition() + move_relative
        min_pos = -4.0
        max_pos = 4.0
        if target_pos < min_pos or target_pos > max_pos:
            return False
        self.phiy_motor_hwobj.moveRelative(move_relative)
        self.wait_device_ready(5)
        return True

    def move_loop_hor_relative(self, dis):
        cent_vertical_pos = self.cent_vertical_pseudo_motor.getValue() + dis / float(
            self.pixelsPerMmY
        )
        self.cent_vertical_pseudo_motor.set_value(cent_vertical_pos)
        self.wait_device_ready(5)

    def take_snapshots_loop(self, suffix):
        dir_name = "/data/staff/ispybstorage/staff/jienan"
        timestr = time.strftime("%Y%m%d-%H%M%S")
        file_name = os.path.join(dir_name, "{}_{}.jpeg".format(timestr, suffix))
        logging.getLogger("user_level_log").info(
            "Taking snapshot {} {} pre-aligning loop".format(file_name, suffix)
        )
        self.camera_hwobj.save_snapshot(file_name)
