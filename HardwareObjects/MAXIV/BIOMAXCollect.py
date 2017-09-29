"""
BIOMAXCollect
"""
"""todo list
cancellation
exception
stopCollect
abort
"""

import os
import logging
import gevent
import time
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

        self.osc_id = None
        self.owner = None
        self._collecting = False
        self._error_msg = ""
        self._error_or_aborting = False
        self.collect_frame  = None
        self.helical = False
        self.helical_pos = None
        self.ready_event = None

        self.exp_type_dict = None

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
        self.detector_cover_hwobj = self.getObjectByRole("detector_cover") #use mockup now
        self.safety_shutter_hwobj = self.getObjectByRole("safety_shutter")
        self.fast_shutter_hwobj = self.getObjectByRole("fast_shutter")

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

#---------------------------------------------------------
#refactor do_collect
    def do_collect(self, owner):
        """
        Actual collect sequence
        """
        log = logging.getLogger("user_level_log")
        log.info("Collection: Preparing to collect")
        # todo, add more exceptions and abort
        try:
                self.emit("collectReady", (False, ))
                self.emit("collectStarted", (owner, 1))

                # ----------------------------------------------------------------
                """ should all go data collection hook
		self.open_detector_cover()
		self.open_safety_shutter()
		self.open_fast_shutter()
		"""

                # ----------------------------------------------------------------

                self.current_dc_parameters["status"] = "Running"
                self.current_dc_parameters["collection_start_time"] = \
                     time.strftime("%Y-%m-%d %H:%M:%S")
                self.current_dc_parameters["synchrotronMode"] = \
                     self.get_machine_fill_mode()

                log.info("Collection: Storing data collection in LIMS")
                self.store_data_collection_in_lims()

                log.info("Collection: Creating directories for raw images and processing files")
                self.create_file_directories()

                log.info("Collection: Getting sample info from parameters")
                self.get_sample_info()

                #log.info("Collect: Storing sample info in LIMS")
                #self.store_sample_info_in_lims()

                if all(item == None for item in self.current_dc_parameters['motors'].values()):
                    # No centring point defined
                    # create point based on the current position
                    current_diffractometer_position = self.diffractometer_hwobj.getPositions()
                    for motor in self.current_dc_parameters['motors'].keys():
                        self.current_dc_parameters['motors'][motor] = \
                             current_diffractometer_position[motor]

                log.info("Collection: Moving to centred position")
                #todo, self.move_to_centered_position() should go inside take_crystal_snapshots,
                #which makes sure it move motors to the correct positions and move back
                #if there is a phase change
                self.take_crystal_snapshots()

                # prepare beamline for data acquisiion
                self.prepare_acquisition()
                self.emit("collectOscillationStarted", (owner, None, \
                    None, None, self.current_dc_parameters, None))

                self.data_collection_hook()
                self.emit_collection_finished()
        except:
                self.emit_collection_failed()
        # ----------------------------------------------------------------

        """ should all go data collection hook
        self.close_fast_shutter()
        self.close_safety_shutter()
        self.close_detector_cover()
        """

    def prepare_acquisition(self):
        """ todo
        1. check the currrent value is the same as the tobeset value
        2. check how to add detroi in the mode
        """
      
        log = logging.getLogger("user_level_log")
        if "transmission" in self.current_dc_parameters:
            log.info("Collection: Setting transmission to %.3f",
                     self.current_dc_parameters["transmission"])
            self.set_transmission(self.current_dc_parameters["transmission"])

        if "wavelength" in self.current_dc_parameters:
            log.info("Collection: Setting wavelength to %.3f", \
                     self.current_dc_parameters["wavelength"])
            self.set_wavelength(self.current_dc_parameters["wavelength"])
        elif "energy" in self.current_dc_parameters:
            log.info("Collection: Setting energy to %.3f",
                     self.current_dc_parameters["energy"])
            self.set_energy(self.current_dc_parameters["energy"])

        if "detroi" in self.current_dc_parameters:
            log.info("Collection: Setting detector to %s",
                     self.current_dc_parameters["detroi"])
            self.set_detector_roi(self.current_dc_parameters["detroi"])

        if "resolution" in self.current_dc_parameters:
            resolution = self.current_dc_parameters["resolution"]["upper"]
            log.info("Collection: Setting resolution to %.3f", resolution)
            self.set_resolution(resolution)

        elif 'detdistance' in self.current_dc_parameters:
            log.info("Collection: Moving detector to %f",
                     self.current_dc_parameters["detdistance"])
            self.move_detector(self.current_dc_parameters["detdistance"])

        log.info("Collection: Updating data collection in LIMS")
        self.update_data_collection_in_lims()
        self.prepare_detector()

        #move MD3 to DataCollection phase if it's not
        if self.diffractometer_hwobj.get_current_phase() != "DataCollection":
            log.info("Moving Diffractometer to Data Collection")
            self.diffractometer_hwobj.set_phase("DataCollection", wait=True, timeout=200)
        self.move_to_centered_position()


