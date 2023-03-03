import os
import logging
import contextlib
import enum
import subprocess
from pydantic import BaseModel, Field
from devtools import debug

from mxcubecore.model.common import (
    CommonCollectionParamters,
    PathParameters,
    LegacyParameters,
    StandardCollectionParameters,
)

from mxcubecore import HardwareRepository as HWR

from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
)

from mxcubecore.model.queue_model_objects import (
    DataCollection,
)


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class SSXUserCollectionParameters(BaseModel):
    sub_sampling: float = Field(6, gt=0, lt=100)
    nb_samples_per_line: int = Field(500, gt=0, lt=1000)
    nb_lines: int = Field(3000, gt=0, lt=10000)
    take_pedestal: bool = Field(True)

    class Config:
        extra: "ignore"


class SsxFoilColletionTaskParameters(BaseModel):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: SSXUserCollectionParameters
    legacy_parameters: LegacyParameters


class SsxFoilCollectionQueueModel(DataCollection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SsxBigFoilCollectionLima2CalibQueueEntry(BaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    QMO = SsxFoilCollectionQueueModel
    DATA_MODEL = SsxFoilColletionTaskParameters
    NAME = "SSX Big Foil Collection (Lima2) Calib"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    # New style queue entry does not take view argument,
    # adding kwargs for compatability, but they are unsued
    def __init__(self, view, data_model: SsxFoilCollectionQueueModel):
        super().__init__(view=view, data_model=data_model)

    def execute(self):
        super().execute()
        debug(self._data_model._task_data)
        params = self._data_model._task_data.user_collection_parameters

        MAX_FREQ = 1387.5

        gonio_config = HWR.beamline.diffractometer.get_head_configuration()
        chip_calibration_data = gonio_config["calibration_data"]

        z = 0.08
        motor_top_left_x = chip_calibration_data["top_left"][0]
        motor_top_left_y = chip_calibration_data["top_left"][1]
        motor_top_left_z = z

        motor_bottom_right_x = chip_calibration_data["bottom_right"][0]
        motor_bottom_right_y = chip_calibration_data["bottom_right"][1]

        motor_top_right_x: motor_bottom_right_x
        motor_top_right_y: motor_top_left_y
        motor_top_right_z: z

        motor_bottom_left_x: motor_top_left_x
        motor_bottom_left_y: motor_bottom_right_y
        motor_bottom_left_z: z

        exp_time = self._data_model._task_data.user_collection_parameters.exp_time
        fname_prefix = self._data_model._task_data.path_parameters.prefix
        num_images = self._data_model._task_data.user_collection_parameters.num_images
        sub_sampling = (
            self._data_model._task_data.user_collection_parameters.sub_sampling
        )

        # if HWR.beamline.control.safshut_oh2.state.name == "DISABLE":
        #    raise RuntimeError(HWR.beamline.control.safshut_oh2.state.value)

        debug(f"type(HWR.beamline.control)={type(HWR.beamline.control)}")
        if hasattr(HWR.beamline.control, "SCAN_DISPLAY"):
            HWR.beamline.control.SCAN_DISPLAY.auto = True

        data_root_path = HWR.beamline.session.get_image_directory(
            os.path.join(
                self._data_model._task_data.path_parameters.subdir,
                self._data_model._task_data.path_parameters.experiment_name,
            )
        )

        process_path = os.path.join(
            HWR.beamline.session.get_base_process_directory(),
            self._data_model._task_data.path_parameters.subdir,
        )

        if params.take_pedestal:
            HWR.beamline.control.safshut_oh2.close()
            if not hasattr(HWR.beamline.control, "lima2_jungfrau_pedestal_scans"):
                HWR.beamline.control.load_script("id29_lima2.py")

            pedestal_dir = HWR.beamline.detector.find_next_pedestal_dir(
                data_root_path, "pedestal"
            )
            logging.getLogger("user_level_log").info(
                f"Storing pedestal in {pedestal_dir}"
            )
            subprocess.Popen(
                "mkdir --parents %s && chmod -R 755 %s" % (pedestal_dir, pedestal_dir),
                shell=True,
                stdin=None,
                stdout=None,
                stderr=None,
                close_fds=True,
            ).wait()

            HWR.beamline.control.lima2_jungfrau_pedestal_scans(
                HWR.beamline.control.lima2_jungfrau4m_rr_smx,
                exp_time,
                MAX_FREQ / sub_sampling,
                1000,
                pedestal_dir,
                "pedestal.h5",
                disable_saving="raw",
                print_params=True,
            )

            subprocess.Popen(
                "cd %s && rm -f pedestal.h5 && ln -s %s/pedestal.h5"
                % (data_root_path, pedestal_dir),
                shell=True,
                stdin=None,
                stdout=None,
                stderr=None,
                close_fds=True,
            ).wait()

        fname_prefix = self._data_model._task_data.path_parameters.prefix
        fname_prefix += f"_foil_"

        region = (
            motor_top_left_x,
            motor_top_left_y,
            motor_top_left_z,
            motor_top_right_x,
            motor_top_right_y,
            motor_top_right_z,
            motor_bottom_left_x,
            motor_bottom_left_y,
            motor_bottom_left_z,
        )

        beamline_values = HWR.beamline.lims.pyispyb.get_current_beamline_values()

        logging.getLogger("user_level_log").info(f"Defining region {region}")

        HWR.beamline.diffractometer.define_ssx_scan_region(
            *region, params.nb_samples_per_line, params.nb_lines
        )

        logging.getLogger("user_level_log").info("Preparing detector")
        HWR.beamline.detector.stop_acquisition()

        num_images = params.nb_samples_per_line * params.nb_lines
        HWR.beamline.detector.prepare_acquisition(
            num_images, exp_time, data_root_path, fname_prefix
        )

        HWR.beamline.detector.wait_ready()

        HWR.beamline.detector.start_acquisition()
        logging.getLogger("user_level_log").info(
            "Detector ready, waiting for trigger ..."
        )

        HWR.beamline.diffractometer.wait_ready()
        HWR.beamline.diffractometer.set_phase("DataCollection", wait=True, timeout=120)
        # HWR.beamline.diffractometer.wait_ready()

        if HWR.beamline.control.safshut_oh2.state.name != "OPEN":
            logging.getLogger("user_level_log").info(f"Opening OH2 safety shutter")
            HWR.beamline.control.safshut_oh2.open()

        logging.getLogger("user_level_log").info(f"Acquiring {num_images}")

        try:
            HWR.beamline.diffractometer.start_ssx_scan(params.sub_sampling)
            HWR.beamline.diffractometer.wait_ready()
        except:
            msg = "Diffractometer failed! Waiting for detector to finish"
            logging.getLogger("user_level_log").error(msg)
            HWR.beamline.detector.wait_ready()
            raise

        if HWR.beamline.control.safshut_oh2.state.name == "OPEN":
            HWR.beamline.control.safshut_oh2.close()
            logging.getLogger("user_level_log").info("shutter closed")

        HWR.beamline.detector.wait_ready()
        logging.getLogger("user_level_log").info(f"Acquired {region}")

        HWR.beamline.lims.pyispyb.create_ssx_collection(
            self._data_model._task_data,
            beamline_values,
        )

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()
        if HWR.beamline.control.safshut_oh2.state.name == "OPEN":
            HWR.beamline.control.safshut_oh2.close()
            logging.getLogger("user_level_log").info("shutter closed")

        HWR.beamline.detector.stop_acquisition()

    def stop(self):
        super().stop()
        if HWR.beamline.control.safshut_oh2.state.name == "OPEN":
            HWR.beamline.control.safshut_oh2.close()
            logging.getLogger("user_level_log").info("shutter closed")

        HWR.beamline.detector.stop_acquisition()
