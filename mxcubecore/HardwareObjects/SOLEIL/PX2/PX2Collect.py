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

import os
import logging
import gevent
from mxcubecore.TaskUtils import task
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractCollect import AbstractCollect

from omega_scan import omega_scan
from inverse_scan import inverse_scan
from reference_images import reference_images
from helical_scan import helical_scan
from fluorescence_spectrum import fluorescence_spectrum
from energy_scan import energy_scan

# from xray_centring import xray_centring
from raster_scan import raster_scan
from nested_helical_acquisition import nested_helical_acquisition
from tomography import tomography
from film import film
from mxcubecore import HardwareRepository as HWR

from slits import slits1

__credits__ = ["Synchrotron SOLEIL"]
__version__ = "2.3."
__category__ = "General"


class PX2Collect(AbstractCollect, HardwareObject):
    """Main data collection class. Inherited from AbstractCollect.
       Collection is done by setting collection parameters and
       executing collect command
    """

    experiment_types = [
        "omega_scan",
        "reference_images",
        "inverse_scan",
        "mad",
        "helical_scan",
        "xrf_spectrum",
        "energy_scan",
        "raster_scan",
        "nested_helical_acquisition",
        "tomography",
        "film",
        "optical_centering",
    ]

    # experiment_types = ['OSC',
    # 'Collect - Multiwedge',
    # 'Helical',
    # 'Mesh',
    # 'energy_scan',
    # 'xrf_spectrum',
    # 'neha'

    def __init__(self, name):
        """
        :param name: name of the object
        :type name: string
        """

        AbstractCollect.__init__(self, name)
        HardwareObject.__init__(self, name)

        self.current_dc_parameters = None
        self.osc_id = None
        self.owner = None
        self.aborted_by_user = None
        self.slits1 = slits1()

    def init(self):

        self.ready_event = gevent.event.Event()

        undulators = []
        try:
            for undulator in self["undulators"]:
                undulators.append(undulator)
        except Exception:
            pass

        beam_div_hor, beam_div_ver = HWR.beamline.beam.get_beam_divergence()

        self.set_beamline_configuration(
            synchrotron_name="SOLEIL",
            directory_prefix=self.get_property("directory_prefix"),
            default_exposure_time=HWR.beamline.detector.get_property(
                "default_exposure_time"
            ),
            minimum_exposure_time=HWR.beamline.detector.get_property(
                "minimum_exposure_time"
            ),
            detector_fileext=HWR.beamline.detector.get_property("fileSuffix"),
            detector_type=HWR.beamline.detector.get_property("type"),
            detector_manufacturer=HWR.beamline.detector.get_property("manufacturer"),
            detector_model=HWR.beamline.detector.get_property("model"),
            detector_px=HWR.beamline.detector.get_property("px"),
            detector_py=HWR.beamline.detector.get_property("py"),
            undulators=undulators,
            focusing_optic=self.get_property("focusing_optic"),
            monochromator_type=self.get_property("monochromator"),
            beam_divergence_vertical=beam_div_ver,
            beam_divergence_horizontal=beam_div_hor,
            polarisation=self.get_property("polarisation"),
            input_files_server=self.get_property("input_files_server"),
        )

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True,))

    def data_collection_hook(self):
        """Main collection hook"""

        if self.aborted_by_user:
            self.collection_failed("Aborted by user")
            self.aborted_by_user = False
            return

        parameters = self.current_dc_parameters

        log = logging.getLogger("user_level_info")
        log.info("data collection parameters received %s" % parameters)

        for parameter in parameters:
            log.info("%s: %s" % (str(parameter), str(parameters[parameter])))

        osc_seq = parameters["oscillation_sequence"][0]
        fileinfo = parameters["fileinfo"]
        sample_reference = parameters["sample_reference"]
        experiment_type = parameters["experiment_type"]
        energy = parameters["energy"]
        transmission = parameters["transmission"]
        resolution = parameters["resolution"]

        exposure_time = osc_seq["exposure_time"]
        in_queue = parameters["in_queue"] != False

        overlap = osc_seq["overlap"]
        angle_per_frame = osc_seq["range"]
        scan_start_angle = osc_seq["start"]
        number_of_images = osc_seq["number_of_images"]
        image_nr_start = osc_seq["start_image_number"]

        directory = fileinfo["directory"]
        prefix = fileinfo["prefix"]
        template = fileinfo["template"]
        run_number = fileinfo["run_number"]
        process_directory = fileinfo["process_directory"]

        # space_group = str(sample_reference['space_group'])
        # unit_cell = list(eval(sample_reference['cell']))

        self.emit("collectStarted", (self.owner, 1))
        self.emit("progressInit", ("Data collection", 100))
        self.emit("fsmConditionChanged", "data_collection_started", True)

        self.store_image_in_lims_by_frame_num(1)

        name_pattern = template[:-8]

        if experiment_type == "OSC":
            scan_range = angle_per_frame * number_of_images
            scan_exposure_time = exposure_time * number_of_images
            experiment = omega_scan(
                name_pattern,
                directory,
                scan_range=scan_range,
                scan_exposure_time=scan_exposure_time,
                scan_start_angle=scan_start_angle,
                angle_per_frame=angle_per_frame,
                image_nr_start=image_nr_start,
                photon_energy=energy,
                transmission=transmission,
                resolution=resolution,
                simulation=False,
            )
            experiment.execute()

        elif experiment_type == "Characterization":

            number_of_wedges = osc_seq["number_of_images"]
            wedge_size = osc_seq["wedge_size"]
            overlap = osc_seq["overlap"]
            scan_start_angles = []
            scan_exposure_time = exposure_time * wedge_size
            scan_range = angle_per_frame * wedge_size

            for k in range(number_of_wedges):
                scan_start_angles.append(
                    scan_start_angle + k * -overlap + k * scan_range
                )

            experiment = reference_images(
                name_pattern,
                directory,
                scan_range=scan_range,
                scan_exposure_time=scan_exposure_time,
                scan_start_angles=scan_start_angles,
                angle_per_frame=angle_per_frame,
                image_nr_start=image_nr_start,
                photon_energy=energy,
                transmission=transmission,
                resolution=resolution,
                simulation=False,
            )

            experiment.execute()

        elif experiment_type == "Helical" and osc_seq["mesh_range"] == ():
            scan_range = angle_per_frame * number_of_images
            scan_exposure_time = exposure_time * number_of_images
            log.info("helical_pos %s" % self.helical_pos)
            experiment = helical_scan(
                name_pattern,
                directory,
                scan_range=scan_range,
                scan_exposure_time=scan_exposure_time,
                scan_start_angle=scan_start_angle,
                angle_per_frame=angle_per_frame,
                image_nr_start=image_nr_start,
                position_start=self.translate_position(self.helical_pos["1"]),
                position_end=self.translate_position(self.helical_pos["2"]),
                photon_energy=energy,
                transmission=transmission,
                resolution=resolution,
                simulation=False,
            )
            experiment.execute()

        elif experiment_type == "Helical" and osc_seq["mesh_range"] != ():
            horizontal_range, vertical_range = osc_seq["mesh_range"]

            experiment = xray_centring(name_pattern, directory)

            experiment.execute(simulation=False)

        elif experiment_type == "Mesh":
            number_of_columns = osc_seq["number_of_lines"]
            number_of_rows = int(number_of_images / number_of_columns)
            horizontal_range, vertical_range = osc_seq["mesh_range"]
            angle_per_line = angle_per_frame * number_of_columns
            experiment = raster_scan(
                name_pattern,
                directory,
                vertical_range,
                horizontal_range,
                number_of_rows,
                number_of_columns,
                frame_time=exposure_time,
                scan_start_angle=scan_start_angle,
                scan_range=angle_per_line,
                image_nr_start=image_nr_start,
                photon_energy=energy,
                transmission=transmission,
                simulation=False,
            )
            experiment.execute()

        # for image in range(number_of_images):
        # if self.aborted_by_user:
        # self.ready_event.set()
        # return

        # Uncomment to test collection failed
        # if image == 5:
        # self.emit("collectOscillationFailed", (self.owner, False,
        # "Failed on 5", parameters.get("collection_id")))
        # self.ready_event.set()
        # return

        # gevent.sleep(exposure_time)
        # self.emit("collectImageTaken", image)
        # self.emit("progressStep", (int(float(image) / number_of_images * 100)))

        self.emit_collection_finished()

    def translate_position(self, position):
        translation = {
            "sampx": "CentringX",
            "sampy": "CentringY",
            "phix": "AlignmentX",
            "phiy": "AlignmentY",
            "phiz": "AlignmentZ",
        }
        translated_position = {}
        for key in position:
            if key in translation:
                translated_position[translation[key]] = position[key]
            else:
                translated_position[key] = position[key]
        return translated_position

    def trigger_auto_processing(self, process_event, params_dict, frame_number):
        """
        Descript. :
        """
        if HWR.beamline.offline_processing is not None:
            HWR.beamline.offline_processing.execute_autoprocessing(
                process_event,
                self.current_dc_parameters,
                frame_number,
                self.run_offline_processing,
            )

    @task
    def _take_crystal_snapshot(self, filename):
        HWR.beamline.sample_view.save_snapshot(filename)

    @task
    def _take_crystal_animation(self, animation_filename, duration_sec):
        """Rotates sample by 360 and composes a gif file
           Animation is saved as the fourth snapshot
        """
        HWR.beamline.sample_view.save_scene_animation(animation_filename, duration_sec)

    @task
    def move_motors(self, motor_position_dict):
        """
        Descript. :
        """
        return

    def emit_collection_finished(self):
        """Collection finished beahviour
        """
        if self.current_dc_parameters["experiment_type"] != "Collect - Multiwedge":
            self.update_data_collection_in_lims()

            last_frame = self.current_dc_parameters["oscillation_sequence"][0][
                "number_of_images"
            ]
            if last_frame > 1:
                self.store_image_in_lims_by_frame_num(last_frame)
            if (
                self.current_dc_parameters["experiment_type"] in ("OSC", "Helical")
                and self.current_dc_parameters["oscillation_sequence"][0]["overlap"]
                == 0
                and last_frame > 19
            ):
                self.trigger_auto_processing("after", self.current_dc_parameters, 0)

        success_msg = "Data collection successful"
        self.current_dc_parameters["status"] = success_msg
        self.emit(
            "collectOscillationFinished",
            (
                self.owner,
                True,
                success_msg,
                self.current_dc_parameters.get("collection_id"),
                self.osc_id,
                self.current_dc_parameters,
            ),
        )
        self.emit("collectEnded", self.owner, success_msg)
        self.emit("collectReady", (True,))
        self.emit("progressStop", ())
        self.emit("fsmConditionChanged", "data_collection_successful", True)
        self.emit("fsmConditionChanged", "data_collection_started", False)
        self._collecting = None
        self.ready_event.set()

    def store_image_in_lims_by_frame_num(self, frame, motor_position_id=None):
        """
        Descript. :
        """
        image_id = None
        self.trigger_auto_processing("image", self.current_dc_parameters, frame)
        image_id = self.store_image_in_lims(frame)
        return image_id

    def stopCollect(self, owner="MXCuBE"):
        """
        Descript. :
        """
        self.aborted_by_user = True
        self.cmd_collect_abort()
        self.emit_collection_failed("Aborted by user")

    def set_helical_pos(self, helical_pos):
        self.helical_pos = helical_pos

    def get_slit_gaps(self):
        return self.get_slits_gap()

    def get_slits_gap(self):
        return self.slits1.get_horizontal_gap(), self.slits1.get_vertical_gap()
