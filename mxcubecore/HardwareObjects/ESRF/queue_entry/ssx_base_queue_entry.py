import os
import logging
import subprocess
import datetime
import json
import gevent

from typing_extensions import Literal
from pydantic import BaseModel, Field
from devtools import debug

from mxcubecore import HardwareRepository as HWR
from mxcubecore.queue_entry.base_queue_entry import BaseQueueEntry

import logging
import xmlrpc.client


class BaseUserCollectionParameters(BaseModel):
    num_images: int = Field(0, description="")
    exp_time: float = Field(100e-6, gt=0, lt=1, description="s")
    sub_sampling: Literal[1, 2, 4, 6, 8] = Field(1)
    take_pedestal: bool = Field(True)

    frequency: float = Field(
        float(HWR.beamline.config.diffractometer.get_property("max_freq", 925)),
        description="Hz",
    )


class SsxBaseQueueTaskParameters(BaseModel):
    @staticmethod
    def ui_schema():
        return json.dumps(
            {
                "ui:order": [
                    "num_images",
                    "exp_time",
                    "osc_range",
                    "osc_start",
                    "resolution",
                    "transmission",
                    "energy",
                    "vertical_spacing",
                    "horizontal_spacing",
                    "nb_lines",
                    "nb_samples_per_line",
                    "motor_top_left_x",
                    "motor_top_left_y",
                    "motor_top_left_z",
                    "motor_top_right_x",
                    "motor_top_right_y",
                    "motor_top_right_z",
                    "motor_bottom_left_x",
                    "motor_bottom_left_y",
                    "motor_bottom_left_z",
                    "chip_type",
                    "take_pedestal",
                    "sub_sampling",
                    "*",
                ],
                "ui:submitButtonOptions": {
                    "norender": "true",
                },
                "sub_sampling": {"ui:readonly": "true"},
                "frequency": {"ui:readonly": "true"},
            }
        )


