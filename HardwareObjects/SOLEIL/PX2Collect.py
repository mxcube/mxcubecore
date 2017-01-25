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
PX2Collect
"""
import os
import logging
import gevent
from HardwareRepository.TaskUtils import *
from HardwareRepository.BaseHardwareObjects import HardwareObject
from AbstractCollect import AbstractCollect

from eiger import detector, goniometer
import eiger

__author__ = "laurent gadea"
__credits__ = ["MXCuBE colaboration"]
__version__ = "0."


class PX2Collect(AbstractCollect, HardwareObject):
    """Main data collection class. Inherited from AbstractMulticollect
       Collection is done by setting collection parameters and 
       executing collect command  
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

        # a redefinir #######################
        
        #hwobj -----------------------------------------------
        # all in AbstracCollect yet !!!! except graphics_manager_hwobj
        #pour l'instant detector>xml pointe vers un detector mockup la distance est recup par le Hwobj detectordistance
        self.detector_hwobj = None
        self.diffractometer_hwobj = None

        self.lims_client_hwobj = None
        self.machine_info_hwobj = None #rebaptise machine_current
        self.energy_hwobj = None
        self.resolution_hwobj = None
        self.transmission_hwobj = None
        self.beam_info_hwobj = None
        self.autoprocessing_hwobj = None
        
        self.graphics_manager_hwobj = None
        
        #hwobj PX2
        self.headerdev     = DeviceProxy( self.headername )
        #----> distance du detector !!!!!!!
        self.detector_distance_hwobj = None
        #self.undulators_hwobj = None
        self.flux_hwobj = None
        
        
        

    def init(self):
        """Main init method
        """

        self.ready_event = gevent.event.Event()
                               
        # no beamlineControl !!!!!!!!!
                               
        self.diffractometer_hwobj = self.getObjectByRole("diffractometer")
        self.lims_client_hwobj = self.getObjectByRole("dbserve")#self.getObjectByRole("lims_client")# avoir dans le xml dbserver 
        self.machine_info_hwobj = self.getObjectByRole("machine_info")
        self.energy_hwobj = self.getObjectByRole("energy")
        self.resolution_hwobj = self.getObjectByRole("resolution")
        self.transmission_hwobj = self.getObjectByRole("transmission")
        
        self.detector_hwobj = self.getObjectByRole("detector")
        self.beam_info_hwobj = self.getObjectByRole("beam_info")
        self.autoprocessing_hwobj = self.getObjectByRole("auto_processing")
        self.graphics_manager_hwobj = self.getObjectByRole("graphics_manager")
        self.sample_changer_hwobj = self.getObjectByRole("sample_changer")
        
        #PX2
        self.flux_hwobj              = elf.getObjectByRole("flux")
        self.safety_shutter_hwobj    = self.getObjectByRole("safety_shutter")#?
        self.cryo_stream_hwobj       = self.getObjectByRole("cryo_stream")#?
        self.detector_distance_hwobj = self.getObjectByRole("detector_distance")#??? a voir plus tard si inegrqtion dans detector_hwobj
        
        #pas de getObjectByRole("undulators") reste [] mais pas None
        undulators = []
        try:
            for undulator in self["undulators"]:
                undulators.append(undulator)
        except:
            pass  

        #sc
        self.exp_type_dict = {'Mesh': 'raster',
                              'Helical': 'Helical'}
