"""
Descript: EMBLMultiCollect hwobj
"""
import os
import logging
import gevent
from HardwareRepository.TaskUtils import *
from HardwareRepository.BaseHardwareObjects import HardwareObject
from AbstractMultiCollect import AbstractMultiCollect

class EMBLMultiCollect(AbstractMultiCollect, HardwareObject):
    """
    Descript: Main data collection class. Inherited from AbstractMulticollect
              Collection is done by setting collection parameters and 
              executing collect command  
    """
    def __init__(self, name):
        """
        Descript. :
        """
        AbstractMultiCollect.__init__(self)
        HardwareObject.__init__(self, name)
        self._centring_status = None
        self._previous_collect_status = None
        self._actual_collect_status = None
        self.actual_data_collect_parameters = None

        self.osc_id = None
        self.owner = None
        self._collecting = False
        self._error_msg = ""
        self._error_or_aborting = False
        self.collect_frame  = None
        self.ready_event = None

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

    def execute_command(self, command_name, *args, **kwargs): 
        """
        Descript. :
        Note      : 
        """
        return	
        
    def init(self):
        """
        Descript. : 
        """
        self.run_without_loop = True

        self.ready_event = gevent.event.Event()
        self.setControlObjects(diffractometer = self.getObjectByRole("diffractometer"),
                               sample_changer = self.getObjectByRole("sample_changer"),
                               lims = self.getObjectByRole("dbserver"),
                               safety_shutter = self.getObjectByRole("safety_shutter"),
                               machine_current = self.getObjectByRole("machine_current"),
                               cryo_stream = self.getObjectByRole("cryo_stream"),
                               energy = self.getObjectByRole("energy"),
                               resolution = self.getObjectByRole("resolution"),
                               detector_distance = self.getObjectByRole("detector_distance"),
                               transmission = self.getObjectByRole("transmission"),
                               undulators = self.getObjectByRole("undulators"),
                               flux = self.getObjectByRole("flux"),
                               detector = self.getObjectByRole("detector"),
                               beam_info = self.getObjectByRole("beam_info"))

        self.autoprocessing_hwobj = self.getObjectByRole("auto_processing")

        undulators = []
        try:
           for undulator in self["undulators"]:
               undulators.append(undulator)
        except:
           pass  
        self.exp_type_dict = {'Mesh': 'raster',
                              'Helical': 'Helical'}
        self.setBeamlineConfiguration(synchrotron_name = self.bl_control.lims.session_hwobj.synchrotron_name,
                                      directory_prefix = self.getProperty("directory_prefix"),
                                      default_exposure_time = self.bl_control.detector.getProperty("default_exposure_time"),
                                      minimum_exposure_time = self.bl_control.detector.getProperty("minimum_exposure_time"),
                                      detector_fileext = self.bl_control.detector.getProperty("fileSuffix"),
                                      detector_type = self.bl_control.detector.getProperty("type"),
                                      detector_manufacturer = self.bl_control.detector.getProperty("manufacturer"),
                                      detector_model = self.bl_control.detector.getProperty("model"),
                                      detector_px = self.bl_control.detector.getProperty("px"),
                                      detector_py = self.bl_control.detector.getProperty("py"),
                                      undulators = undulators,
                                      focusing_optic = self.getProperty('focusing_optic'),
                                      monochromator_type = self.getProperty('monochromator'),
                                      beam_divergence_vertical = self.bl_control.beam_info.get_beam_divergence_hor(),
                                      beam_divergence_horizontal = self.bl_control.beam_info.get_beam_divergence_ver(),
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

    def execute_collect_without_loop(self, p):
        """
        Descript. : main collection command
        """
        if self._actual_collect_status in ["ready", "unknown", "error"]:
            comment = 'Comment: %s' % str(p.get('comments', ""))
            self._error_msg = ""
            self._collecting = True
            self.cmd_collect_description(comment)
            self.cmd_collect_detector(self.bl_control.detector.get_collect_name())
            self.cmd_collect_directory(str(p["fileinfo"]["directory"]))
            self.cmd_collect_exposure_time(p['oscillation_sequence'][0]['exposure_time'])
            self.cmd_collect_in_queue(p['in_queue'])
            self.cmd_collect_overlap(p['oscillation_sequence'][0]['overlap'])
            shutter_name = self.bl_control.detector.get_shutter_name()
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
                self.process_image(1)
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
        self.actual_data_collect_parameters["status"] = failed_msg
        self.actual_data_collect_parameters["comments"] = "%s\n%s" %(failed_msg, self._error_msg) 
        self.emit("collectOscillationFailed", (self.owner, False, failed_msg, \
                                               self.collection_id, self.osc_id))
        self.emit("collectEnded", self.owner, failed_msg)
        self.emit("collectReady", (True, ))
        self._collecting = None
        self.ready_event.set()

        self.store_in_lims() 

    def emit_collection_finished(self):  
        """
        Descript. :
        """
        success_msg = "Data collection successful"
        self.actual_data_collect_parameters["status"] = success_msg
        self.emit("collectOscillationFinished", (self.owner, True, success_msg,
              self.collection_id, self.osc_id, self.actual_data_collect_parameters))
        self.emit("collectEnded", self.owner, success_msg)
        self.emit("collectReady", (True, ))
        self._collecting = None
        self.ready_event.set()

        self.store_in_lims()

        last_frame = self.actual_data_collect_parameters['oscillation_sequence'][0]['number_of_images']
        if last_frame > 1:
            self.process_image(last_frame)
        if (self.actual_data_collect_parameters['experiment_type'] in ('OSC', 'Helical') and
            self.actual_data_collect_parameters['oscillation_sequence'][0]['overlap'] == 0 and
            self.actual_data_collect_parameters['oscillation_sequence'][0]['number_of_images'] > 19):
            self.trigger_auto_processing("after", self.actual_data_collect_parameters, 0)

    def store_in_lims(self):
        """
        Descript:
        """
        if self.bl_control.lims is not None:
            try:
               self.actual_data_collect_parameters["wavelength"]= self.get_wavelength()
               self.actual_data_collect_parameters["resolution"] = self.get_resolution()
               self.actual_data_collect_parameters["transmission"] = self.get_transmission()  
               self.bl_control.lims.update_data_collection(self.actual_data_collect_parameters)
            except:
               logging.getLogger("HWR").exception("Could not store data collection into ISPyB")        

    def update_lims_with_workflow(self, workflow_id, grid_snapshot_filename):
        if self.bl_control.lims is not None:
            try:
               self.actual_data_collect_parameters["workflow_id"] = workflow_id
               self.actual_data_collect_parameters["xtalSnapshotFullPath3"] = \
                    grid_snapshot_filename
               self.bl_control.lims.update_data_collection(self.actual_data_collect_parameters)
            except:
               logging.getLogger("HWR").exception("Could not store data collection into ISPyB")

    def collect_frame_update(self, frame):
        """
        Descript. : 
        """
        self.collect_frame = frame
        self.emit("collectImageTaken", frame) 

    def process_image(self, frame):
        """
        Descript. :
        """
        if self.bl_control.lims:
            try:
                file_location = self.actual_data_collect_parameters["fileinfo"]["directory"]
                image_file_template = self.actual_data_collect_parameters['fileinfo']['template'] 
                filename = image_file_template % frame 
                lims_image = {'dataCollectionId': self.collection_id,
                              'fileName': filename,
                              'fileLocation': file_location,
                              'imageNumber': frame,
                              'measuredIntensity': self.get_measured_intensity(),
                              'synchrotronCurrent': self.get_machine_current(),
                              'machineMessage': self.get_machine_message(),
                              'temperature': self.get_cryo_temperature()}
                archive_directory = self.actual_data_collect_parameters['fileinfo']['archive_directory']
                if archive_directory:
                    jpeg_filename = "%s.jpeg" % os.path.splitext(image_file_template)[0]
                    thumb_filename = "%s.thumb.jpeg" % os.path.splitext(image_file_template)[0]
                    jpeg_file_template = os.path.join(archive_directory, jpeg_filename)
                    jpeg_thumbnail_file_template = os.path.join(archive_directory, thumb_filename)
                    jpeg_full_path = jpeg_file_template % frame
                    jpeg_thumbnail_full_path = jpeg_thumbnail_file_template % frame
                    lims_image['jpegFileFullPath'] = jpeg_full_path
                    lims_image['jpegThumbnailFileFullPath'] = jpeg_thumbnail_full_path
                self.bl_control.lims.store_image(lims_image) 
            except:
                logging.debug("Unable to store image in ISPyB")  
        self.trigger_auto_processing("image", self.actual_data_collect_parameters, frame)

    @task
    def generate_image_jpeg(self, filename, jpeg_path, jpeg_thumbnail_path):
        pass

    def last_image_saved(self):
        pass

    def trigger_auto_processing(self, process_event, params_dict, frame_number):
        """
        Descript. : 
        """
        if self.autoprocessing_hwobj is not None:
            self.autoprocessing_hwobj.execute_autoprocessing(process_event, 
                                                             params_dict,  
                                                             frame_number)
    def stopCollect(self, owner):
        """
        Descript. :
        """
        if self._actual_collect_status == 'collecting':
            self.cmd_collect_abort()
            self.ready_event.set() 

    def set_helical(self, arg):
        """
        Descript. : 
        """
        return

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
        self.cmd_collect_raster_range(mesh_range)

    def log_message_from_spec(self, msg):
        """
        Descript. : 
        """
        return

    @task
    def take_crystal_snapshots(self, image_count):
        """
        Descript. : 
        """
        self.bl_control.diffractometer.take_snapshots(image_count, wait=True)
    
    def set_transmission(self, transmission_percent):
        """
        Descript. : 
        """
        self.cmd_collect_transmission(transmission_percent)

    def data_collection_hook(self, data_collect_parameters):
        """
        Descript. : 
        """
        return     

    def set_wavelength(self, wavelength):
        """
        Descript. : 
        """
        return

    def set_energy(self, energy):
        """
        Descript. : 
        """
        self.cmd_collect_energy(energy * 1000.0)

    def set_resolution(self, resolution):
        """
        Descript. : 
        """
        self.cmd_collect_resolution(resolution)

    @task
    def set_detector_collect_mode(self, collect_mode):
        """
        Descript. : 
        """
        if self.bl_control.detector is not None:
            self.bl_control.detector.set_collect_mode(collect_mode) 
        
    @task
    def move_detector(self, detector_distance):
        """
        Descript. : 
        """    
        return

    @task
    def close_fast_shutter(self):
        """
        Descript. : 
        """
        return

    @task
    def open_fast_shutter(self):
        """
        Descript. : 
        """
        return
        
    @task 
    def move_motors(self, motor_position_dict):
        """
        Descript. : 
        """        
        self.bl_control.diffractometer.move_motors(motor_position_dict)

    def frameEmitter(self, frame):
        """
        Descript. : 
        """
        return

    @task
    def open_safety_shutter(self):
        """
        Descript. : 
        """
        return

    @task
    def close_safety_shutter(self):
        """
        Descript. : 
        """
        return

    @task
    def prepare_intensity_monitors(self):
        """
        Descript. : 
        """
        return

    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""):
        """
        Descript. : 
        """
        return 

    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
        """
        Descript. : 
        """
        return 

    def prepare_oscillation(self, start, osc_range, exptime, npass):
        """
        Descript. : 
        """
        return start, start+osc_range

    
    def do_oscillation(self, start, end, exptime, npass):
        """
        Descript. : 
        """    
        return
    
    def start_acquisition(self, exptime, npass, first_frame):
        """
        Descript. : 
        """
        return
   
    def write_image(self, last_frame):
        """
        Descript. : 
        """
        return 

    def stop_acquisition(self):
        """
        Descript. : 
        """
        return
              
    def reset_detector(self):
        """
        Descript. : 
        """
        return       

    def prepare_input_files(self, files_directory, prefix, run_number, process_directory):
        """
        Descript. : 
        """
        i = 1
        while True:
            xds_input_file_dirname = "xds_%s_%s_%d" % (prefix, run_number, i)
            xds_directory = os.path.join(process_directory, xds_input_file_dirname)
            if not os.path.exists(xds_directory):
                break
            i += 1
        mosflm_input_file_dirname = "mosflm_%s_run%s_%d" % (prefix, run_number, i)
        mosflm_directory = os.path.join(process_directory, mosflm_input_file_dirname)

        #self.raw_data_input_file_dir = os.path.join(files_directory, "process", xds_input_file_dirname)
        #self.mosflm_raw_data_input_file_dir = os.path.join(files_directory, "process", mosflm_input_file_dirname)
        
        return xds_directory, mosflm_directory, ""

    @task
    def write_input_files(self, collection_id):
        """
        Descript. : 
        """
        return

    def get_wavelength(self):
        """
        Descript. : 
        """
        if self.bl_control.energy is not None:
            return self.bl_control.energy.getCurrentWavelength()

    def get_detector_distance(self):
        """
        Descript. : 
        """
        if self.bl_control.detector is not None:	
            return self.bl_control.detector.get_distance()

    def get_detector_distance_limits(self):
        """
        Descript. : 
        """
        if self.bl_control.detector is not None:
            return self.bl_control.detector.get_distance_limits()
       
    def get_resolution(self):
        """
        Descript. : 
        """
        if self.bl_control.resolution is not None:
            return self.bl_control.resolution.getPosition()

    def get_transmission(self):
        """
        Descript. : 
        """
        if self.bl_control.transmission is not None:
            return self.bl_control.transmission.getAttFactor()

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

    def get_resolution_at_corner(self):
        """
        Descript. : 
        """
        return
        #if self.bl_control.resolution is not None:
        #    return self.bl_control.resolution.getPosition()

    def get_beam_size(self):
        """
        Descript. : 
        """
        if self.bl_control.beam_info is not None:
            return self.bl_control.beam_info.get_beam_size()

    def get_slit_gaps(self):
        """
        Descript. : 
        """
        if self.bl_control.beam_info is not None:
            return self.bl_control.beam_info.get_slits_gap()

    def get_beam_shape(self):
        """
        Descript. : 
        """
        if self.bl_control.beam_info is not None:
            return self.bl_control.beam_info.get_beam_shape()
    
    def get_measured_intensity(self):
        """
        Descript. : 
        """
        #return 0
        return 3.000000e+12

    def get_machine_current(self):
        """
        Descript. : 
        """
        if self.bl_control.machine_current:
            return self.bl_control.machine_current.getCurrent()
        else:
            return 0

    def get_machine_message(self):
        """
        Descript. : 
        """
        if self.bl_control.machine_current:
            return self.bl_control.machine_current.getMessage()
        else:
            return ''

    def get_machine_fill_mode(self):
        """
        Descript. : 
        """
        if self.bl_control.machine_current:
            fill_mode = str(self.bl_control.machine_current.getFillMode()) 
            return fill_mode[:20]
        else:
            return ''

    def get_cryo_temperature(self):
        """
        Descript. : 
        """
        return

    def get_beam_centre(self):
        """
        Descript. : 
        """
        if self.bl_control.detector is not None:
            return self.bl_control.detector.get_beam_centre()
		
    def getBeamlineConfiguration(self, *args):
        """
        Descript. : 
        """
        return self.bl_config._asdict()

    def isConnected(self):
        """
        Descript. : 
        """
        return True
      
    def isReady(self):
        """
        Descript. : 
        """
        return True
 
    def diffractometer(self):
        """
        Descript. : 
        """
        return self.bl_control.diffractometer

    def sanityCheck(self, collect_params):
        """
        Descript. : 
        """
        return
    
    def setBrick(self, brick):
        """
        Descript. : 
        """
        return

    def directoryPrefix(self):
        """
        Descript. : 
        """
        return self.bl_config.directory_prefix

    def store_image_in_lims(self, frame, first_frame, last_frame):
        """
        Descript. : 
        """
        if first_frame or last_frame:
            return True

    def get_flux(self):
        """
        Descript. : 
        """
        return

    def getOscillation(self, oscillation_id):
        """
        Descript. : 
        """
        return self.oscillations_history[oscillation_id - 1]
       
    def sampleAcceptCentring(self, accepted, centring_status):
        """
        Descript. : 
        """
        self.sample_centring_done(accepted, centring_status)

    def setCentringStatus(self, centring_status):
        """
        Descript. : 
        """
        self._centring_status = centring_status

    def getOscillations(self, session_id):
        """
        Descript. : 
        """
        return []

    def get_archive_directory(self, directory):
        return

    def data_collection_cleanup(self):
        """
        Descript. : 
        """
        return