class SsxBaseQueueEntry(BaseQueueEntry):
    """
    Defines common SSX collection methods.
    """

    def __init__(self, view, data_model):
        super().__init__(view=view, data_model=data_model)
        self.beamline_values = None

        self._use_nicoproc = False
        self._processing_host = "http://lid29control-2:9998"

    def get_data_path(self):
        data_root_path = HWR.beamline.config.session.get_image_directory(
            os.path.join(
                self._data_model._task_data.path_parameters.subdir,
                self._data_model._task_data.path_parameters.experiment_name,
            )
        )

        process_path = os.path.join(
            HWR.beamline.config.session.get_base_process_directory(),
            self._data_model._task_data.path_parameters.subdir,
        )

        return data_root_path, process_path

    def take_pedestal(self, max_freq):
        params = self._data_model._task_data.user_collection_parameters

        exp_time = self._data_model._task_data.user_collection_parameters.exp_time
        sub_sampling = (
            self._data_model._task_data.user_collection_parameters.sub_sampling
        )

        data_root_path, _ = self.get_data_path()

        packet_fifo_depth = 20000

        if params.take_pedestal:
            HWR.beamline.config.control.safshut_oh2.close()
            if not hasattr(HWR.beamline.config.control, "lima2_jungfrau_pedestal_scans"):
                HWR.beamline.config.control.load_script("id29_lima2.py")

            pedestal_dir = HWR.beamline.config.detector.find_next_pedestal_dir(
                data_root_path, "pedestal"
            )
            sls_detectors = "/users/blissadm/local/sls_detectors"
            lima2_path = f"{sls_detectors}/lima2"
            cl_source_path = f"{lima2_path}/processings/common/fai/kernels"

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

            HWR.beamline.config.control.lima2_jungfrau_pedestal_scans(
                HWR.beamline.config.control.lima2_jungfrau4m_rr_smx,
                exp_time,
                max_freq / sub_sampling,
                1000,
                pedestal_dir,
                "pedestal.h5",
                disable_saving="raw",
                print_params=True,
                det_params={"packet_fifo_depth": packet_fifo_depth},
                cl_source_path=cl_source_path,
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

    def start_processing(self, exp_type):
        data_root_path, _ = self.get_data_path()

        if self._use_nicoproc:
            self._start_ssx_processing(
                self.beamline_values,
                self._data_model._task_data,
                data_root_path,
                experiment_type=exp_type,
            )
        else:
            logging.getLogger("user_level_log").info(f"NICOPROC False")

    def prepare_acqiusition(self):
        exp_time = self._data_model._task_data.user_collection_parameters.exp_time
        fname_prefix = self._data_model._task_data.path_parameters.prefix
        num_images = self._data_model._task_data.user_collection_parameters.num_images
        data_root_path, _ = self.get_data_path()

        HWR.beamline.config.detector.stop_acquisition()
        HWR.beamline.config.detector.prepare_acquisition(
            num_images, exp_time, data_root_path, fname_prefix
        )
        HWR.beamline.config.detector.wait_ready()

    def _monitor_collect(self):
        for i in range(1, 99):
            self.emit_progress(i / 100.0)
            gevent.sleep(0.1)

    def execute(self):
        super().execute()
        debug(self._data_model._task_data)

        self._monitor_task = gevent.spawn(self._monitor_collect)

    def pre_execute(self):
        super().pre_execute()
        self.beamline_values = HWR.beamline.config.lims.pyispyb.get_current_beamline_values()
        self.additional_lims_values = (
            HWR.beamline.config.lims.pyispyb.get_additional_lims_values()
        )
        self.emit_progress(0)

    def post_execute(self):
        super().post_execute()
        data_root_path, _ = self.get_data_path()
        self.additional_lims_values.end_time = datetime.datetime.now()

        HWR.beamline.config.lims.pyispyb.create_ssx_collection(
            data_root_path,
            self._data_model._task_data,
            self.beamline_values,
            self.additional_lims_values,
        )

        if HWR.beamline.config.control.safshut_oh2.state.name == "OPEN":
            logging.getLogger("user_level_log").info(f"Opening OH2 safety shutter")
            HWR.beamline.config.control.safshut_oh2.close()

        HWR.beamline.config.detector.wait_ready()
        HWR.beamline.config.detector.stop_acquisition()
        self.emit_progress(1)

    def emit_progress(self, progress):
        HWR.beamline.config.collect.emit_progress(progress)

    def stop(self):
        super().stop()
        if HWR.beamline.config.control.safshut_oh2.state.name == "OPEN":
            HWR.beamline.config.control.safshut_oh2.close()
            logging.getLogger("user_level_log").info("shutter closed")

        HWR.beamline.config.detector.stop_acquisition()

    def _start_processing(self, dc_parameters, file_paramters):
        param = {
            "exposure": dc_parameters["oscillation_sequence"][0]["exposure_time"],
            "detector_distance": dc_parameters["detectorDistance"],
            "wavelength": dc_parameters["wavelength"],
            "orgx": dc_parameters["xBeam"],
            "orgy": dc_parameters["yBeam"],
            "oscillation_range": dc_parameters["oscillation_sequence"][0]["range"],
            "start_angle": dc_parameters["oscillation_sequence"][0]["start"],
            "number_images": dc_parameters["oscillation_sequence"][0][
                "number_of_images"
            ],
            "image_first": dc_parameters["oscillation_sequence"][0][
                "start_image_number"
            ],
            "fileinfo": file_paramters,
        }

        logging.getLogger("HWR").info("NICOPROC START")

        with xmlrpc.client.ServerProxy(self._processing_host) as p:
            p.start(param)

    def _start_ssx_processing(self, beamline_values, params, path, experiment_type=""):
        param = {
            "exposure": params.user_collection_parameters.exp_time,
            "detector_distance": beamline_values.detector_distance,
            "wavelength": beamline_values.wavelength,
            "orgx": beamline_values.beam_x,
            "orgy": beamline_values.beam_y,
            "oscillation_range": params.collection_parameters.osc_range,
            "start_angle": params.collection_parameters.osc_start,
            "number_images": params.user_collection_parameters.num_images,
            "image_first": params.collection_parameters.first_image,
            "fileinfo": params.path_parameters.dict(),
            "root_path": path,
            "experiment_type": experiment_type,
        }

        logging.getLogger("HWR").info("NICOPROC START")

        try:
            with xmlrpc.client.ServerProxy(self._processing_host) as p:
                p.start(param)
        except Exception:
            logging.getLogger("HWR").exception("")

    def _stop_processing(self):
        logging.getLogger("HWR").info("NICOPROC STOP")

        with xmlrpc.client.ServerProxy(self._processing_host) as p:
            p.stop()