#-------------------------------------------------------------------------------


    def data_collection_hook(self):
        """
        Descript. : main collection command
        """

        try:
            oscillation_parameters = self.current_dc_parameters["oscillation_sequence"][0]
            osc_start = oscillation_parameters['start']
            osc_end = osc_start + oscillation_parameters["range"] * \
                oscillation_parameters['number_of_images']
            self.open_detector_cover()
            self.open_safety_shutter()
            #make sure detector configuration is finished
            self.detector_hwobj.wait_config_done()
            self.detector_hwobj.start_acquisition()
            # call after start_acquisition (detector is armed), when all the config parameters are definitely
            # implemented
            shutterless_exptime = self.detector_hwobj.get_acquisition_time()
            
            self.oscillation_task = self.oscil(osc_start, osc_end, shutterless_exptime, 1, wait=True)
            self.detector_hwobj.stop_acquisition()

            self.close_safety_shutter()
            self.close_detector_cover()
            self.emit("collectImageTaken", oscillation_parameters['number_of_images'])
        except:
            self.data_collection_cleanup()
            raise Exception("data collection hook failed")

    def oscil(self, start, end, exptime, npass, wait = True):
        if self.helical:
            self.diffractometer_hwobj.osc_scan_4d(start, end, exptime, self.helical_pos, wait=True)
        else:
            self.diffractometer_hwobj.osc_scan(start, end, exptime, wait=True)


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

    def open_detector_cover(self):
        """
        Descript. :
        """
        try:
            self.detector_cover_hwobj.set_out()
        except:
            logging.getLogger("HWR").exception("Could not open the detector cover")
            pass

    def close_detector_cover(self):
        """
        Descript. :
        """
        pass

    def open_safety_shutter(self):
        """
        Descript. :
        """
        #todo add time out? if over certain time, then stop acquisiion and
        #popup an error message
        return # disable temp
        self.safety_shutter_hwobj.openShutter()
        while self.safety_shutter_hwobj.getShutterState() == 'closed':
            time.sleep(0.1)

    def close_safety_shutter(self):
        """
        Descript. :
        """
        #todo, add timeout, same as open
        return #disable temp
        self.safety_shutter_hwobj.closeShutter()
        while self.safety_shutter_hwobj.getShutterState() == 'opened':
            time.sleep(0.1)

    def open_fast_shutter(self):
        """
        Descript. : important to make sure it's passed, as we
                    don't open the fast shutter in MXCuBE
        """
        pass

    def close_fast_shutter(self):
        """
        Descript. :
        """
        #to do, close the fast shutter as early as possible in case
        #MD3 fails to do so
        pass

    @task
    def _take_crystal_snapshot(self, filename):
        """
        Descript. :
        """
        #todo,from client!?

    def set_detector_roi(self, value):
        """
        Descript. : set the detector roi mode
        """
        self.detector_hwobj.set_roi_mode(value)

    def set_helical(self, helical_on):
        """
        Descript. : 
        """
        self.helical = helical_on

    def set_helical_pos(self, helical_oscil_pos):
        """
        Descript. :
        """
        self.helical_pos = helical_oscil_pos


    def set_resolution(self, value):
        """
        Descript. :
        """

        """ todo, move detector,
            but then should be done after set energy and roi
        """
        pass

    def set_energy(self, value):
        #todo,disabled temp
        #self.energy_hwobj.set_energy(value)

        self.detector_hwobj.set_photon_energy(value*1000)

    def set_wavelength(self, value):
        self.energy_hwobj.set_wavelength(value)
        current_energy = self.energy_hwobj.get_energy()
        self.detector_hwobj.set_photon_energy(value*1000)

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
        logging.getLogger("user_level_log").info("Creating XDS (MAXIV-BioMAX) processing input file directories")

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

    def prepare_detector(self):

        oscillation_parameters = self.current_dc_parameters["oscillation_sequence"][0]
        config = self.detector_hwobj.col_config
        """ move after setting energy
        if roi == "4M":
            config['RoiMode'] = "4M"
        else:
            config['RoiMode'] = "disabled" #disabled means 16M

        config['PhotonEnergy'] = self._tunable_bl.getCurrentEnergy()
        """
        config['OmegaStart'] = oscillation_parameters['start']
        config['OmegaIncrement'] = oscillation_parameters["range"]
        beam_centre_x, beam_centre_y = self.get_beam_centre() #self.get_beam_centre_pixel() # returns pixel
        config['BeamCenterX'] = beam_centre_x  # unit, should be pixel for master file
        config['BeamCenterY'] = beam_centre_y
        config['DetectorDistance'] = self.get_detector_distance()/1000.0

        config['CountTime'] = oscillation_parameters['exposure_time']

        config['NbImages'] = oscillation_parameters['number_of_images']
        try:
            # tocheck, perhaps can use oscillation_parameters["number_of_passes"]
            config['NbTriggers'] = oscillation_parameters['number_of_triggers'] # to check for different tasks
        except:
            config['NbTriggers'] = 1
        try:
            config['ImagesPerFile'] = oscillation_parameters['images_per_file']
        except:
            config['ImagesPerFile'] = 100

        import re
        file_parameters = self.current_dc_parameters["fileinfo"]
        file_parameters["suffix"] = self.bl_config.detector_fileext
        image_file_template = "%(prefix)s_%(run_number)s" % file_parameters
        name_pattern = os.path.join(file_parameters["directory"], image_file_template)
        file_parameters["template"] = image_file_template
 
        os.path.join(file_parameters["directory"], image_file_template) 
        config['FilenamePattern'] = re.sub("^/data","",name_pattern)  # remove "/data in the beginning"
        return self.detector_hwobj.prepare_acquisition(config)

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
        #todo
        return None

    def get_slit_gaps(self):
        """
        Descript. : 
        """
        #todo
        return None, None

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
