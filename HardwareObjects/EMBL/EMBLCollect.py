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
import logging
import gevent
from HardwareRepository.TaskUtils import task
from AbstractCollect import AbstractCollect


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


class EMBLCollect(AbstractCollect):
    """Main data collection class. Inherited from AbstractCollect.
       Collection is done by setting collection parameters and
       executing collect command
    """
    def __init__(self, name):

        """
        :param name: name of the object
        :type name: string
        """

        AbstractCollect.__init__(self, name)
        self._previous_collect_status = None
        self._actual_collect_status = None

        self.use_still = None
        self.break_bragg_released = False

        self.aborted_by_user = None
        self.run_autoprocessing = None

        self.chan_collect_status = None
        self.chan_collect_frame = None
        self.chan_collect_error = None
        self.chan_undulator_gap = None

        self.cmd_collect_compression = None
        self.cmd_collect_description = None
        self.cmd_collect_detector = None
        self.cmd_collect_directory = None
        self.cmd_collect_energy = None
        self.cmd_collect_exposure_time = None
        self.cmd_collect_helical_position = None
        self.cmd_collect_in_queue = None
        self.cmd_collect_num_images = None
        self.cmd_collect_overlap = None
        self.cmd_collect_processing = None
        self.cmd_collect_range = None
        self.cmd_collect_raster_lines = None
        self.cmd_collect_raster_range = None
        self.cmd_collect_resolution = None
        self.cmd_collect_scan_type = None
        self.cmd_collect_shutter = None
        self.cmd_collect_shutterless = None
        self.cmd_collect_start_angle = None
        self.cmd_collect_start_image = None
        self.cmd_collect_template = None
        self.cmd_collect_transmission = None
        self.cmd_collect_space_group = None
        self.cmd_collect_unit_cell = None
        self.cmd_collect_start = None
        self.cmd_collect_abort = None
        self.cmd_collect_xds_data_range = None

        self.flux_hwobj = None
        self.graphics_manager_hwobj = None
        self.image_tracking_hwobj = None

    def init(self):
        """Main init method"""

        AbstractCollect.init(self)

        self.flux_hwobj = self.getObjectByRole("flux")
        self.graphics_manager_hwobj = self.getObjectByRole("graphics_manager")
        self.image_tracking_hwobj = self.getObjectByRole("image_tracking")


        self.exp_type_dict = {'Mesh': 'raster',
                              'Helical': 'Helical'}

        self.chan_collect_status = self.getChannelObject('collectStatus')
        self._actual_collect_status = self.chan_collect_status.getValue()
        self.chan_collect_status.connectSignal('update', self.collect_status_update)
        self.chan_collect_frame = self.getChannelObject('collectFrame')
        self.chan_collect_frame.connectSignal('update', self.collect_frame_update)
        self.chan_collect_error = self.getChannelObject('collectError')
        self.chan_collect_error.connectSignal('update', self.collect_error_update)
        self.chan_undulator_gap = self.getChannelObject('chanUndulatorGap')

        #Commands to set collection parameters
        self.cmd_collect_compression = self.getCommandObject('collectCompression')
        self.cmd_collect_description = self.getCommandObject('collectDescription')
        self.cmd_collect_detector = self.getCommandObject('collectDetector')
        self.cmd_collect_directory = self.getCommandObject('collectDirectory')
        self.cmd_collect_energy = self.getCommandObject('collectEnergy')
        self.cmd_collect_exposure_time = self.getCommandObject('collectExposureTime')
        self.cmd_collect_helical_position = self.getCommandObject('collectHelicalPosition')
        self.cmd_collect_in_queue = self.getCommandObject('collectInQueue')
        self.cmd_collect_num_images = self.getCommandObject('collectNumImages')
        self.cmd_collect_overlap = self.getCommandObject('collectOverlap')
        self.cmd_collect_processing = self.getCommandObject('collectProcessing')
        self.cmd_collect_range = self.getCommandObject('collectRange')
        self.cmd_collect_raster_lines = self.getCommandObject('collectRasterLines')
        self.cmd_collect_raster_range = self.getCommandObject('collectRasterRange')
        self.cmd_collect_resolution = self.getCommandObject('collectResolution')
        self.cmd_collect_scan_type = self.getCommandObject('collectScanType')
        self.cmd_collect_shutter = self.getCommandObject('collectShutter')
        self.cmd_collect_shutterless = self.getCommandObject('collectShutterless')
        self.cmd_collect_start_angle = self.getCommandObject('collectStartAngle')
        self.cmd_collect_start_image = self.getCommandObject('collectStartImage')
        self.cmd_collect_template = self.getCommandObject('collectTemplate')
        self.cmd_collect_transmission = self.getCommandObject('collectTransmission')
        self.cmd_collect_space_group = self.getCommandObject('collectSpaceGroup')
        self.cmd_collect_unit_cell = self.getCommandObject('collectUnitCell')
        self.cmd_collect_xds_data_range = self.getCommandObject('collectXdsDataRange')

        #Collect start and abort commands
        self.cmd_collect_start = self.getCommandObject('collectStart')
        self.cmd_collect_abort = self.getCommandObject('collectAbort')

        #Other commands

        #Properties
        self.use_still = self.getProperty("use_still")

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True, ))

    def data_collection_hook(self):
        """Main collection hook"""

        if self.aborted_by_user:
            self.collection_failed("Aborted by user")
            self.aborted_by_user = False
            return

        if self._actual_collect_status in ["ready", "unknown", "error", "not available"]:
            #self.emit("progressInit", ("Collection", 100, False))
            self.diffractometer_hwobj.save_centring_positions()
            comment = 'Comment: %s' % str(self.current_dc_parameters.get('comments', ""))
            self._error_msg = ""
            self._collecting = True

            osc_seq = self.current_dc_parameters['oscillation_sequence'][0]
            file_info = self.current_dc_parameters["fileinfo"]
            sample_ref = self.current_dc_parameters['sample_reference']

            if self.image_tracking_hwobj is not None:
                self.image_tracking_hwobj.set_image_tracking_state(True)

            if self.cmd_collect_compression is not None:
                self.cmd_collect_compression(file_info["compression"])
            self.cmd_collect_description(comment)
            self.cmd_collect_detector(self.detector_hwobj.get_collect_name())
            self.cmd_collect_directory(str(file_info["directory"]))
            self.cmd_collect_exposure_time(osc_seq['exposure_time'])
            self.cmd_collect_in_queue(self.current_dc_parameters['in_queue'] != False)
            self.cmd_collect_overlap(osc_seq['overlap'])
            shutter_name = self.detector_hwobj.get_shutter_name()
            if shutter_name is not None:
                self.cmd_collect_shutter(shutter_name)

            if osc_seq['overlap'] == 0:
                self.cmd_collect_shutterless(1)
            else:
                self.cmd_collect_shutterless(0)
            self.cmd_collect_range(osc_seq['range'])
            if self.current_dc_parameters['experiment_type'] != 'Mesh':
                self.cmd_collect_num_images(osc_seq['number_of_images'])

            if self.cmd_collect_processing is not None:
                #self.cmd_collect_processing(self.current_dc_parameters["processing_parallel"] in ("MeshScan", "XrayCentering"))
                self.cmd_collect_processing(self.current_dc_parameters["processing_parallel"] is not None)
            self.cmd_collect_start_angle(osc_seq['start'])
            self.cmd_collect_start_image(osc_seq['start_image_number'])
            self.cmd_collect_template(str(file_info['template']))
            space_group = str(sample_ref['spacegroup'])
            if len(space_group) == 0:
                space_group = " "
            self.cmd_collect_space_group(space_group)
            unit_cell = list(eval(sample_ref['cell']))
            self.cmd_collect_unit_cell(unit_cell)

            if self.current_dc_parameters['experiment_type'] == 'OSC':
                xds_range = (osc_seq['start_image_number'],
                             osc_seq['start_image_number'] + \
                             osc_seq['number_of_images'] - 1)
                self.cmd_collect_xds_data_range(xds_range)
            elif self.current_dc_parameters['experiment_type'] == "Collect - Multiwedge":
                xds_range = self.current_dc_parameters['in_interleave']
                self.cmd_collect_xds_data_range(xds_range)

            if self.use_still:
                self.cmd_collect_scan_type("still")
            else:
                self.cmd_collect_scan_type(self.exp_type_dict.get(\
                    self.current_dc_parameters['experiment_type'], 'OSC'))
            self.cmd_collect_start()
        else:
            self.collection_failed(\
                 "Unable to start collection. " + \
                 "Detector server is in %s state" % \
                 self._actual_collect_status)

    def collect_status_update(self, status):
        """Status event that controls execution

        :param status: collection status
        :type status: string
        """

        self._previous_collect_status = self._actual_collect_status
        self._actual_collect_status = status
        if self._collecting:
            if self._actual_collect_status == "error":
                self.collection_failed()
            elif self._actual_collect_status == "collecting":
                if self.current_dc_parameters['experiment_type'] != 'Mesh':
                    self.store_image_in_lims_by_frame_num(1)
            if self._previous_collect_status is None:
                if self._actual_collect_status == 'busy':
                    logging.info("Collection: Preparing ...")
            elif self._previous_collect_status == 'busy':
                if self._actual_collect_status == 'collecting':
                    self.emit("collectStarted", (None, 1))
            elif self._previous_collect_status == 'collecting':
                if self._actual_collect_status == "ready":
                    self.collection_finished()
                elif self._actual_collect_status == "aborting":
                    logging.info("Collection: Aborting...")
                    self.collection_failed()

    def collect_error_update(self, error_msg):
        """Collect error behaviour

        :param error_msg: error message
        :type error_msg: string
        """

        if (self._collecting and
            len(error_msg) > 0):
            self._error_msg = error_msg
            logging.getLogger("GUI").error("Collection: Error from detector server: %s" % error_msg)

    def collection_finished(self):
        AbstractCollect.collection_finished(self)
        if self.current_dc_parameters['in_queue'] is False and \
            self.break_bragg_released:
            self.break_bragg_released = False
            self.energy_hwobj.set_break_bragg() 

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
                logging.getLogger("HWR").exception(\
                     "Could not store data collection into ISPyB")

    def collect_frame_update(self, frame):
        """Image frame update

        :param frame: frame num.
        :type frame: int
        """
        if self._collecting:
            number_of_images = self.current_dc_parameters\
              ['oscillation_sequence'][0]['number_of_images']
            self.emit("progressStep", (int(float(frame) / number_of_images * 100)))
            self.emit("collectImageTaken", frame)

    def store_image_in_lims_by_frame_num(self, frame, motor_position_id=None):
        """Store image in lims

        :param frame: dict with frame parameters
        :type frame: dict
        :param motor_position_id: position id
        :type motor_position_id: int
        """
        self.trigger_auto_processing("image", self.current_dc_parameters, frame)

        return self.store_image_in_lims(frame)

    def trigger_auto_processing(self, process_event, params_dict, frame_number):
        """Starts autoprocessing"""
        self.autoprocessing_hwobj.execute_autoprocessing(process_event,
             self.current_dc_parameters, frame_number, self.run_processing_after)

    def stopCollect(self, owner="MXCuBE"):
        """Stops collect"""

        self.aborted_by_user = True
        self.cmd_collect_abort()
        self.collection_failed("Aborted by user")
        #self.ready_event.set()

    def set_helical_pos(self, arg):
        """Sets helical positions
           8 floats describe:
             p1AlignmY, p1AlignmZ, p1CentrX, p1CentrY
             p2AlignmY, p2AlignmZ, p2CentrX, p2CentrY
        """
        helical_positions = [arg["1"]["phiy"], arg["1"]["phiz"],
                             arg["1"]["sampx"], arg["1"]["sampy"],
                             arg["2"]["phiy"], arg["2"]["phiz"],
                             arg["2"]["sampx"], arg["2"]["sampy"]]
        self.cmd_collect_helical_position(helical_positions)

    def set_mesh_scan_parameters(self, num_lines, num_total_frames, mesh_center, mesh_range):
        """Sets mesh parameters"""
        self.cmd_collect_raster_lines(num_lines)
        self.cmd_collect_num_images(num_total_frames / num_lines)
        self.cmd_collect_raster_range(mesh_range[::-1])

    @task
    def _take_crystal_snapshot(self, filename):
        """Saves crystal snapshot"""
        self.graphics_manager_hwobj.save_scene_snapshot(filename)

    @task
    def _take_crystal_animation(self, animation_filename, duration_sec=1):
        """Rotates sample by 360 and composes a gif file
           Animation is saved as the fourth snapshot
        """

        return
        #self.graphics_manager_hwobj.save_scene_animation(animation_filename,
        #                                                 duration_sec)

    def set_energy(self, value):
        """Sets energy"""
        if abs(value - self.get_energy()) > 0.001 and not \
           self.break_bragg_released:
            self.break_bragg_released = True
            self.energy_hwobj.release_break_bragg()
            
        self.cmd_collect_energy(value * 1000.0)

    def get_energy(self):
        """Returns energy value in keV"""
        return self.energy_hwobj.getCurrentEnergy()

    def set_resolution(self, value):
        """Sets resolution in A"""
        self.cmd_collect_resolution(value)

    def set_transmission(self, value):
        """Sets transmission in %"""
        self.cmd_collect_transmission(value)

    def set_detector_roi_mode(self, roi_mode):
        """Sets detector ROI mode

        :param roi_mode: roi mode
        :type roi_mode: str (0, C2, ..)
        """
        if self.detector_hwobj is not None:
            self.detector_hwobj.set_collect_mode(roi_mode)

    @task
    def move_motors(self, motor_position_dict):
        """Move to centred position"""
        self.diffractometer_hwobj.move_motors(motor_position_dict)

    def prepare_input_files(self):
        """Prepares xds and mosfl directories"""
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
        self.current_dc_parameters["xds_dir"] = xds_directory

        mosflm_input_file_dirname = "mosflm_%s_run%s_%d" % (\
                self.current_dc_parameters['fileinfo']['prefix'],
                self.current_dc_parameters['fileinfo']['run_number'],
                i)
        mosflm_directory = os.path.join(\
                self.current_dc_parameters['fileinfo']['process_directory'],
                mosflm_input_file_dirname)

        return xds_directory, mosflm_directory, ""


    def get_wavelength(self):
        """Returns wavelength"""
        if self.energy_hwobj is not None:
            return self.energy_hwobj.getCurrentWavelength()

    def get_detector_distance(self):
        """Returns detector distance in mm"""
        if self.detector_hwobj is not None:
            return self.detector_hwobj.get_distance()

    def get_detector_distance_limits(self):
        """Returns detector distance limits"""
        if self.detector_hwobj is not None:
            return self.detector_hwobj.get_distance_limits()

    def get_resolution(self):
        """Returns resolution in A"""
        if self.resolution_hwobj is not None:
            return self.resolution_hwobj.getPosition()

    def get_transmission(self):
        """Returns transmision in %"""
        if self.transmission_hwobj is not None:
            return self.transmission_hwobj.getAttFactor()

    def get_undulators_gaps(self):
        """Return triplet with gaps. In our case we have one gap,
        """
        if self.chan_undulator_gap:
            und_gaps = self.chan_undulator_gap.getValue()
            if type(und_gaps) in (list, tuple):
                return und_gaps
            else:
                return (und_gaps)
        else:
            return {}

    def get_measured_intensity(self):
        """Returns flux"""
        return float("%.3e" % self.flux_hwobj.get_flux())

    def get_machine_current(self):
        """Returns flux"""
         
        if self.machine_info_hwobj:
            return self.machine_info_hwobj.get_current()
        else:
            return 0

    def get_machine_message(self):
        """Returns machine message"""
        if self.machine_info_hwobj:
            return self.machine_info_hwobj.get_message()
        else:
            return ''

    def get_machine_fill_mode(self):
        """Returns machine filling mode"""
        if self.machine_info_hwobj:
            fill_mode = str(self.machine_info_hwobj.get_message())
            return fill_mode[:20]
        else:
            return ''

    def getBeamlineConfiguration(self, *args):
        """Returns beamline config"""
        return self.bl_config._asdict()

    def get_flux(self):
        """Returns flux"""
        return self.get_measured_intensity()

    def set_run_autoprocessing(self, status):
        """Enables or disables autoprocessing after a collection"""
        self.run_autoprocessing = status
