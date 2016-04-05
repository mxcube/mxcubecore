#
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

"""
EMBLMultiCollect
"""
import os
import logging
import gevent
import p13_calc_flux
from HardwareRepository.TaskUtils import *
from HardwareRepository.BaseHardwareObjects import HardwareObject
from AbstractCollect import AbstractCollect


__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE colaboration"]

__version__ = "2.2."
__maintainer__ = "Ivars Karpics"
__email__ = "ivars.karpics[at]embl-hamburg.de"
__status__ = "Draft"


class EMBLCollect(AbstractCollect, HardwareObject):
    """
    Descript: Main data collection class. Inherited from AbstractMulticollect
              Collection is done by setting collection parameters and 
              executing collect command  
    """
    def __init__(self, name):
        """
        Descript. :
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
        

        self.chan_collect_status = None
        self.chan_collect_frame = None
        self.chan_collect_error = None
        self.chan_undulator_gap = None

        self.cmd_collect_description = None
        self.cmd_collect_detector = None
        self.cmd_collect_directory = None
        self.cmd_collect_energy = None
        self.cmd_collect_exposure_time = None
        self.cmd_collect_helical_position = None
        self.cmd_collect_in_queue = None
        self.cmd_collect_num_images = None
        self.cmd_collect_overlap = None
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
        """
        Descript. : 
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

        self.chan_collect_status = self.getChannelObject('collectStatus')
        self._actual_collect_status = self.chan_collect_status.getValue()
        self.chan_collect_status.connectSignal('update', self.collect_status_update)
        self.chan_collect_frame = self.getChannelObject('collectFrame')
        self.chan_collect_frame.connectSignal('update', self.collect_frame_update)
        self.chan_collect_error = self.getChannelObject('collectError')
        if self.chan_collect_error is not None:
            self.chan_collect_error.connectSignal('update', self.collect_error_update)

        self.chan_undulator_gap = self.getChannelObject('chanUndulatorGap')
 
        #Commands to set collection parameters
        self.cmd_collect_description = self.getCommandObject('collectDescription')
        self.cmd_collect_detector = self.getCommandObject('collectDetector')
        self.cmd_collect_directory = self.getCommandObject('collectDirectory')
        self.cmd_collect_energy = self.getCommandObject('collectEnergy')
        self.cmd_collect_exposure_time = self.getCommandObject('collectExposureTime')
        self.cmd_collect_helical_position = self.getCommandObject('collectHelicalPosition')
        self.cmd_collect_in_queue = self.getCommandObject('collectInQueue')
        self.cmd_collect_num_images = self.getCommandObject('collectNumImages')
        self.cmd_collect_overlap = self.getCommandObject('collectOverlap')
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
    
        #Collect start and abort commands
        self.cmd_collect_start = self.getCommandObject('collectStart')
        self.cmd_collect_abort = self.getCommandObject('collectAbort')

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True, ))

    def data_collection_hook(self):
        """
        Descript. : main collection command
        """
        p = self.current_dc_parameters
     
        if self._actual_collect_status in ["ready", "unknown", "error"]:
            self.emit("progressInit", ("Data collection", 100))
            comment = 'Comment: %s' % str(p.get('comments', ""))
            self._error_msg = ""
            self._collecting = True
            self.cmd_collect_description(comment)
            self.cmd_collect_detector(self.detector_hwobj.get_collect_name())
            self.cmd_collect_directory(str(p["fileinfo"]["directory"]))
            self.cmd_collect_exposure_time(p['oscillation_sequence'][0]['exposure_time'])
            self.cmd_collect_in_queue(p['in_queue'])
            self.cmd_collect_overlap(p['oscillation_sequence'][0]['overlap'])
            shutter_name = self.detector_hwobj.get_shutter_name()
            if shutter_name is not None:  
                self.cmd_collect_shutter(shutter_name)
            if p['oscillation_sequence'][0]['overlap'] == 0:
                self.cmd_collect_shutterless(1)
            else:
                self.cmd_collect_shutterless(0)
            self.cmd_collect_range(p['oscillation_sequence'][0]['range'])
            if p['experiment_type'] != 'Mesh':
                self.cmd_collect_num_images(p['oscillation_sequence'][0]['number_of_images'])
            self.cmd_collect_start_angle(p['oscillation_sequence'][0]['start'])
            self.cmd_collect_start_image(p['oscillation_sequence'][0]['start_image_number'])
            self.cmd_collect_template(str(p['fileinfo']['template']))
            space_group = str(p['sample_reference']['spacegroup'])
            if len(space_group) == 0:
                space_group = " "
            self.cmd_collect_space_group(space_group)
            unit_cell = list(eval(p['sample_reference']['cell']))
            self.cmd_collect_unit_cell(unit_cell)
            self.cmd_collect_scan_type(self.exp_type_dict.get(p['experiment_type'], 'OSC'))
            self.cmd_collect_start()
        else:
            self.emit_collection_failed()

            
    def collect_status_update(self, status):
        """
        Descript. : 
        """
        self._previous_collect_status = self._actual_collect_status
        self._actual_collect_status = status
        if self._collecting:
            if self._actual_collect_status == "error":
                self.emit_collection_failed()
            elif self._actual_collect_status == "collecting":
                self.store_image_in_lims_by_frame_num(1)
            if self._previous_collect_status is None:
                if self._actual_collect_status == 'busy':
                    logging.info("Preparing collecting...")  
            elif self._previous_collect_status == 'busy':
                if self._actual_collect_status == 'collecting':
                    self.emit("collectStarted", (self.owner, 1))
            elif self._previous_collect_status == 'collecting':
                if self._actual_collect_status == "ready":
                    self.emit_collection_finished()
                elif self._actual_collect_status == "aborting":
                    logging.info("Aborting...")
                    self.emit_collection_failed()

    def collect_error_update(self, error_msg):
        """
        Descrip. :
        """
        if (self._collecting and
            len(error_msg) > 0):
            self._error_msg = error_msg 
            #logging.info(error_msg) 
            logging.getLogger("user_level_log").error(error_msg)

    def emit_collection_failed(self):
        """
        Descrip. :
        """ 
        failed_msg = 'Data collection failed!'
        self.current_dc_parameters["status"] = failed_msg
        self.current_dc_parameters["comments"] = "%s\n%s" % (failed_msg, self._error_msg) 
        self.emit("collectOscillationFailed", (self.owner, False, 
             failed_msg, self.current_dc_parameters.get("collection_id"), self.osc_id))
        self.emit("collectEnded", self.owner, failed_msg)
        self.emit("collectReady", (True, ))
        self._collecting = None
        self.ready_event.set()

        self.update_data_collection_in_lims()

    def emit_collection_finished(self):  
        """
        Descript. :
        """
        success_msg = "Data collection successful"
        self.current_dc_parameters["status"] = success_msg
        self.emit("collectOscillationFinished", (self.owner, True, 
              success_msg, self.current_dc_parameters.get('collection_id'), 
              self.osc_id, self.current_dc_parameters))
        self.emit("collectEnded", self.owner, success_msg)
        self.emit("collectReady", (True, ))
        self.emit("progressStop", ()) 
        self._collecting = None
        self.ready_event.set()

        self.update_data_collection_in_lims()

        last_frame = self.current_dc_parameters['oscillation_sequence'][0]['number_of_images']
        if last_frame > 1:
            self.store_image_in_lims_by_frame_num(last_frame)
        if (self.current_dc_parameters['experiment_type'] in ('OSC', 'Helical') and
            self.current_dc_parameters['oscillation_sequence'][0]['overlap'] == 0 and
            self.current_dc_parameters['oscillation_sequence'][0]['number_of_images'] > 19):
            self.trigger_auto_processing("after", self.current_dc_parameters, 0)

    def update_lims_with_workflow(self, workflow_id, grid_snapshot_filename):
        if self.lims_client_hwobj is not None:
            try:
                self.current_dc_parameters["workflow_id"] = workflow_id
                self.current_dc_parameters["xtalSnapshotFullPath3"] = \
                     grid_snapshot_filename
                self.lims_client_hwobj.update_data_collection(self.current_dc_parameters)
            except:
                logging.getLogger("HWR").exception("Could not store data collection into ISPyB")

    def collect_frame_update(self, frame):
        """
        Descript. : 
        """
        if self._collecting: 
            self.collect_frame = frame
            number_of_images = self.current_dc_parameters\
                 ['oscillation_sequence'][0]['number_of_images']
            self.emit("progressStep", (int(float(frame) / number_of_images * 100)))
            self.emit("collectImageTaken", frame) 

    def store_image_in_lims_by_frame_num(self, frame, motor_position_id=None):
        """
        Descript. :
        """
        # Dont save mesh first and last images
        # Mesh images (best positions) are stored after data analysis
        if self.current_dc_parameters['experiment_type'] in ('Mesh') and \
           motor_position_id is None:
            return
        image_id = None

        self.trigger_auto_processing("image", self.current_dc_parameters, frame)
        image_id = self.store_image_in_lims(frame)
        return image_id 

    def trigger_auto_processing(self, process_event, params_dict, frame_number):
        """
        Descript. : 
        """
        if self.autoprocessing_hwobj is not None:
            self.autoprocessing_hwobj.execute_autoprocessing(process_event, 
                                                             self.current_dc_parameters,
                                                             frame_number)
    def stopCollect(self, owner):
        """
        Descript. :
        """
        if self._actual_collect_status == 'collecting':
            self.cmd_collect_abort()
            self.ready_event.set() 

    def set_helical_pos(self, arg):
        """
        Descript. : 8 floats describe
        p1AlignmY, p1AlignmZ, p1CentrX, p1CentrY
        p2AlignmY, p2AlignmZ, p2CentrX, p2CentrY               
        """
        helical_positions = [arg["1"]["phiy"],  arg["1"]["phiz"], 
                             arg["1"]["sampx"], arg["1"]["sampy"],
                             arg["2"]["phiy"],  arg["2"]["phiz"],
                             arg["2"]["sampx"], arg["2"]["sampy"]]
        self.cmd_collect_helical_position(helical_positions)       

    def setMeshScanParameters(self, num_lines, num_images_per_line, mesh_range):
        """
        Descript. : 
        """
        self.cmd_collect_raster_lines(num_lines)
        self.cmd_collect_num_images(num_images_per_line)        
        self.cmd_collect_raster_range(mesh_range[::-1])

    @task
    def _take_crystal_snapshot(self, filename):
        """
        Descript. : 
        """
        self.graphics_manager_hwobj.save_scene_snapshot(filename)

    def set_energy(self, value):
        """
        Descript. : 
        """
        self.cmd_collect_energy(value * 1000.0)

    def set_resolution(self, value):
        """
        Descript. : 
        """
        self.cmd_collect_resolution(value)

    def set_transmission(self, value):
        """
        Descript. : 
        """
        self.cmd_collect_transmission(value)

    def set_detector_roi_mode(self, roi_mode):
        """
        Descript. : 
        """
        if self.detector_hwobj is not None:
            self.detector_hwobj.set_collect_mode(roi_mode) 
        
    @task 
    def move_motors(self, motor_position_dict):
        """
        Descript. : 
        """        
        self.diffractometer_hwobj.move_motors(motor_position_dict)

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


    def get_wavelength(self):
        """
        Descript. : 
        """
        if self.energy_hwobj is not None:
            return self.energy_hwobj.getCurrentWavelength()

    def get_detector_distance(self):
        """
        Descript. : 
        """
        if self.detector_hwobj is not None:	
            return self.detector_hwobj.get_distance()

    def get_detector_distance_limits(self):
        """
        Descript. : 
        """
        if self.detector_hwobj is not None:
            return self.detector_hwobj.get_distance_limits()
       
    def get_resolution(self):
        """
        Descript. : 
        """
        if self.resolution_hwobj is not None:
            return self.resolution_hwobj.getPosition()

    def get_transmission(self):
        """
        Descript. : 
        """
        if self.transmission_hwobj is not None:
            return self.transmission_hwobj.getAttFactor()

    def get_undulators_gaps(self):
        """
        Descript. : return triplet with gaps. In our case we have one gap, 
                    others are 0        
        """
        #TODO 
        if self.chan_undulator_gap:
            und_gaps = self.chan_undulator_gap.getValue()
            if type(und_gaps) in (list, tuple):
                return und_gaps
            else: 
                return (und_gaps)
        else:
            return {} 

    def get_beam_size(self):
        """
        Descript. : 
        """
        if self.beam_info_hwobj is not None:
            return self.beam_info_hwobj.get_beam_size()

    def get_slit_gaps(self):
        """
        Descript. : 
        """
        if self.beam_info_hwobj is not None:
            return self.beam_info_hwobj.get_slits_gap()

    def get_beam_shape(self):
        """
        Descript. : 
        """
        if self.beam_info_hwobj is not None:
            return self.beam_info_hwobj.get_beam_shape()
    
    def get_measured_intensity(self):
        """
        Descript. : 
        """
        flux = None
        if self.lims_client_hwobj:
            if self.lims_client_hwobj.beamline_name == "P13":
                aperture_pos = self.beam_info_hwobj.get_aperture_pos_name()
                energy = self.energy_hwobj.getCurrentEnergy()
                #mode = self.bl_control.beam_info.get_focus_mode()
                mode = "large"

                #flux = p13_calc_flux.calculate_flux(aperture_pos, energy, mode) / 4.0
                #print p13_calc_flux.calculate_flux(aperture_pos, energy, mode)
                flux =  2.64E+11 
            else:
                fullflux = 3.5e12
                fullsize_hor = 1.200
                fullsize_ver =  0.700

                foc = self.beam_info_hwobj.get_focus_mode()

                if foc == 'unfocused':
                    flux = fullflux * self.get_beam_size()[0] * \
                           self.get_beam_size()[1] / fullsize_hor / fullsize_ver
                elif foc == 'horizontal':
                    flux = fullflux * self.get_beam_size()[1] / fullsize_ver
                elif foc == 'vertical':
                    flux = fullflux * self.get_beam_size()[0] / fullsize_hor
                elif foc == 'double':
                    flux = fullflux
                else:
                    flux = None
               # logging.getLogger("HWR").info("Flux in %s mode %e photon/sec" % \
               #     (self.beam_info_hwobj.get_focus_mode(), flux))
        return flux

    def get_machine_current(self):
        """
        Descript. : 
        """
        if self.machine_info_hwobj:
            return self.machine_info_hwobj.get_current()
        else:
            return 0

    def get_machine_message(self):
        """
        Descript. : 
        """
        if self.machine_info_hwobj:
            return self.machine_info_hwobj.get_message()
        else:
            return ''

    def get_machine_fill_mode(self):
        """
        Descript. : 
        """
        if self.machine_info_hwobj:
            fill_mode = str(self.machine_info_hwobj.get_message()) 
            return fill_mode[:20]
        else:
            return ''

    def getBeamlineConfiguration(self, *args):
        """
        Descript. : 
        """
        return self.bl_config._asdict()

    def get_flux(self):
        """
        Descript. : 
        """
        return self.get_measured_intensity()