#==============================================================================
#                               en attendant GODO ou pire !!!! plutot un vrai detector.xml
#==============================================================================
#==============================================================================
#         self.set_beamline_configuration(\
#              synchrotron_name = "SOLEIL-PX2",
#              directory_prefix = self.getProperty("directory_prefix"),
#              default_exposure_time = self.detector_hwobj.getProperty("default_exposure_time"),
#              minimum_exposure_time = self.detector_hwobj.getProperty("minimum_exposure_time"),
#              detector_fileext = self.detector_hwobj.getProperty("fileSuffix"),
#              detector_type = self.detector_hwobj.getProperty("type"),
#              detector_manufacturer = self.detector_hwobj.getProperty("manufacturer"),
#              detector_model = self.detector_hwobj.getProperty("model"),
#              detector_px = self.detector_hwobj.getProperty("px"),
#              detector_py = self.detector_hwobj.getProperty("py"),
#              undulators = self.undulators_hwobj,
#              focusing_optic = self.getProperty('focusing_optic'),
#              monochromator_type = self.getProperty('monochromator'),
#              beam_divergence_vertical = self.beam_info_hwobj.get_beam_divergence_hor(),
#              beam_divergence_horizontal = self.beam_info_hwobj.get_beam_divergence_ver(),
#              polarisation = self.getProperty('polarisation'),
#              input_files_server = self.getProperty("input_files_server"))
#==============================================================================
                                      detector_type = bcm_pars["detector"].getProperty("type"),
                                      detector_mode = spec_pars["detector"].getProperty("binning"),####### >>> ISPYBCLIENT queue_model_object
                                      detector_manufacturer = bcm_pars["detector"].getProperty("manufacturer"),
                                      detector_model = bcm_pars["detector"].getProperty("model"),
                                      detector_px = bcm_pars["detector"].getProperty("px"),
                                      detector_py = bcm_pars["detector"].getProperty("py"),
        self.set_beamline_configuration(\
             synchrotron_name = "SOLEIL-PX2",
             directory_prefix = self.getProperty("directory_prefix"),
             default_exposure_time = bcm_pars["detector"].getProperty("default_exposure_time"),##
             minimum_exposure_time = bcm_pars["detector"].getProperty("minimum_exposure_time"),##
             detector_fileext = bcm_pars["detector"].getProperty("FileSuffix"),##
             #detector_type = self.detector_hwobj.getProperty("type"),
             detector_type = bcm_pars["detector"].getProperty("type"),
             #detector_manufacturer = self.detector_hwobj.getProperty("manufacturer"),
             detector_manufacturer = bcm_pars["detector"].getProperty("manufacturer")
             #detector_model = self.detector_hwobj.getProperty("model"),
             #detector_px = self.detector_hwobj.getProperty("px"),
             #detector_py = self.detector_hwobj.getProperty("py"),
             detector_model = bcm_pars["detector"].getProperty("model"),
             detector_px = bcm_pars["detector"].getProperty("px"),
             detector_py = sbcm_pars["detector"].getProperty("py"),
             undulators = self.undulators_hwobj,
             focusing_optic = self.getProperty('focusing_optic'),
             monochromator_type = self.getProperty('monochromator'),
             beam_divergence_vertical = self.beam_info_hwobj.get_beam_divergence_hor(),
             beam_divergence_horizontal = self.beam_info_hwobj.get_beam_divergence_ver(),
             polarisation = self.getProperty('polarisation'),
             input_files_server = self.getProperty("input_files_server"))
#==============================================================================
# 
#         self.chan_collect_status = self.getChannelObject('collectStatus')
#         self._actual_collect_status = self.chan_collect_status.getValue()
#         self.chan_collect_status.connectSignal('update', self.collect_status_update)
#         self.chan_collect_frame = self.getChannelObject('collectFrame')
#         self.chan_collect_frame.connectSignal('update', self.collect_frame_update)
#         self.chan_collect_error = self.getChannelObject('collectError')
#         if self.chan_collect_error is not None:
#             self.chan_collect_error.connectSignal('update', self.collect_error_update)
# 
#         self.chan_undulator_gap = self.getChannelObject('chanUndulatorGap')
#         self.chan_guillotine_state = self.getChannelObject('guillotineState')
#         
#         if self.chan_guillotine_state is not None:
#             self.chan_guillotine_state.connectSignal('update', self.guillotine_state_changed)
#==============================================================================
 
