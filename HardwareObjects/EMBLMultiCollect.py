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
        self._error_or_aborting = False
        self.collect_frame  = None
        self.ready_event = None

        self.chan_collect_status = None
        self.chan_collect_frame = None
        self.chan_collect_error = None

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
        self.cmd_collect_shutterless = None
        self.cmd_collect_start_angle = None
        self.cmd_collect_start_image = None
        self.cmd_collect_template = None
        self.cmd_collect_transmission = None
        self.cmd_collect_space_group = None
        self.cmd_collect_unit_cell = None
        self.cmd_collect_start = None
        self.cmd_collect_abort = None

        self.chan_collect_error = None
        self.chan_undulator_gap = None

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
        self.ready_event = gevent.event.Event()
        self.setControlObjects(
             diffractometer = self.getObjectByRole("diffractometer"),
             sample_changer = self.getObjectByRole("sample_changer"),
             lims = self.getObjectByRole("dbserver"),
             safety_shutter = self.getObjectByRole("safety_shutter"),
             machine_current = self.getObjectByRole("machine_current"),
             #cryo_stream = self.getObjectByRole("cryo_stream"),
             energy = self.getObjectByRole("energy"),
             resolution = self.getObjectByRole("resolution"),
             detector = self.getObjectByRole("detector"),
             transmission = self.getObjectByRole("transmission"),
             #undulators = self.getObjectByRole("undulators"),
             #flux = self.getObjectByRole("flux"),
             beam_info = self.getObjectByRole("beam_info"))
             #slitbox = self.getObjectByRole("slitbox"))

        mxlocal_hwobj = self.getObjectByRole("beamline_configuration")
        self.autoprocessing_hwobj = self.getObjectByRole("auto_processing")
        bcm_pars = mxlocal_hwobj["BCM_PARS"]
        try:
            undulators = bcm_pars["undulator"]
        except IndexError:
            undulators = []

        self.setBeamlineConfiguration(
             directory_prefix = self.getProperty("directory_prefix"),
             default_exposure_time = bcm_pars.getProperty("default_exposure_time"),
             default_number_of_passes = bcm_pars.getProperty("default_number_of_passes"),
             maximum_radiation_exposure = bcm_pars.getProperty("maximum_radiation_exposure"),
             nominal_beam_intensity = bcm_pars.getProperty("nominal_beam_intensity"),
             minimum_exposure_time = bcm_pars.getProperty("minimum_exposure_time"),
             minimum_phi_speed = bcm_pars.getProperty("minimum_phi_speed"),
             minimum_phi_oscillation = bcm_pars.getProperty("minimum_phi_oscillation"),
             maximum_phi_speed = bcm_pars.getProperty("maximum_phi_speed"),
             detector_fileext = self.bl_control.detector.getProperty("fileSuffix"),
             detector_type = self.bl_control.detector.getProperty("type"),
             #detector_mode = self.bl_control.detector.getProperty("mode"),
             detector_manufacturer = self.bl_control.detector.getProperty("manufacturer"),
             detector_model = self.bl_control.detector.getProperty("model"),
             detector_px = self.bl_control.detector.getProperty("px"),
             detector_py = self.bl_control.detector.getProperty("py"),
             detector_collect_name = self.bl_control.detector.get_collect_name(),
             detector_shutter_name = self.bl_control.detector.get_shutter_name(),
             #beam_ax = spec_pars["beam"].getProperty("ax"),
             #beam_ay = spec_pars["beam"].getProperty("ay"),
             #beam_bx = spec_pars["beam"].getProperty("bx"),
             #beam_by = spec_pars["beam"].getProperty("by"),
             undulators = undulators,
             focusing_optic = bcm_pars.getProperty('focusing_optic'),
             monochromator_type = bcm_pars.getProperty('monochromator'),
             #beam_divergence_vertical = bcm_pars.getProperty('beam_divergence_vertical'),
             #beam_divergence_horizontal = bcm_pars.getProperty('beam_divergence_horizontal'),     
             beam_divergence_vertical = self.bl_control.beam_info.get_beam_divergence_hor(),
             beam_divergence_horizontal = self.bl_control.beam_info.get_beam_divergence_ver(),
             polarisation = bcm_pars.getProperty('polarisation'),
             input_files_server = self.getProperty("input_files_server"))

        #Main channels
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
        self.cmd_collect_num_images = self.getCommandObject('collectNumImages')
        self.cmd_collect_overlap = self.getCommandObject('collectOverlap')
        self.cmd_collect_range = self.getCommandObject('collectRange')
        self.cmd_collect_raster_lines = self.getCommandObject('collectRasterLines')
        self.cmd_collect_raster_range = self.getCommandObject('collectRasterRange')
        self.cmd_collect_resolution = self.getCommandObject('collectResolution')
        self.cmd_collect_scan_type = self.getCommandObject('collectScanType')
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

    def collect_sync(self, owner, data_collect_parameters_list):
        """
        Descript. :
        """
        self.owner = owner
        in_multicollect = len(data_collect_parameters_list) > 1
        self.emit("collectReady", (False, ))
        self.emit("collectStarted", (self.owner, 1))
        total_frames = 0
        total_time_sec = 0
        #Calculate total collection time TODO: add snapshot taking time
        for data_collect_parameters in data_collect_parameters_list:
            total_frames = total_frames + data_collect_parameters['oscillation_sequence'][0]['number_of_images']
            total_time_sec = total_time_sec + total_frames + 2* \
                  (data_collect_parameters['oscillation_sequence'][0]['exposure_time'] + 0.02)
        self.emit("collectOverallFramesTime", (total_frames, int(total_time_sec)))
        for data_collect_parameters in data_collect_parameters_list:
            logging.debug("collect parameters = %r", data_collect_parameters)
            self.actual_data_collect_parameters = data_collect_parameters
            self.osc_id, sample_id, sample_code, sample_location = \
                  self.update_oscillations_history(self.actual_data_collect_parameters)
            self.emit('collectOscillationStarted', (self.owner, sample_id, \
                  sample_code, sample_location, self.actual_data_collect_parameters, self.osc_id))
            self.actual_data_collect_parameters["status"] = 'Running'
            self.do_collect(True, self.owner, self.actual_data_collect_parameters, in_multicollect = in_multicollect)

    def send_collection_cmd(self, p):
        """
        Descript. : main collection command
        """
        if self._actual_collect_status in ["ready", "unknown", "error"]:
            comment = 'Comment: %s' % str(p['comment'])
            self.cmd_collect_description(comment)
            self.cmd_collect_detector(self.bl_config.detector_collect_name)
            self.cmd_collect_directory(str(p["fileinfo"]["directory"]))
            self.cmd_collect_energy(int(p['energy']*1000.0))
            self.cmd_collect_exposure_time(p['oscillation_sequence'][0]['exposure_time'])
            self.cmd_collect_num_images(p['oscillation_sequence'][0]['number_of_images'])
            self.cmd_collect_overlap(p['oscillation_sequence'][0]['overlap'])
            if p['oscillation_sequence'][0]['overlap'] == 0:
                self.cmd_collect_shutterless(1)
            else:
                self.cmd_collect_shutterless(0)
            self.exposureWaitTime =max(p['oscillation_sequence'][0]['exposure_time'] ,0.0)

            self.cmd_collect_range(p['oscillation_sequence'][0]['range'])
            #elf.cmd_collect_raster_lines(p['oscillation_sequence'][0]['raster_lines'])
            #elf.cmd_collect_raster_range(p['oscillation_sequence'][0]['raster_range'])
            self.cmd_collect_resolution(p['resolution'])
            if p['experiment_type'] == 'Helical':
                self.cmd_collect_scan_type(p['experiment_type'])
            elif p['experiment_type'] == 'MESH':
                self.cmd_collect_scan_type('raster')
            else:
                self.cmd_collect_scan_type('OSC')
            self.cmd_collect_start_angle(p['oscillation_sequence'][0]['start'])
            self.cmd_collect_start_image(p['oscillation_sequence'][0]['start_image_number'])
            self.cmd_collect_template(str(p['fileinfo']['template']))
            self.cmd_collect_transmission(p['transmission'])
            space_group = str(p['sample_reference']['spacegroup'])
            if len(space_group) == 0:
                space_group = " "
            self.cmd_collect_space_group(space_group)
            unit_cell = list(eval(p['sample_reference']['cell']))
            self.cmd_collect_unit_cell(unit_cell)
            self._collecting = True
            
            self.cmd_collect_start(self.bl_config.detector_shutter_name)
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
                    logging.info("Collecting started")
            elif self._previous_collect_status == 'collecting':
                if self._actual_collect_status == "ready":
                    self.emit_collection_finished()

    def collect_error_update(self, error_msg):
        """
        Descrip. :
        """
        if (self._collecting and
            len(error_msg) > 0):
            logging.info(error_msg) 
            logging.getLogger("user_level_log").error(error_msg)

    def emit_collection_failed(self):
        """
        Descrip. :
        """ 
        failed_msg = 'Data collection failed!'
        self.actual_data_collect_parameters["status"] = failed_msg
        self.emit("collectOscillationFailed", (self.owner, False, failed_msg, \
                                               self.collection_id, self.osc_id))
        self.emit("collectEnded", self.owner, failed_msg)
        self.emit("collectReady", (True, ))
        self._collecting = None
        self.ready_event.set()
  
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

        if self.bl_control.lims is not None:
            try:
                self.bl_control.lims.update_data_collection(self.actual_data_collect_parameters)
            except:
                logging.getLogger("HWR").exception("Could not store data collection into ISPyB")
        last_frame = self.actual_data_collect_parameters['oscillation_sequence'][0]['number_of_images']
        if last_frame > 1:
            self.process_image(last_frame)
        if last_frame > 100 and self.actual_data_collect_parameters.get("processing", False) == "True":
            self.trigger_auto_processing("after", self.actual_data_collect_parameters, 0)

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
                              'fileLocation': "/mnt/p13ppu01" + file_location,
                              'imageNumber': frame,
                              'measuredIntensity': self.get_measured_intensity(),
                              'synchrotronCurrent': self.get_machine_current(),
                              'machineMessage': self.get_machine_message(),
                              'temperature': self.get_cryo_temperature()}
                archive_directory = self.get_archive_directory(file_location)
                self.actual_data_collect_parameters["archive_dir"] = archive_directory
                if archive_directory:
                    jpeg_filename = "%s.jpeg" % os.path.splitext(image_file_template)[0]
                    thumb_filename = "%s.thumb.jpeg" % os.path.splitext(image_file_template)[0]
                    jpeg_file_template = os.path.join(archive_directory, jpeg_filename)
                    jpeg_thumbnail_file_template = os.path.join(archive_directory, thumb_filename)
                    jpeg_full_path = jpeg_file_template % frame
                    jpeg_thumbnail_full_path = jpeg_thumbnail_file_template % frame
                    #TODO remove /mnt/p13ppu01
                    lims_image['jpegFileFullPath'] = "/mnt/p13ppu01" + jpeg_full_path
                    lims_image['jpegThumbnailFileFullPath'] = "/mnt/p13ppu01" + jpeg_thumbnail_full_path
                self.bl_control.lims.store_image(lims_image) 
            except:
                logging.debug("Unable to store image in ISPyB")  
        self.trigger_auto_processing("image", self.actual_data_collect_parameters, 1)

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

    def setHelical(self, arg):
        """
        Descript. : 
        """
        return

    def setHelicalPosition(self, arg):
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

    def setMeshScanParameters(self, mesh_step, mesh_range):
        """
        Descript. : 
        """
        if self.bl_control.diffractometer.is_vertical_gonio():
            self.cmd_collect_raster_lines(mesh_step[0])
        else:
            self.cmd_collect_raster_lines(mesh_step[1])
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
    
    @task
    def set_transmission(self, transmission_percent):
        """
        Descript. : 
        """
        return

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
        return

    @task
    def set_resolution(self, resolution):
        """
        Descript. : 
        """
        return

    @task
    def set_detector_mode(self, detector_mode):
        """
        Descript. : 
        """
        if self.bl_control.detector is not None:
            self.bl_control.detector.set_detector_mode(detector_mode) 
        
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
        return

    def frameEmitter(self, frame):
        """
        Descript. : 
        """
        return
        #self.emit("collectImageTaken", self.collectFrame)

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
            xds_input_file_dirname = "xds_%s_run%s_%d" % (prefix, run_number, i)
            xds_directory = os.path.join(process_directory, xds_input_file_dirname)
            if not os.path.exists(xds_directory):
                break
            i += 1
        mosflm_input_file_dirname = "mosflm_%s_run%s_%d" % (prefix, run_number, i)
        mosflm_directory = os.path.join(process_directory, mosflm_input_file_dirname)

        #self.raw_data_input_file_dir = os.path.join(files_directory, "process", xds_input_file_dirname)
        #self.mosflm_raw_data_input_file_dir = os.path.join(files_directory, "process", mosflm_input_file_dirname)
        
        return xds_directory, mosflm_directory

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
            return self.bl_control.transmission.transmissionValueGet()

    def get_undulators_gaps(self):
        """
        Descript. : return triplet with gaps. In our case we have one gap, 
                    others are 0        
        """
        if self.chan_undulator_gap:
            und_gaps = self.chan_undulator_gap.getValue()
            if type(und_gaps) in (list, tuple):
                return und_gaps[0], 0, 0
            else: 
                return und_gaps, 0, 0
        else:
            return 0, 0, 0 

    def get_resolution_at_corner(self):
        """
        Descript. : 
        """
        return

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
        return 0

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
            return self.bl_control.machine_current.getFillMode()
        else:
            return ''

    def get_cryo_temperature(self):
        """
        Descript. : 
        """
        return

    """def getCurrentEnergy(self):
	if self.bl_control.energy:
	    return self.bl_control.energy.getCurrentEnergy()"""

    def get_beam_centre(self):
        """
        Descript. : 
        """
        if self.bl_control.beam_info is not None:
            return self.bl_control.beam_info.get_beam_position()
		
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
 
    def sampleChangerHO(self):
        """
        Descript. : 
        """
        return self.bl_control.sample_changer


    def diffractometer(self):
        """
        Descript. : 
        """
        return self.bl_control.diffractometer

    def dbServerHO(self):
        """
        Descript. : 
        """
        return self.bl_control.lims

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
        """
        Descript. : 
        """
        return directory

    def data_collection_cleanup(self):
        """
        Descript. : 
        """
        return
