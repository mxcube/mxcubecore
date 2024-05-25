import logging
import gevent
import lucid3
import numpy as np
from PIL import Image
from mxcubecore.HardwareObjects.GenericDiffractometer import (
    GenericDiffractometer,
    DiffractometerState,
)
from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.MAXIV.MAXIVMD3 import MAXIVMD3

from gevent import monkey

monkey.patch_all(thread=False)

MONITORING_INTERVAL = 0.1
DEFAULT_TASK_TIMEOUT = 200
DEFAULT_TASK_RUNNING_TIMEOUT = 2


class MICROMAXMD3(MAXIVMD3):
    def __init__(self, *args):
        """
        Description:
        """
        super().__init__(*args)

    def init(self):

        super().init()

        self.image_width = None
        self.image_height = None

    def state_changed(self, state):
        logging.getLogger("HWR").debug("State changed %s" % str(state))
        self.current_state = state
        self.emit("valueChanged", (self.current_state))

    def find_loop(self):
        img_buf, _, _ = HWR.beamline.sample_view.camera.get_image_array()
        info, x, y = lucid3.find_loop(img_buf)

        if info != "Coord":
            # loop not found
            return -1, -1, 0

        surface_score = 10
        return x, y, surface_score

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
        table_pitch=1,
        fast_scan=1,
    ):
        """
           raster_scan: snake scan by default
           start, end, exptime are the parameters per line
           Note: vertical_range and horizontal_range unit is mm, a test value could be 0.1,0.1
           example, raster_scan(20, 22, 5, 0.1, 0.1, 10, 10)

        Args:
            invert_direction: ``1`` to enable passes in the reverse direction.
            table_pitch: ``1`` to use the centring table to do the pitch movements.
            fast_scan: ``1`` to use the fast raster scan if available (power PMAC).
        """
        logging.getLogger("HWR").info("[MICROMAXMD3] MD3 raster oscillation requested")
        msg = "[MICROMAXMD3] MD3 raster scan params:"
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
        self.channel_dict["ScanNumberOfFrames"].set_value(1)

        raster_params = "%0.5f\t%0.5f\t%i\t%i\t%i\t%i\t%i" % (
            vertical_range,
            horizontal_range,
            nlines,
            1,
            invert_direction,
            table_pitch,
            fast_scan,
        )

        raster = self.command_dict["startRasterScan"]
        logging.getLogger("HWR").info(
            "[MICROMAXMD3] MD3 raster oscillation requested, params: %s"
            % (raster_params)
        )
        logging.getLogger("HWR").info(
            "[MICROMAXMD3] MD3 raster oscillation requested, waiting device ready"
        )

        self.wait_ready(200)
        logging.getLogger("HWR").info(
            "[MICROMAXMD3] MD3 raster oscillation requested, device ready."
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
            "[MICROMAXMD3] MD3 raster oscillation finished, task result %s."
            % str(task_info)
        )

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
        self.motor_hwobj_dict['phiz'].set_value(2)
        self.set_organ_pos("beamstopZ", -10)
        self.wait_ready(10)
        return ori_motors, ori_phase

    def set_organ_pos(self, motor_name, pos_name):
        try:
            if motor_name =="beamstop":
                self.command_dict["setBeamstopPosition"](pos_name)
                self.wait_device_ready(DEFAULT_PHASE_TIMEOUT)
                return
            elif motor_name =="cameraExposure":
                name = "CameraExposure"
            else:
                name = "{}{}Position".format(motor_name[0].upper(), motor_name[1:])
            self.channel_dict[name].set_value(pos_name)
            self.wait_device_ready(DEFAULT_PHASE_TIMEOUT)
        except Exception as ex:
            error_msg = "[MICROMAXMD3] Error while moving {} to {}, {}".format(
                motor_name, pos_name, ex
            )
            logging.getLogger("HWR").error(error_msg)
            raise