#==============================================================================
#         #Commands to set collection parameters
#         self.cmd_collect_description = self.getCommandObject('collectDescription')
#         self.cmd_collect_detector = self.getCommandObject('collectDetector')
#         self.cmd_collect_directory = self.getCommandObject('collectDirectory')
#         self.cmd_collect_energy = self.getCommandObject('collectEnergy')
#         self.cmd_collect_exposure_time = self.getCommandObject('collectExposureTime')
#         self.cmd_collect_helical_position = self.getCommandObject('collectHelicalPosition')
#         self.cmd_collect_in_queue = self.getCommandObject('collectInQueue')
#         self.cmd_collect_num_images = self.getCommandObject('collectNumImages')
#         self.cmd_collect_overlap = self.getCommandObject('collectOverlap')
#         self.cmd_collect_range = self.getCommandObject('collectRange')
#         self.cmd_collect_raster_lines = self.getCommandObject('collectRasterLines')
#         self.cmd_collect_raster_range = self.getCommandObject('collectRasterRange')
#         self.cmd_collect_resolution = self.getCommandObject('collectResolution')
#         self.cmd_collect_scan_type = self.getCommandObject('collectScanType')
#         self.cmd_collect_shutter = self.getCommandObject('collectShutter')
#         self.cmd_collect_shutterless = self.getCommandObject('collectShutterless')
#         self.cmd_collect_start_angle = self.getCommandObject('collectStartAngle')
#         self.cmd_collect_start_image = self.getCommandObject('collectStartImage')
#         self.cmd_collect_template = self.getCommandObject('collectTemplate')
#         self.cmd_collect_transmission = self.getCommandObject('collectTransmission')
#         self.cmd_collect_space_group = self.getCommandObject('collectSpaceGroup')
#         self.cmd_collect_unit_cell = self.getCommandObject('collectUnitCell')
#         self.cmd_collect_xds_data_range = self.getCommandObject('collectXdsDataRange')
#     
#         #Collect start and abort commands
#         self.cmd_collect_start = self.getCommandObject('collectStart')
#         self.cmd_collect_abort = self.getCommandObject('collectAbort')
# 
#         #Other commands
#         self.cmd_close_guillotine = self.getCommandObject('cmdCloseGuillotine')
#         self.cmd_set_calibration_name = self.getCommandObject('cmdSetCallibrationName')
#==============================================================================

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True, ))
    
    def set_beamline_configuration(self, **configuration_parameters):
        self.bl_config = BeamlineConfig(**configuration_parameters)
    # A REECRIRE !!!
    def data_collection_hook(self):
        """Main collection hook A REECRIRE !!!!!!!!!!!!!!!!!!!!!!!!!!111
        """

        #self.detector_hwobj.prepare_for_collect()

        #self.minidiff_hwobj.prepare_for_collect(collection_type)

        if self.is_helical:
            self.minidiff_hwobj.start_helical_scan()
        elif self.is_mesh:
            self.minidiff_hwobj.start_mesh_scan()
        else:
            self.minidiff_hwobj.start_scan()

  
        # ---- FORGET ANYTHHING FROM HERE

        if self.aborted_by_user:
            self.emit_collection_failed("Aborted by user")
            self.aborted_by_user = False
            return
        #ecoute etadu device COLLECT si ready
        if self._actual_collect_status in ["ready", "unknown", "error"]:
            self.emit("progressInit", ("Data collection", 100)) # envoie vers ProgressBar brick
            
            comment = 'Comment: %s' % str(self.current_dc_parameters.get('comments', ""))
            
            self._error_msg = ""
            self._collecting = True

            osc_seq = self.current_dc_parameters['oscillation_sequence'][0]
            
            self.cmd_collect_in_queue(self.current_dc_parameters['in_queue'])
            self.cmd_collect_overlap(osc_seq['overlap'])
            shutter_name = self.detector_hwobj.get_shutter_name()
            if shutter_name is not None:  
                self.cmd_collect_shutter(shutter_name)

            calibration_name = self.beam_info_hwobj.get_focus_mode()
            if calibration_name and self.cmd_set_calibration_name:
                self.cmd_set_calibration_name(calibration_name)

            if osc_seq['overlap'] == 0:
                self.cmd_collect_shutterless(1)
            else:
                self.cmd_collect_shutterless(0)
            self.cmd_collect_range(osc_seq['range'])
            if self.current_dc_parameters['experiment_type'] != 'Mesh':
                self.cmd_collect_num_images(osc_seq['number_of_images'])
            self.cmd_collect_start_angle(osc_seq['start'])
            self.cmd_collect_start_image(osc_seq['start_image_number'])
            self.cmd_collect_template(str(self.current_dc_parameters['fileinfo']['template']))
            space_group = str(self.current_dc_parameters['sample_reference']['spacegroup'])
            if len(space_group) == 0:
                space_group = " "
            self.cmd_collect_space_group(space_group)
            unit_cell = list(eval(self.current_dc_parameters['sample_reference']['cell']))
            self.cmd_collect_unit_cell(unit_cell)

            if self.current_dc_parameters['experiment_type'] == 'OSC':
                xds_range = (osc_seq['start_image_number'],
                             osc_seq['start_image_number'] + \
                             osc_seq['number_of_images'] - 1)
                self.cmd_collect_xds_data_range(xds_range)
            elif self.current_dc_parameters['experiment_type'] == "Collect - Multiwedge":
                xds_range = self.current_dc_parameters['in_interleave']
                self.cmd_collect_xds_data_range(xds_range)

            self.cmd_collect_scan_type(self.exp_type_dict.get(\
                 self.current_dc_parameters['experiment_type'], 'OSC'))
            #self.cmd_collect_scan_type("still")
            self.cmd_collect_start()
        else:
            self.emit_collection_failed("Detector server not in unknown state")


    #PAS UTILISABLE PAS DE DEVICE COLLECT
    def collect_status_update(self, status):
        """Status event that controls execution

        :param status: collection status
        :type status: string
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
                    
    #PAS UTILISABLE PAS DE DEVICE COLLECT
    def collect_error_update(self, error_msg):
        """Collect error behaviour

        :param error_msg: error message
        :type error_msg: string
        """

        if (self._collecting and
            len(error_msg) > 0):
            self._error_msg = error_msg 
            logging.getLogger("user_level_log").error(error_msg)

    def emit_collection_failed(self, failed_msg=None):
        """Collection failed method
        """ 
        if not failed_msg:
            failed_msg = 'Data collection failed!'
        self.current_dc_parameters["status"] = failed_msg
        self.current_dc_parameters["comments"] = "%s\n%s" % (failed_msg, self._error_msg) 
        #self.emit("collectOscillationFailed", (self.owner, False, 
        #     failed_msg, self.current_dc_parameters.get("collection_id"), self.osc_id))
        self.emit("collectEnded", self.owner, failed_msg)
        self.emit("collectReady", (True, ))
        self.emit("progressStop", ())
        self._collecting = None
        self.ready_event.set()
        self.update_data_collection_in_lims()
#==============================================================================
#         #PAS UTILISABLE PAS DE DEVICE COLLECT
#==============================================================================
    def guillotine_state_changed(self, state):
        pass
        #if state[1] == 0:
        #    self.guillotine_state = "closed"
        #elif state[1] == 1:
        #    self.guillotine_state = "opened"
        #elif state[1] == 2:
        #    self.guillotine_state = "closing"
        #elif state[1] == 3:
        #    self.guillotine_state = "opening"

#==============================================================================
#     fin de collect
#==============================================================================
    
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
                #WARNINGGGGG
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
        self._collecting = None
        self.ready_event.set()
    
    #PAS UTILISABLE PAS DE DEVICE COLLECT
    #from ParalleleProcessing !!!!!!!!!
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
    
    #channel update a adapter PX2 #PAS UTILISABLE PAS DE DEVICE COLLECT
    def collect_frame_update(self, frame):
        """Image frame update  A REECRIRE !!!!!!!!!!!!!!!!!!!!!!!!!!111
        """

        if self._collecting: 
            self.collect_frame = frame
            number_of_images = self.current_dc_parameters\
                 ['oscillation_sequence'][0]['number_of_images']
            self.emit("progressStep", (int(float(frame) / number_of_images * 100)))
            self.emit("collectImageTaken", frame) 

    def store_image_in_lims_by_frame_num(self, frame, motor_position_id=None):
        """
        Descript. : A REECRIRE !!!!!!!!!!!!!!!!!!!!!!!!!!111
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
        Descript. : APPEL  autoprocessing_hwobj traitement des resultats plus EDN mais GRIDSCAN par exemple
        """
        self.autoprocessing_hwobj.execute_autoprocessing(process_event, 
             self.current_dc_parameters, frame_number, self.run_processing_after)
    
    @task
    # Fait 
    def stop_acquisition(self):
        logging.info("<SOLEIL MultiCollect> stop acquisition " )
        self.bl_control.diffractometer.stop_acquisition()
        return self._detector.stop_acquisition()
    
    # Fait !!
    def stop_collect(self, owner="MXCuBE"):
        """
        Descript. : SOLEILMULTICOLLECT
        
        """
        self.aborted_by_user = True
        #self.ready_event.set()
        self.stop_acquisition()
        if self.data_collect_task is not None:
            self.data_collect_task.kill(block = False)
        
    #OK!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    def set_helical_pos(self, arg):
        """
        appele dans queue_entry collect_dc !!!!! in PX2 remplace par set_helical !!!!!
        Descript. : 8 floats describe
        p1AlignmY, p1AlignmZ, p1CentrX, p1CentrY
        p2AlignmY, p2AlignmZ, p2CentrX, p2CentrY
        """
        pass
#==============================================================================
#         helical_positions = [arg["1"]["phiy"],  arg["1"]["phiz"], 
#                              arg["1"]["sampx"], arg["1"]["sampy"],
#                              arg["2"]["phiy"],  arg["2"]["phiz"],
#                              arg["2"]["sampx"], arg["2"]["sampy"]]
#         self.cmd_collect_helical_position(helical_positions)
#==============================================================================
    #OK!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    def set_helical(self, onmode, positions=None, posmot=None):
        logging.info("<PX2 MultiCollect> set helical onmode is %s position is %s posmot is %s" % (str(onmode) , str(positions), str(posmot)))
        self.helical = onmode
        if positions is None and posmot is None:
            return
        if onmode:
            logging.info("<PX2 MultiCollect> set helical pos1 %s pos2 %s" % (str(positions['1']), str(positions['2'])))
            self.helicalStart = positions['1']
            self.helicalFinal = positions['2']
            self.hs_start = posmot['1']
            self.hs_final = posmot['2']
        #self.goniometer.set_helical_start() goniometer = md2
        #self.bl_control.diffractometer.moveToCentredPosition(self.hs_start) => md2
        #self.bl_control.diffractometer.wait() => md2
        #self.goniometer.set_helical_start() => md2
        #def set_helical_start(self):
        #return self.md2.setstartscan4d()
    
        #def set_helical_stop(self):
        #return self.md2.setstopscan4d()    

    #OK!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    def setMeshScanParameters(self, num_lines, num_images_per_line, mesh_range):
        """
        Descript. : appel dans queue_entry 
        """
#==============================================================================
#         self.cmd_collect_raster_lines(num_lines)
#         self.cmd_collect_num_images(num_images_per_line)        
#         self.cmd_collect_raster_range(mesh_range[::-1])#???
#==============================================================================

        self.num_images_per_line = num_images_per_line #row
        self.num_lines = num_lines #column
        self.mesh_range = mesh_range # dim mesh

    #OK APPELER PAR DO_COLLECT ABSTRACTCOLLECT A TESTER !!!!! 
    @task
    def _take_crystal_snapshot(self, filename):
        """
        Descript. : 
        """
        self.graphics_manager_hwobj.save_scene_snapshot(filename)
    #OK OK !!!!!!!!!!!!!!!!!!
    def set_wavelength(self, wavelength):
        """
        Descript. : 
        """
        if self.energy_hwobj is not None:
            self.energy_obj.startMoveWavelength(wavelength)
            while energy_obj.getState() != 'STANDBY':
                time.sleep(0.5)
    #OK  OK !!!!!!!!!!!!!!!!!!
    def set_energy(self, value):
        """
        Descript. : 
        """
        if self.energy_hwobj is not None:
            self.energy_obj.startMoveEnergy(energy)
            logging.info("energy_obj.getState() %s " % energy_obj.getState())
            while energy_obj.getState() != 'STANDBY':
                time.sleep(0.5)
    #OK  OK !!!!!!!!!!!!!!!!!!
    def get_energy(self):
        if self.energy_hwobj is not None:
            return self.energy_hwobj.getCurrentEnergy()
        else : return None
    
    #OKOK !!!!!!!!!!!!!!!!!!
    @task
    def set_resolution(self, value):
        """
        Descript. :
        """
        #self.cmd_collect_resolution(value)
        logging.info("<SOLEIL MultiCollect> send resolution to %s" % new_resolution)
        logging.getLogger("user_level_log").info("Setting resolution -- moving the detector.")
        self.resolution_hwobj.move(new_resolution)
        while self.resolution_hwobj.motorIsMoving():
            logging.info("<SOLEIL MultiCollect set resolution> motor stateValue is %s" % self.bl_control.resolution.motorIsMoving())
            time.sleep(0.5)
    
    #OK
    @task    
    def set_transmission(self, value):
        #self.cmd_collect_transmission(value)
        logging.info("<SOLEIL MultiCollect> set transmission")
        self.transmission_hwobj.setTransmission(value)
    
    #not used ????!!!!!????
    def set_detector_roi_mode(self, roi_mode):
        """
        Descript. : speifique de EMBL voir si utilise a SOLEIL et n'est pas utilise
        """
        pass
        #if self.detector_hwobj is not None:
        #    self.detector_hwobj.set_collect_mode(roi_mode) 
    
    @task
    #AbstractCollect ----> OK!!!
    #remplacer par send_Detector !!!! + verify_detector_distance
    def move_detector(self, detector_distance):
        logging.info("<PX2 MultiCollect> move detector to %s" % detector_distance)
        logging.getLogger("user_level_log").info("Moving the detector -- it may take a few seconds.")
        self.bl_control.detector_distance.move(detector_distance)
        while self.bl_control.detector_distance.motorIsMoving():
            time.sleep(0.5)
        logging.getLogger("user_level_log").info("Moving the detector -- done.")
    
    #OK !!!!!!!!!!!!!!!!!! 
    @task
    def move_motors(self, motor_position_dict):
        """
        Descript. : 
        """        
        self.diffractometer_hwobj.move_motors(motor_position_dict)

    def prepare_input_files(self):
        """
        Descript. : SoleilMulticollect def prepare_input_files(self, files_directory, prefix, run_number, process_directory):
                    return "/tmp", "/tmp"
                    
                    A REDEFINIR !!!!!!!!!!!!!!!!!!!!!!! 
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
        Descript. : BLEnergy
        """
        if self.energy_hwobj is not None:
            return self.energy_hwobj.getCurrentWavelength()
            
    #OK !!!!!!!!!!!!!!!!!!
    def get_detector_distance(self):
        """
        Descript. : detector_distance_hwobj TangoDCMotor getPosition
        """
        pass
        #if self.detector_hwobj is not None:	
        #    return self.detector_hwobj.get_distance()
#==============================================================================
#         #a tester 
#==============================================================================
        if self.detectordistance_hwobj is not None:	
            return self.detectordistance_hwobj.getPosition()
    #OK !!!!!!!!!!!!!!!!!!
    def get_detector_distance_limits(self):
        """
        Descript. : detector_distance_hwobj TangoDCMotor getLimits
        """
        pass
        #if self.detector_hwobj is not None:
        #    return self.detector_hwobj.get_distance_limits()
#==============================================================================
#         #a tester 
#==============================================================================
        if self.detectordistance_hwobj is not None:
            return self.detectordistance_hwobj.getLimits()
    
    #OK !!!!!!!!!!!!!!!!!!
    def get_resolution(self):
        """
        Descript. : TangoResolutionComplex
        """
        if self.resolution_hwobj is not None:
            return self.resolution_hwobj.getPosition()
    
    #OK !!!!!!!!!!!!!!!!!!
    def get_transmission(self):
        """
        Descript. : Ps_attenuatorPX2
        """
        if self.transmission_hwobj is not None:
            return self.transmission_hwobj.getAttFactor()
    
    #OK !!!!!!!!!!!!!!!!!!
    def get_undulators_gaps(self):
        """
        Descript. : return triplet with gaps. In PX2 return [None]*3 see SOLEILMULTICOLLECT
        """
        return [None]*3
#==============================================================================
#         if self.chan_undulator_gap:
#             und_gaps = self.chan_undulator_gap.getValue()
#             if type(und_gaps) in (list, tuple):
#                 return und_gaps
#             else: 
#                 return (und_gaps)
#         else:
#             return {} 
#==============================================================================
        
    #OK !!!!!!!!!!!!!!!!!!
    def get_beam_size(self):
        """
        Descript. : en dur dans SoleilMultiCollect return (0.010, 0.005)
        """
        if self.beam_info_hwobj is not None:
            return self.beam_info_hwobj.get_beam_size()
            
    #OK !!!!!!!!!!!!!!!!!!
    def get_slit_gaps(self):
        """
        Descript. : en dur dans SoleilMultiCollect return [-999,-999]
        """
        if self.beam_info_hwobj is not None:
            return self.beam_info_hwobj.get_slits_gap()
            
            
    #OK !!!!!!!!!!!!!!!!!!
    def get_beam_shape(self):
        """
        Descript. : 
        """
        if self.beam_info_hwobj is not None:
            return self.beam_info_hwobj.get_beam_shape()
            
    #OK !!!!!!!!!!!!!!!!!!
    def get_measured_intensity(self):
        """
        Descript. : not in PX2 a redefinir en dur par exemple dans EMBL
                    donne le flux -> method
        """
        self.get_flux()

    
    #OK !!!!!!!!!!!!!!!!!!
    def get_machine_current(self):
        """
        Descript. : TangoMashCurrent > get_current = getcurrent
        """
        if self.machine_info_hwobj:
            return self.machine_info_hwobj.get_current()
        else:
            return 0
    ##OK !!!!!!!!!!!!!!!!!!
    def get_machine_message(self):
        """
        Descript. : TangoMashCurrent > get_message = getmessage
        """
        if self.machine_info_hwobj:
            return self.machine_info_hwobj.get_message()
        else:
            return ''
    
    #OK !!!!!!!!!!!!!!!!!!
    def get_machine_fill_mode(self):
        """
        Descript. : getFillMode() in machine_info_hwobj PX2
        """
#==============================================================================
#         if self.machine_info_hwobj:
#             fill_mode = str(self.machine_info_hwobj.get_message()) 
#             return fill_mode[:20]
#         else:
#             return ''
#==============================================================================
        
        if self.machine_info_hwobj:
            return self.machine_info_hwobj.getFillMode()
        else:
            return ''
            
#==============================================================================
#     def getBeamlineConfiguration(self, *args):
#         """
#         Descript. :   : ??? utiliser nulle part
#         """
#         return self.bl_config._asdict()
#==============================================================================
        
    ##OK !!!!!!!!!!!!!!!!!! 
    def get_flux(self):
        """
        Descript. : PX2
        """
        #return self.get_measured_intensity()
        try:
            return self.flux_hwobj.getCurrentFlux()
        except :
            return -1
        
    # dans la queue
    def set_run_autoprocessing(self, status):
        self.run_autoprocessing = status
        
