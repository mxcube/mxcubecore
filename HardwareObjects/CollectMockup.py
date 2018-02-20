#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import os
import time
import logging
import gevent
from HardwareRepository.TaskUtils import *
from HardwareRepository.BaseHardwareObjects import HardwareObject
from AbstractCollect import AbstractCollect


__credits__ = ["MXCuBE colaboration"]
__version__ = "2.2."


class CollectMockup(AbstractCollect, HardwareObject):
    """
    """
    def __init__(self, name):
        """

        :param name: name of the object
        :type name: string
        """

        AbstractCollect.__init__(self)
        HardwareObject.__init__(self, name)
        self._centring_status = None
        self._previous_collect_status = None
        self._actual_collect_status = None
        self.current_dc_parameters = None

        self.osc_id = None
        self.owner = None
        self._collecting = False
        self._error_msg = ""
        self._error_or_aborting = False
        self.collect_frame  = None
        self.ready_event = None

        self.exp_type_dict = None
        self.aborted_by_user = None 

        self.diffractometer_hwobj = None
        self.lims_client_hwobj = None
        self.machine_info_hwobj = None
        self.energy_hwobj = None
        self.resolution_hwobj = None
        self.transmission_hwobj = None
        self.detector_hwobj = None
        self.beam_info_hwobj = None
        self.autoprocessing_hwobj = None
        self.graphics_manager_hwobj = None

    def init(self):
        """Main init method
        """

        self.ready_event = gevent.event.Event()
        self.diffractometer_hwobj = self.getObjectByRole("diffractometer")
        self.lims_client_hwobj = self.getObjectByRole("lims_client")
        self.machine_info_hwobj = self.getObjectByRole("machine_info")
        self.energy_hwobj = self.getObjectByRole("energy")
        self.resolution_hwobj = self.getObjectByRole("resolution")
        self.transmission_hwobj = self.getObjectByRole("transmission")
        self.detector_hwobj = self.getObjectByRole("detector")
        self.beam_info_hwobj = self.getObjectByRole("beam_info")
        self.autoprocessing_hwobj = self.getObjectByRole("auto_processing")
        self.graphics_manager_hwobj = self.getObjectByRole("graphics_manager")
        self.sample_changer_hwobj = self.getObjectByRole("sample_changer")
        self.plate_manipulator_hwobj = self.getObjectByRole("plate_manipulator")

        undulators = []
        try:
            for undulator in self["undulators"]:
                undulators.append(undulator)
        except:
            pass  
        self.exp_type_dict = {'Mesh': 'raster',
                              'Helical': 'Helical'}
        self.set_beamline_configuration(\
             synchrotron_name = "EMBL-HH",
             directory_prefix = self.getProperty("directory_prefix"),
             default_exposure_time = self.detector_hwobj.getProperty("default_exposure_time"),
             minimum_exposure_time = self.detector_hwobj.getProperty("minimum_exposure_time"),
             detector_fileext = self.detector_hwobj.getProperty("fileSuffix"),
             detector_type = self.detector_hwobj.getProperty("type"),
             detector_manufacturer = self.detector_hwobj.getProperty("manufacturer"),
             detector_model = self.detector_hwobj.getProperty("model"),
             detector_px = self.detector_hwobj.getProperty("px"),
             detector_py = self.detector_hwobj.getProperty("py"),
             undulators = undulators,
             focusing_optic = self.getProperty('focusing_optic'),
             monochromator_type = self.getProperty('monochromator'),
             beam_divergence_vertical = self.beam_info_hwobj.get_beam_divergence_hor(),
             beam_divergence_horizontal = self.beam_info_hwobj.get_beam_divergence_ver(),
             polarisation = self.getProperty('polarisation'),
             input_files_server = self.getProperty("input_files_server"))

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True, ))

    def data_collection_hook(self):
        """Main collection hook
        """
        self.emit("collectStarted", (self.owner, 1)) 
        self.emit("fsmConditionChanged",
                  "data_collection_started",
                  True)
        self.store_image_in_lims_by_frame_num(1)
        number_of_images = self.current_dc_parameters\
            ['oscillation_sequence'][0]['number_of_images']
        for image in range(self.current_dc_parameters["oscillation_sequence"][0]["number_of_images"]):
            if self.aborted_by_user:
                self.ready_event.set()
                return

            #Uncomment to test collection failed
            #if image == 5:
            #    self.emit("collectOscillationFailed", (self.owner, False, 
            #       "Failed on 5", self.current_dc_parameters.get("collection_id")))
            #    self.ready_event.set()
            #    return

            time.sleep(self.current_dc_parameters["oscillation_sequence"][0]["exposure_time"])
            self.emit("collectImageTaken", image)
            self.emit("progressStep", (int(float(image) / number_of_images * 100)))
        self.emit_collection_finished()

    def emit_collection_finished(self):  
        """Collection finished beahviour
        """
        if self.current_dc_parameters['experiment_type'] != "Collect - Multiwedge":
            self.update_data_collection_in_lims()

            last_frame = self.current_dc_parameters['oscillation_sequence'][0]['number_of_images']
            if last_frame > 1:
                self.store_image_in_lims_by_frame_num(last_frame)
            if (self.current_dc_parameters['experiment_type'] in ('OSC', 'Helical') and
                self.current_dc_parameters['oscillation_sequence'][0]['overlap'] == 0 and
                last_frame > 19):
                self.trigger_auto_processing("after",
                                             self.current_dc_parameters,
                                             0)

        success_msg = "Data collection successful"
        self.current_dc_parameters["status"] = success_msg
        self.emit("collectOscillationFinished", (self.owner, True, 
              success_msg, self.current_dc_parameters.get('collection_id'), 
              self.osc_id, self.current_dc_parameters))
        self.emit("collectEnded", self.owner, success_msg)
        self.emit("collectReady", (True, ))
        self.emit("progressStop", ()) 
        self.emit("fsmConditionChanged",
                  "data_collection_successful",
                  True)
        self.emit("fsmConditionChanged",
                  "data_collection_started",
                  False)
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

    def update_lims_with_workflow(self, workflow_id, grid_snapshot_filename):
        """Updates collection with information about workflow

        :param workflow_id: workflow id
        :type workflow_id: int
        :param grid_snapshot_filename: grid snapshot file path
        :type grid_snapshot_filename: string
        """
        if self.lims_client_hwobj is not None:
            try:
                self.current_dc_parameters["workflow_id"] = workflow_id
                self.current_dc_parameters["xtalSnapshotFullPath3"] = \
                     grid_snapshot_filename
                self.lims_client_hwobj.update_data_collection(self.current_dc_parameters)
            except:
                logging.getLogger("HWR").exception("Could not store data collection into ISPyB")

    def trigger_auto_processing(self, process_event, params_dict, frame_number):
        """
        Descript. : 
        """
        if self.autoprocessing_hwobj is not None:
            self.autoprocessing_hwobj.execute_autoprocessing(process_event, 
                self.current_dc_parameters, frame_number, self.run_processing_after)

    def stopCollect(self, owner="MXCuBE"):
        """
        Descript. :
        """
        self.aborted_by_user = True 
        self.cmd_collect_abort()
        self.emit_collection_failed("Aborted by user")

    @task
    def _take_crystal_snapshot(self, filename):
        self.graphics_manager_hwobj.save_scene_snapshot(filename)

    @task
    def _take_crystal_animation(self, animation_filename, duration_sec):
        """Rotates sample by 360 and composes a gif file
           Animation is saved as the fourth snapshot
        """
        self.graphics_manager_hwobj.save_scene_animation(animation_filename, duration_sec)

    @task 
    def move_motors(self, motor_position_dict):
        """
        Descript. : 
        """        
        return

    def prepare_input_files(self):
        """
        Descript. : 
        """
        i = 1
        while True:
            xds_input_file_dirname = "xds_%s_%s_%d" % (\
                self.current_dc_parameters['fileinfo']['prefix'],
                self.current_dc_parameters['fileinfo']['run_number'],
                i)
            xds_directory = os.path.join(\
                self.current_dc_parameters['fileinfo']['process_directory'],
                xds_input_file_dirname)
            if not os.path.exists(xds_directory):
                break
            i += 1

        mosflm_input_file_dirname = "mosflm_%s_run%s_%d" % (\
                self.current_dc_parameters['fileinfo']['prefix'],
                self.current_dc_parameters['fileinfo']['run_number'],
                i)
        mosflm_directory = os.path.join(\
                self.current_dc_parameters['fileinfo']['process_directory'],
                mosflm_input_file_dirname)

        return xds_directory, mosflm_directory, ""
