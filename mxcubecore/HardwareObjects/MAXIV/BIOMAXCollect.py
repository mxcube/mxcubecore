"""
BIOMAXCollect
"""
import os
import logging
import gevent
from HardwareRepository.TaskUtils import *
from HardwareRepository.BaseHardwareObjects import HardwareObject
from AbstractCollect import AbstractCollect

class BIOMAXCollect(AbstractCollect, HardwareObject):
    """
    Descript: Data collection class, inherited from AbstractCollect
    """
    # min images to trigger auto processing
    NIMAGES_TRIGGER_AUTO_PROC = 50

    def __init__(self, name):
        """
        Descript. :
        """
        AbstractCollect.__init__(self)
        HardwareObject.__init__(self, name)

        self._centring_status = None

        """
        self._previous_collect_status = None
        self._actual_collect_status = None

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

        """

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
        self.detector_hwobj = self.getObjectByRole("detector")
        self.autoprocessing_hwobj = self.getObjectByRole("auto_processing")
        self.beam_info_hwobj = self.getObjectByRole("beam_info")
        self.transmission_hwobj = self.getObjectByRole("transmission")
        self.dtox_hwobj = self.getObjectByRole("dtox")
        #todo
        #self.cryo_stream_hwobj = self.getObjectByRole("cryo_stream")

        undulators = []
        # todo
        try:
            for undulator in self["undulators"]:
                undulators.append(undulator)
        except:
            pass

        self.exp_type_dict = {'Mesh': 'Mesh','Helical': 'Helical'}
        self.set_beamline_configuration(\
             synchrotron_name = "MAXIV",
             directory_prefix = self.getProperty("directory_prefix"),
             default_exposure_time = self.getProperty("default_exposure_time"),
             minimum_exposure_time = self.detector_hwobj.get_minimum_exposure_time(),
             detector_fileext = self.detector_hwobj.getProperty("file_suffix"),
             detector_type = self.detector_hwobj.getProperty("type"),
             detector_manufacturer = self.detector_hwobj.getProperty("manufacturer"),
             detector_model = self.detector_hwobj.getProperty("model"),
             detector_px = self.detector_hwobj.get_pixel_size_x(),
             detector_py = self.detector_hwobj.get_pixel_size_y(),
             undulators = undulators,
             focusing_optic = self.getProperty('focusing_optic'),
             monochromator_type = self.getProperty('monochromator'),
             beam_divergence_vertical = self.beam_info_hwobj.get_beam_divergence_hor(),
             beam_divergence_horizontal = self.beam_info_hwobj.get_beam_divergence_ver(),
             polarisation = self.getProperty('polarisation'),
             input_files_server = self.getProperty("input_files_server"))

        """ to add """
        #self.chan_undulator_gap = self.getChannelObject('UndulatorGap')
        #self.chan_machine_current = self.getChannelObject("MachineCurrent")
 

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
            self.current_dc_parameters['oscillation_sequence'][0]['number_of_images'] >= \
                self.NIMAGES_TRIGGER_AUTO_PROC):
            self.trigger_auto_processing("after", self.current_dc_parameters, 0)

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
        
        #todo  
        self.trigger_auto_processing("image", self.current_dc_parameters, frame)
        image_id = self.store_image_in_lims(frame)
        return image_id 

    def trigger_auto_processing(self, process_event, params_dict, frame_number):
        """
        Descript. : 
        """
        #todo
        return

        if self.autoprocessing_hwobj is not None:
            self.autoprocessing_hwobj.execute_autoprocessing(process_event, 
                                                             self.current_dc_parameters,
                                                             frame_number)

    def get_beam_centre(self):
        """
        Descript. : 
        """
        if self.resolution_hwobj is not None:
            return self.resolution_hwobj.get_beam_centre()
        else:
            return None, None

    def get_beam_shape(self):
        """
        Descript. : 
        """
        if self.beam_info_hwobj is not None:
            return self.beam_info_hwobj.get_beam_shape()

    @task
    def _take_crystal_snapshot(self, filename):
        """
        Descript. : 
        """
        #todo,from client!?

    def set_energy(self, value):
        """
        Descript. : 
        """
        #todo
        pass

    def set_resolution(self, value):
        """
        Descript. : 
        """

        """ todo, move detector, 
            but then should be done after set energy and roi
        """
        pass
        
    @task 
    def move_motors(self, motor_position_dict):
        """
        Descript. : 
        """        
        self.diffractometer_hwobj.move_sync_motors(motor_position_dict)


    def create_file_directories(self):
        """
        Method create directories for raw files and processing files.
        Directorie for xds.input and auto_processing are created
        """
        self.create_directories(\
            self.current_dc_parameters['fileinfo']['directory'],
            self.current_dc_parameters['fileinfo']['process_directory'])

        """create processing directories and img links"""
        xds_directory,auto_directory = self.prepare_input_files()
        try:
            self.create_directories(xds_directory, auto_directory)
            #temporary, to improve
            os.system("chmod -R 777 %s %s" % (xds_directory, auto_directory))
            """todo, create link of imgs for auto_processing
            try:
                os.symlink(files_directory, os.path.join(process_directory, "img"))
            except os.error, e:
                if e.errno != errno.EEXIST:
                    raise
            """ 
            #os.symlink(files_directory, os.path.join(process_directory, "img"))
        except:
            logging.exception("Could not create processing file directory")
            return
        if xds_directory:
            self.current_dc_parameters["xds_dir"] = xds_directory
        if auto_directory:
            self.current_dc_parameters["auto_dir"] = auto_directory


    def prepare_input_files(self):
        """
        Descript. : 
        """
        i = 1
        logging.info("Creating XDS (MAXIV-BioMAX) processing input file directories")

        while True:
          xds_input_file_dirname = "xds_%s_%s_%d" % (\
              self.current_dc_parameters['fileinfo']['prefix'],
              self.current_dc_parameters['fileinfo']['run_number'],
              i)
          xds_directory = os.path.join(\
              self.current_dc_parameters['fileinfo']['directory'],
              "process", xds_input_file_dirname)
          if not os.path.exists(xds_directory):
            break
          i+=1
        auto_directory = os.path.join(\
              self.current_dc_parameters['fileinfo']['process_directory'],
              xds_input_file_dirname)
        return xds_directory, auto_directory

    def get_detector_distance(self):
        """
        Descript. : 
        """
        if self.dtox_hwobj is not None:	
            return self.dtox_hwobj.getPosition()

    def get_detector_distance_limits(self):
        """
        Descript. : 
        """
        #todo
        return 1000
       
    def get_transmission(self):
        """
        Descript. : 
        """
        #todo
        return 100

    def set_transmission(self, value):
        """
        Descript. :
        """
        #todo
        pass

    def get_undulators_gaps(self):
        """
        Descript. : 
        """
        pass
        #todo

    def get_slit_gaps(self):
        """
        Descript. : 
        """
        #todo
        pass

    def get_machine_current(self):
        """
        Descript. : 
        """
        #todo
        return 0

    def get_machine_message(self):
        """
        Descript. : 
        """
        #todo
        return ""

    def get_flux(self):
        """
        Descript. : 
        """
        #todo
        return 0