#==============================================================================
# only for beamlinetest EMBL      
#==============================================================================
    def close_guillotine(self, wait=True):
        pass
        #self.cmd_close_guillotine()
        #if wait:
        #    with gevent.Timeout(10, Exception("Timeout waiting for close")):
        #       while self.guillotine_state != "closed":
        #             gevent.sleep(0.1) 

#==============================================================================
# plus specific  PX2 
#==============================================================================
    #OK !!!!!!!!!!!!!!!!!!
    @task
    #commenter dans PX2MulticCollect utiliser appeler dans eiger module
    def close_fast_shutter(self):
        logging.info("<SOLEIL MultiCollect> close fast shutter ")
        self.bl_control.fast_shutter.closeShutter()
        t0 = time.time()
        while self.bl_control.fast_shutter.getShutterState() != 'closed':
            time.sleep(0.1)
            if (time.time() - t0) > 4:
                logging.getLogger("HWR").error("Timeout on closing fast shutter")
                break
    #OK !!!!!!!!!!!!!!!!!!
    @task
    #commenter dans PX2MulticCollect utiliser appeler dans eiger module
    def open_fast_shutter(self):
        logging.info("<SOLEIL MultiCollect> open fast shutter ")
        self.bl_control.fast_shutter.openShutter()
        t0 = time.time()
        while self.bl_control.fast_shutter.getShutterState() == 'closed':
            time.sleep(0.1)
            if (time.time() - t0) > 4:
                logging.getLogger("HWR").error("Timeout on opening fast shutter")
                break
    #OK !!!!!!!!!!!!!!!!!!
    @task
    #Utiliser dans le Loop dans AbstractMutlicollect !!!! plus de Loop mais defini AbstractCollect !!!!!
    def close_safety_shutter(self):
        logging.info("<SOLEIL MultiCollect> VERIFY - close safety shutter" )
        if self.test_mode == 1:
            logging.info("<SOLEIL MultiCollect> simulation mode -- leaving safety shutter as it was" )
            return

        return
        self.bl_control.safety_shutter.closeShutter()
        t0 = time.time()
        while self.bl_control.safety_shutter.getShutterState() == 'opened':
          time.sleep(0.1)
          if (time.time() - t0) > 6:
                break
            
    #OK !!!!!!!!!!!!!!!!!!
    @task
    def open_safety_shutter(self):
        logging.info("<PX2 Collect> VERIFY - open safety shutter" )
        if self.test_mode == 1:
            logging.info("<SOLEIL MultiCollect> simulation mode -- leaving safety shutter as it was" )
            return

        self.bl_control.safety_shutter.openShutter()

        t0 = time.time()
        while self.bl_control.safety_shutter.getShutterState() == 'closed':
            time.sleep(0.1)
            if (time.time() - t0) > 8:
                logging.getLogger("user_level_log").error("Cannot open safety shutter. Please checg before restarting data collection")
                #bj.getState() DISABLE
                break
            
            
def test():
    import os
    hwr_directory = os.environ["XML_FILES_PATH"]

    hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
    hwr.connect()

    coll = hwr.getHardwareObject("/Qt4_px2mxcollect")
    
    print "Machine current is ", coll.get_machine_current()
    print "Synchrotron name is ", coll.bl_config.synchrotron_name

if __name__ == '__main__':
   test()
