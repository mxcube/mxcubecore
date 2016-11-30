from HardwareRepository.BaseHardwareObjects import HardwareObject
from AbstractMultiCollect import *
from gevent.event import AsyncResult
import logging
import time
import os
import httplib
import urllib
import math
from queue_model_objects_v1 import PathTemplate
#from MAXIV.BIOMAXPilatus import BIOMAXPilatus

class FixedEnergy:
    def __init__(self, wavelength, energy):
      self.wavelength = wavelength
      self.energy = energy

    def set_wavelength(self, wavelength):
      return

    def set_energy(self, energy):
      return

    def getCurrentEnergy(self):
      return self.energy

    def get_wavelength(self):
      return self.wavelength


class TunableEnergy:
    # self.bl_control is passed by ESRFMultiCollect
    @task
    def set_wavelength(self, wavelength):
        energy_obj = self.bl_control.energy
        return energy_obj.startMoveWavelength(wavelength)

    @task
    def set_energy(self, energy):
        energy_obj = self.bl_control.energy
        return energy_obj.startMoveEnergy(energy)

    def getCurrentEnergy(self):
        return self.bl_control.energy.getCurrentEnergy()

    def get_wavelength(self):
        return self.bl_control.energy.getCurrentWavelength()


class BIOMAXMultiCollect(AbstractMultiCollect, HardwareObject):

    def __init__(self, name):

        AbstractMultiCollect.__init__(self)
        HardwareObject.__init__(self, name)
        self._tunable_bl = FixedEnergy(1.125, 11.0)
        self._centring_status = None
        self.helical = False
        self.shutterless_exptime = None
        self.shutterless_range = None
        self.oscillation_task = None

    def do_oscillation():
	pass
    def last_image_saved():
	pass
    def prepare_oscillation():
	pass
    def set_detector_filenames():
	pass
    def write_image():
	pass


    def execute_command(self, command_name, *args, **kwargs): 
      wait = kwargs.get("wait", True)
      cmd_obj = self.getCommandObject(command_name)
      return cmd_obj(*args, wait=wait)
        
    def init(self):
        self.setControlObjects(diffractometer = self.getObjectByRole("diffractometer"),
                               sample_changer = self.getObjectByRole("sample_changer"),
                               lims = self.getObjectByRole("dbserver"),
                               #lims = None, # disable lims for the moment
                               safety_shutter = self.getObjectByRole("safety_shutter"),
                               machine_current = self.getObjectByRole("machine_current"),
                               #cryo_stream = self.getObjectByRole("cryo_stream"),
                               cryo_stream = None, # disable for the moment, only needed for ISPyB
                               energy = self.getObjectByRole("energy"),
                               resolution = self.getObjectByRole("resolution"),
                               detector_distance = self.getObjectByRole("detector_distance"),
                               transmission = self.getObjectByRole("transmission"),
                               undulators = self.getObjectByRole("undulators"),
                               #flux = self.getObjectByRole("flux"),
                               flux = None, # disable for the moment, only needed for ISPyB
                               detector = self.getObjectByRole("detector"),
                               beam_info = self.getObjectByRole("beam_info"))
       
       
        try:
          undulators = self["undulator"]
        except IndexError:
          undulators = []

        self.setBeamlineConfiguration(synchrotron_name = "MAXIV",
                                      directory_prefix = self.getProperty("directory_prefix"),
                                      default_exposure_time = self.bl_control.detector.getProperty("default_exposure_time"),
                                      minimum_exposure_time = self.bl_control.detector.get_minimum_exposure_time(),
                                      detector_fileext = self.bl_control.detector.getProperty("file_suffix"),
                                      detector_type = self.bl_control.detector.getProperty("type"),
                                      detector_manufacturer = self.bl_control.detector.getProperty("manufacturer"),
                                      detector_model = self.bl_control.detector.getProperty("model"),
                                      detector_px = self.bl_control.detector.get_pixel_size_x(),
                                      detector_py = self.bl_control.detector.get_pixel_size_y(),
                                      undulators = undulators,
                                      focusing_optic = self.getProperty('focusing_optic'),
                                      monochromator_type = self.getProperty('monochromator'),
                                      beam_divergence_vertical = self.bl_control.beam_info.get_beam_divergence_ver(),
                                      beam_divergence_horizontal = self.bl_control.beam_info.get_beam_divergence_hor(),
                                      polarisation = self.getProperty('polarisation'),
                                      input_files_server = self.getProperty("input_files_server"))
  
        self.archive_directory= self.getProperty("archive_directory")
       
        self.detector = self.bl_control.detector
        self._tunable_bl.bl_control = self.bl_control


        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True, ))

    @task
    def take_crystal_snapshots(self, number_of_snapshots):
        #self.bl_control.diffractometer.takeSnapshots(number_of_snapshots, wait=True)
        #take only one image 
        phi = self.bl_control.diffractometer.motor_hwobj_dict['phi'].getPosition()
        img = self.bl_control.diffractometer.camera.get_snapshot_img_str()
        self.bl_control.diffractometer.centring_status["images"] = [[phi,img]]


    #TODO: remove this hook!!!
    @task
    def data_collection_hook(self, data_collect_parameters):
        return
 
    def do_prepare_oscillation(self):
        # the exptime is the total exptime
        diffr = self.bl_control.diffractometer
        #move to DataCollection phase
        if diffr.get_current_phase() != "DataCollection":
            logging.getLogger("user_level_log").info("Moving Diffractometer to Data Collection")
            diffr.set_phase("DataCollection", wait=True, timeout=200)
        #switch on the front light
        diffr.front_light_switch.actuatorIn(wait=True)
        #take the back light out
        diffr.back_light_switch.actuatorOut(wait=True)

    def set_data_collection(self):
        diffr = self.bl_control.diffractometer
        #move to DataCollection phase
        if diffr.get_current_phase() != "DataCollection":
            logging.getLogger("user_level_log").info("Moving Diffractometer to Data Collection")
            diffr.set_phase("DataCollection", wait=True, timeout=200)
        #switch on the front light
        diffr.front_light_switch.actuatorIn(wait=True)
        #take the back light out
        diffr.back_light_switch.actuatorOut(wait=True)


    @task
    def oscil(self, start, end, exptime, npass):
        diffr = self.bl_control.diffractometer
        if self.helical:
            diffr.osc_scan_4d(start, end, exptime, self.helical_pos, wait=True)
        else:
            diffr.osc_scan(start, end, exptime, wait=True)


    @task
    def data_collection_cleanup(self):
        self.close_fast_shutter()


    @task
    def close_fast_shutter(self):
        return #todo


    @task
    def open_fast_shutter(self):
        return #todo

        
    @task
    def move_motors(self, motor_position_dict):
        diffr = self.bl_control.diffractometer
        # to do, set out the detector cover
        """        
        try:
            motors_to_move_dict.pop('kappa')
            motors_to_move_dict.pop('kappa_phi')
        except:
            pass
        """
        diffr.move_sync_motors(motor_position_dict, wait=True)

    @task
    def open_safety_shutter(self):
        self.bl_control.safety_shutter.openShutter()
        while self.bl_control.safety_shutter.getShutterState() == 'closed':
          time.sleep(0.1)


    def safety_shutter_opened(self):
        return self.bl_control.safety_shutter.getShutterState() == "opened"


    @task
    def close_safety_shutter(self):
        self.bl_control.safety_shutter.closeShutter()
        while self.bl_control.safety_shutter.getShutterState() == 'opened':
          time.sleep(0.1)


    def prepare_acquisition(self, start, osc_range, exptime, name_pattern, npass, number_of_images, images_per_file=100, roi="16M", ntrigger=1):

        config = self.detector.col_config

        if roi == "4M":
            config['RoiMode'] = "4M"
        else:
            config['RoiMode'] = "disabled" #disabled means 16M

        config['PhotonEnergy'] = self._tunable_bl.getCurrentEnergy()*1000
        config['OmegaStart'] = start
        config['OmegaIncrement'] = osc_range
        beam_x, beam_y = self.get_beam_centre_pixel() # returns pixel
        config['BeamCenterX'] = beam_x  # unit, should be pixel for master file
        config['BeamCenterY'] = beam_y  
        config['DetectorDistance'] = self.get_detector_distance()/1000.0

        config['CountTime'] = exptime

        config['NbImages'] = number_of_images
        config['NbTriggers'] = ntrigger # to check for different tasks
        config['ImagesPerFile'] = images_per_file
        config['FilenamePattern'] = name_pattern
        return self.detector.prepare_acquisition(config)

  
    def start_acquisition(self, exptime, npass, first_frame):
        try:
            self.collect_obj.getObjectByRole("detector_cover").set_out()
        except:
            logging.getLogger("HWR").exception("Could not open the detector cover")
            pass
        
        return self.detector.start_acquisition()
    
    def stop_acquisition(self):
        #return self._detector.stop_acquisition()
        self.detector.stop_acquisition()
        
      
    def reset_detector(self):
        #return self.detector.reset_detector()
        self.oscillation_task.kill()
        self.detector.cancel_acquisition() # soft abort data collection
        

    def get_wavelength(self):
        return self._tunable_bl.get_wavelength()
      
       
    def get_resolution(self):
        return self.bl_control.resolution.getPosition()


    def get_beam_size(self):
      return self.bl_control.beam_info.get_beam_size()


    def get_beam_shape(self):
      return self.bl_control.beam_info.get_beam_shape()

    def getCurrentEnergy(self):
      return self._tunable_bl.getCurrentEnergy()


    def isConnected(self):
        return True

      
    def isReady(self):
        return True
 
    
    def sampleChangerHO(self):
        return self.bl_control.sample_changer


    def diffractometer(self):
        return self.bl_control.diffractometer


    def dbServerHO(self):
        return self.bl_control.lims


    def directoryPrefix(self):
        return self.bl_config.directory_prefix


    def getOscillation(self, oscillation_id):
      return self.oscillations_history[oscillation_id - 1]
       

    def sampleAcceptCentring(self, accepted, centring_status):
      self.sample_centring_done(accepted, centring_status)


    def setCentringStatus(self, centring_status):
      self._centring_status = centring_status


    def get_archive_directory(self, directory): 
        tmp_directory = directory
        tmp_directory.replace("visitor", "pyarch")
        return tmp_directory

    @task
    def generate_image_jpeg(self, filename, jpeg_path, jpeg_thumbnail_path):
        pass

    def get_cryo_temperature(self):
        if self.bl_control.cryo_stream is not None: 
            return self.bl_control.cryo_stream.getTemperature()
        else:
            return "NA"

    def get_machine_current(self):
        if self.bl_control.machine_current is not None:
            return self.bl_control.machine_current.getCurrent()
        else:
            return 0

    def get_machine_message(self):
        if  self.bl_control.machine_current is not None:
            return self.bl_control.machine_current.getMessage()
        else:
            return ''

    def get_machine_fill_mode(self):
        if self.bl_control.machine_current is not None:
            return self.bl_control.machine_current.getFillMode()
        else:
            ''

    def get_measured_intensity(self):
        return

    def get_flux(self):
        if self.bl_control.flux is not None:
            return self.bl_control.flux.getCurrentFlux()
        else:
            return None

    def get_resolution_at_corner(self):
        return 0.0

    def get_slit_gaps(self):
        return None, None

    def get_transmission(self):
        if self.bl_control.transmission is not None:
            return self.bl_control.transmission.getAttFactor()

    def get_undulators_gaps(self):
        return []

    @task
    def move_detector(self, detector_distance):
        return

    def prepare_input_files(self, files_directory, prefix, run_number, process_directory):
        i = 1
        logging.info("Creating XDS (MAXIV-BioMAX) processing input file directories")

        self.xds_template  = "/mxn/home/jienan/bin/dp_file_templates/xdstemplate_biomax.inp"

        try:
           self.xds_template_buf    = open(self.xds_template).read()
           self.write_files = True
        except:
           print "Cannot find template for xds input files "
           self.write_files = False

        while True:
          xds_input_file_dirname = "xds_%s_run%s_%d" % (prefix, run_number, i)
          xds_directory = os.path.join(process_directory, xds_input_file_dirname)

          if not os.path.exists(xds_directory):
            break

          i+=1

        self.raw_data_input_file_dir = os.path.join(files_directory, "process", xds_input_file_dirname)

        for dir in (self.raw_data_input_file_dir, xds_directory):
          self.create_directories(dir)
          logging.info("Creating XDS processing input file directory: %s", dir)
          os.chmod(dir, 0777)
        # create links for diff images in the process directory
        try:
          try:
              os.symlink(files_directory, os.path.join(process_directory, "img"))
          except os.error, e:
              if e.errno != errno.EEXIST:
                  raise
        except:
            logging.exception("Could not create processing file directory")
        return xds_directory

    @task
    def prepare_intensity_monitors(self):
        return

    @task
    def set_transmission(self, transmission_percent):
        return

    def set_wavelength(self, wavelength):
        return

    def set_energy(self, energy):
        return

    @task
    def set_resolution(self, new_resolution):
        return

    def store_image_in_lims(self, frame, first_frame, last_frame):
        return True

    def set_helical(self, helical_on):
        self.helical = helical_on

    def set_helical_pos(self, helical_oscil_pos):
        self.helical_pos = helical_oscil_pos

    @task
    def write_input_files(self, data_collect_parameters):
        xds_input_file = os.path.join(self.raw_data_input_file_dir, "XDS.INP")
        xds_file = open(xds_input_file, "w")

        oscillation_parameters = data_collect_parameters["oscillation_sequence"][0]
        start_image_number = oscillation_parameters["start_image_number"]
        end_image_number = oscillation_parameters["start_image_number"] + oscillation_parameters["number_of_images"] - 1
        end_image_number_bkg = min (start_image_number + 10, end_image_number)
        end_image_number_beg = min (start_image_number + 5, end_image_number)
        start_image_number_end = max(start_image_number, end_image_number - 5)
            
        file_parameters = data_collect_parameters["fileinfo"]
        xds_file_template = "%(prefix)s_%(run_number)s_?????.%(suffix)s" % file_parameters
        try:
            valdict = {
                "user_comment":                 data_collect_parameters["comment"],
                "BIOMAX-collection_start_time": data_collect_parameters["collection_start_time"],
                "startImageNumber":             start_image_number,
                "endImageNumber":               end_image_number,
                "startImageNumber_bkg":         start_image_number,
                "endImageNumber_bkg":           end_image_number_bkg,
                "startImageNumber_beg":         start_image_number,
                "endImageNumber_beg":           end_image_number_beg,
                "startImageNumber_end":         start_image_number_end,
                "endImageNumber_end":           end_image_number,
                "axisRange":                    oscillation_parameters["range"],
                "axisStart":                    oscillation_parameters["start"],
                "exposure_time":                oscillation_parameters["exposure_time"],
                "xdswait_exposure_time":        oscillation_parameters["exposure_time"]+float(self.bl_control.detector.getProperty("deadtime")),
                "wavelength":                   data_collect_parameters["wavelength"],
                "imageDirectory":               file_parameters["directory"],
                "fileTemplate":                 xds_file_template,
                "detectorDistance":             data_collect_parameters["detectorDistance"],
                "xbeam_px":                     float(data_collect_parameters["xBeam"]/self.bl_control.detector.getProperty("px")),
                "ybeam_px":                     float(data_collect_parameters["yBeam"]/self.bl_control.detector.getProperty("py")),
                "detectorPixelSizeHorizontal":  self.bl_control.detector.getProperty("px"),
                "detectorPixelSizeVertical":    self.bl_control.detector.getProperty("py"), 
                "resolution_upper":             data_collect_parameters["resolutionAtCorner"]
           }
        except:
           logging.getLogger("user_level_log").warning("Could not write xds input file correctly")
           return
        
        try:
           xds_buf = self.xds_template_buf % valdict
        except:
           logging.getLogger("user_level_log").warning("Could not write xds input file correctly")
           return

        xds_file.write(xds_buf)
        xds_file.close()

        os.chmod(xds_input_file, 0666)
        os.system("cp %s %s" % (xds_input_file, self.xds_directory))
        return


    def do_collect(self, owner, data_collect_parameters):
	try:
            if self.__safety_shutter_close_task is not None:
                self.__safety_shutter_close_task.kill()
	except:
	    pass

        logging.getLogger("user_level_log").info("Closing fast shutter")
        self.close_fast_shutter()

        # reset collection id on each data collect
        self.collection_id = None

        # Preparing directory path for images and processing files
        # creating image file template and jpegs files templates
        file_parameters = data_collect_parameters["fileinfo"]

        file_parameters["suffix"] = self.bl_config.detector_fileext
        image_file_template = "%(prefix)s_%(run_number)s" % file_parameters
        image_filename_pattern = os.path.join(file_parameters["directory"], image_file_template)
        file_parameters["template"] = image_file_template

        archive_directory = self.get_archive_directory(file_parameters["directory"])
        data_collect_parameters["archive_dir"] = archive_directory

        if archive_directory:
          jpeg_filename="_%s.jpeg" % image_file_template
          thumb_filename="_%s.thumb.jpeg" % image_file_template
          jpeg_file_template = os.path.join(archive_directory, jpeg_filename)
          jpeg_thumbnail_file_template = os.path.join(archive_directory, thumb_filename)
        else:
          jpeg_file_template = None
          jpeg_thumbnail_file_template = None
         
        # database filling
        if self.bl_control.lims:
            data_collect_parameters["collection_start_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            if self.bl_control.machine_current is not None:
                logging.getLogger("user_level_log").info("Getting synchrotron filling mode")
                data_collect_parameters["synchrotronMode"] = self.get_machine_fill_mode()
            data_collect_parameters["status"] = "failed"

            logging.getLogger("user_level_log").info("Storing data collection in LIMS")
            (self.collection_id, detector_id) = \
                                 self.bl_control.lims.store_data_collection(data_collect_parameters, self.bl_config)
              
            data_collect_parameters['collection_id'] = self.collection_id

            if detector_id:
                data_collect_parameters['detector_id'] = detector_id
        # Creating the directory for images and processing information
        logging.getLogger("user_level_log").info("Creating directory for images and processing")
        self.create_directories(file_parameters['directory'],  file_parameters['process_directory'])
        """
        to remove later, will not be needed with the correct uid and gid
        """
        os.chmod(file_parameters['directory'], 0777)
        os.chmod(file_parameters['process_directory'], 0777)
        
        self.xds_directory = self.prepare_input_files(file_parameters["directory"], file_parameters["prefix"], file_parameters["run_number"], file_parameters['process_directory'])
        data_collect_parameters['xds_dir'] = self.xds_directory
        logging.getLogger("user_level_log").info("Getting sample info from parameters")
        sample_id, sample_location, sample_code = self.get_sample_info_from_parameters(data_collect_parameters)
        data_collect_parameters['blSampleId'] = sample_id

        if self.bl_control.sample_changer is not None:
            try:
                data_collect_parameters["actualSampleBarcode"] = \
                    self.bl_control.sample_changer.getLoadedSample().getID()
                data_collect_parameters["actualContainerBarcode"] = \
                    self.bl_control.sample_changer.getLoadedSample().getContainer().getID()

                logging.getLogger("user_level_log").info("Getting loaded sample coords")
                basket, vial = self.bl_control.sample_changer.getLoadedSample().getCoords()

                data_collect_parameters["actualSampleSlotInContainer"] = vial
                data_collect_parameters["actualContainerSlotInSC"] = basket
            except:
                data_collect_parameters["actualSampleBarcode"] = None
                data_collect_parameters["actualContainerBarcode"] = None
        else:
            data_collect_parameters["actualSampleBarcode"] = None
            data_collect_parameters["actualContainerBarcode"] = None

        centring_info = {}
        try:
            logging.getLogger("user_level_log").info("Getting centring status")
            centring_status = self.diffractometer().getCentringStatus()
        except:
            pass
        else:
            centring_info = dict(centring_status)

        #Save sample centring positions
        positions_str = ""
        motors = centring_info.get("motors", {}) #.update(centring_info.get("extraMotors", {}))
        motors_to_move_before_collect = data_collect_parameters.setdefault("motors", {})

        for motor, pos in motors.iteritems():
              if motor in motors_to_move_before_collect:
                  continue
              motors_to_move_before_collect[motor]=pos

        current_diffractometer_position = self.diffractometer().getPositions()
        for motor in motors_to_move_before_collect.keys():
            if motors_to_move_before_collect[motor] is None:
                del motors_to_move_before_collect[motor]
                try:
                    if current_diffractometer_position[motor] is not None:
                        positions_str += "%s=%f " % (motor, current_diffractometer_position[motor])
                except:
                    pass

        # this is for the LIMS
        positions_str += " ".join([motor+("=%f" % pos) for motor, pos in motors_to_move_before_collect.iteritems()])
        data_collect_parameters['actualCenteringPosition'] = positions_str

        self.move_motors(motors_to_move_before_collect)
        # take snapshots, then assign centring status (which contains images) to centring_info variable
        logging.getLogger("user_level_log").info("Taking sample snapshosts")
        self._take_crystal_snapshots(data_collect_parameters.get("take_snapshots", False))
        centring_info = self.bl_control.diffractometer.getCentringStatus()
        # move *again* motors, since taking snapshots may change positions
        logging.getLogger("user_level_log").info("Moving motors: %r", motors_to_move_before_collect)
        self.move_motors(motors_to_move_before_collect)

        if self.bl_control.lims:
          try:
            if self.current_lims_sample:
              self.current_lims_sample['lastKnownCentringPosition'] = positions_str
              logging.getLogger("user_level_log").info("Updating sample information in LIMS")
              self.bl_control.lims.update_bl_sample(self.current_lims_sample)
          except:
            logging.getLogger("HWR").exception("Could not update sample information in LIMS")

        if centring_info.get('images'):
          # Save snapshots
          snapshot_directory = self.get_archive_directory(file_parameters["directory"])

          try:
            logging.getLogger("user_level_log").info("Creating snapshosts directory: %r", snapshot_directory)
            self.create_directories(snapshot_directory)
          except:
              logging.getLogger("HWR").exception("Error creating snapshot directory")
          else:
              snapshot_i = 1
              snapshots = []
              for img in centring_info["images"]:
                img_phi_pos = img[0]
                img_data = img[1]
                snapshot_filename = "%s_%s_%s.snapshot.jpeg" % (file_parameters["prefix"],
                                                                file_parameters["run_number"],
                                                                snapshot_i)
                full_snapshot = os.path.join(snapshot_directory,
                                             snapshot_filename)

                try:
                  f = open(full_snapshot, "w")
                  logging.getLogger("user_level_log").info("Saving snapshot %d", snapshot_i)
                  f.write(img_data)
                except:
                  logging.getLogger("HWR").exception("Could not save snapshot!")
                  try:
                    f.close()
                  except:
                    pass

                data_collect_parameters['xtalSnapshotFullPath%i' % snapshot_i] = full_snapshot

                snapshots.append(full_snapshot)
                snapshot_i+=1

          try:
            data_collect_parameters["centeringMethod"] = centring_info['method']
          except:
            data_collect_parameters["centeringMethod"] = None

        if self.bl_control.lims:
            try:
                logging.getLogger("user_level_log").info("Updating data collection in LIMS")
                self.bl_control.lims.update_data_collection(data_collect_parameters)
            except:
                logging.getLogger("HWR").exception("Could not update data collection in LIMS")

        oscillation_parameters = data_collect_parameters["oscillation_sequence"][0]
        sample_id = data_collect_parameters['blSampleId']
        subwedge_size = oscillation_parameters.get("reference_interval", 1)

        #if data_collect_parameters["shutterless"]:
        #    subwedge_size = 1 
        #else:
        #    subwedge_size = oscillation_parameters["number_of_images"]
       
        wedges_to_collect = self.prepare_wedges_to_collect(oscillation_parameters["start"],
                                                           oscillation_parameters["number_of_images"],
                                                           oscillation_parameters["range"],
                                                           subwedge_size,
                                                           oscillation_parameters["overlap"])
        nframes = sum([wedge_size for _, wedge_size in wedges_to_collect])

        #Added exposure time for ProgressBarBrick. 
        #Extra time for each collection needs to be added (in this case 0.04)
        self.emit("collectNumberOfFrames", nframes, oscillation_parameters["exposure_time"] + 0.04)

        start_image_number = oscillation_parameters["start_image_number"]    
        last_frame = start_image_number + nframes - 1
        if data_collect_parameters["skip_images"]:
            for start, wedge_size in wedges_to_collect[:]:
              filename = image_file_template % start_image_number
              file_location = file_parameters["directory"]
              file_path  = os.path.join(file_location, filename)
              if os.path.isfile(file_path):
                logging.info("Skipping existing image %s", file_path)
                del wedges_to_collect[0]
                start_image_number += wedge_size
                nframes -= wedge_size
              else:
                # images have to be consecutive
                break

        if nframes == 0:
            return

	# data collection
        self.data_collection_hook(data_collect_parameters)

        if 'transmission' in data_collect_parameters:
          logging.getLogger("user_level_log").info("Setting transmission to %f", data_collect_parameters["transmission"])
          self.set_transmission(data_collect_parameters["transmission"])

        if 'wavelength' in data_collect_parameters:
          logging.getLogger("user_level_log").info("Setting wavelength to %f", data_collect_parameters["wavelength"])
          self.set_wavelength(data_collect_parameters["wavelength"])
        elif 'energy' in data_collect_parameters:
          logging.getLogger("user_level_log").info("Setting energy to %f", data_collect_parameters["energy"])
          self.set_energy(data_collect_parameters["energy"])

        if 'resolution' in data_collect_parameters:
          resolution = data_collect_parameters["resolution"]["upper"]
          logging.getLogger("user_level_log").info("Setting resolution to %f", resolution)
          self.set_resolution(resolution)
        elif 'detdistance' in oscillation_parameters:
          logging.getLogger("user_level_log").info("Moving detector to %f", data_collect_parameters["detdistance"])
          self.move_detector(oscillation_parameters["detdistance"])

        with cleanup(self.data_collection_cleanup):
            if not self.safety_shutter_opened():
                logging.getLogger("user_level_log").info("Opening safety shutter")
                self.open_safety_shutter(timeout=10)

            logging.getLogger("user_level_log").info("Preparing intensity monitors")
            self.prepare_intensity_monitors()

            frame = start_image_number
            osc_range = oscillation_parameters["range"]
            exptime = oscillation_parameters["exposure_time"]
            npass = oscillation_parameters["number_of_passes"]

            # update LIMS
            if self.bl_control.lims:
                  try:
                    logging.getLogger("user_level_log").info("Gathering data for LIMS update")
                    data_collect_parameters["flux"] = self.get_flux()
                    data_collect_parameters["flux_end"] = data_collect_parameters["flux"]
                    data_collect_parameters["wavelength"]= self.get_wavelength()
                    data_collect_parameters["detectorDistance"] =  self.get_detector_distance()
                    data_collect_parameters["resolution"] = self.get_resolution()
                    data_collect_parameters["transmission"] = self.get_transmission()
                    beam_centre_x, beam_centre_y = self.get_beam_centre() # return length
                    data_collect_parameters["xBeam"] = beam_centre_x
                    data_collect_parameters["yBeam"] = beam_centre_y

                    und = self.get_undulators_gaps()
                    i = 1
                    for jj in self.bl_config.undulators:
                        key = jj.type
                        if und.has_key(key):
                            data_collect_parameters["undulatorGap%d" % (i)] = und[key]
                            i += 1
                    data_collect_parameters["resolutionAtCorner"] = self.get_resolution_at_corner()
                    beam_size_x, beam_size_y = self.get_beam_size()
                    data_collect_parameters["beamSizeAtSampleX"] = beam_size_x
                    data_collect_parameters["beamSizeAtSampleY"] = beam_size_y
                    data_collect_parameters["beamShape"] = self.get_beam_shape()
                    hor_gap, vert_gap = self.get_slit_gaps()
                    data_collect_parameters["slitGapHorizontal"] = hor_gap
                    data_collect_parameters["slitGapVertical"] = vert_gap

                    logging.getLogger("user_level_log").info("Updating data collection in LIMS")
                    self.bl_control.lims.update_data_collection(data_collect_parameters, wait=True)
                    logging.getLogger("user_level_log").info("Done updating data collection in LIMS")
                  except:
                    logging.getLogger("HWR").exception("Could not store data collection into LIMS")

            if self.bl_control.lims and self.bl_config.input_files_server:
                logging.getLogger("user_level_log").info("Asking for input files writing")
                self.write_input_files(data_collect_parameters, wait=False) 

            # at this point input files should have been written           
            # TODO aggree what parameters will be sent to this function
            if data_collect_parameters.get("processing", False)=="True":
                self.trigger_auto_processing("before",
                                       self.xds_directory,
                                       data_collect_parameters["EDNA_files_dir"],
                                       data_collect_parameters["anomalous"],
                                       data_collect_parameters["residues"],
                                       data_collect_parameters["do_inducedraddam"],
                                       data_collect_parameters.get("sample_reference", {}).get("spacegroup", ""),
                                       data_collect_parameters.get("sample_reference", {}).get("cell", ""))
            if self.run_without_loop:
                self.execute_collect_without_loop(data_collect_parameters)
            else: 
                # will break for wedge_size >1, if do arm in prepare_acquisition
                # with filewriter, one can't change the namepattern for different triggers. the following is not possible.

                for start, wedge_size in wedges_to_collect:
                    logging.getLogger("user_level_log").info("Preparing acquisition, start=%f, wedge size=%d", start, wedge_size)
                    filename = "%s_master.h5" % image_file_template 

                    self.prepare_acquisition(start,
                                             osc_range,
                                             exptime,
                                             image_filename_pattern,
                                             npass,
                                             wedge_size,
                                             ntrigger = 1)
                    data_collect_parameters["dark"] = 0

                    i = 0
                    j = wedge_size
                    while j > 0: 
                      frame_start = start+i*osc_range
                      i+=1

                      #filename = image_file_template % frame
                      try:
                        jpeg_full_path = jpeg_file_template % frame
                        jpeg_thumbnail_full_path = jpeg_thumbnail_file_template % frame
                      except:
                        jpeg_full_path = None
                        jpeg_thumbnail_full_path = None
                      file_location = file_parameters["directory"]
                      file_path  = os.path.join(file_location, filename)

                      osc_start = frame_start
                      self.shutterless_range = osc_range*wedge_size
                      osc_end = osc_start + self.shutterless_range
                      self.do_prepare_oscillation()

                      self.move_motors(motors_to_move_before_collect) 

                      with error_cleanup(self.reset_detector):
                          # Make sure the new energy is applied to the detector before getting the new readout time
 			  self.detector.wait_config_done()
                          self.shutterless_exptime = self.detector.get_acquisition_time()

                          self.start_acquisition(exptime, npass, j == wedge_size) 
                          self.oscillation_task = self.oscil(osc_start, osc_end, self.shutterless_exptime, 1, wait=True)
                          self.stop_acquisition()
                                     
                          # Store image in lims
                          if self.bl_control.lims:
                            if self.store_image_in_lims(frame, j == wedge_size, j == 1):
                              lims_image={'dataCollectionId': self.collection_id,
                                          'fileName': filename,
                                          'fileLocation': file_location,
                                          'imageNumber': frame,
                                          'measuredIntensity': self.get_measured_intensity(),
                                          'synchrotronCurrent': self.get_machine_current(),
                                          'machineMessage': self.get_machine_message(),
                                          'temperature': self.get_cryo_temperature()}

                              if archive_directory:
                                lims_image['jpegFileFullPath'] = jpeg_full_path
                                lims_image['jpegThumbnailFileFullPath'] = jpeg_thumbnail_full_path

                              try:
                                  self.bl_control.lims.store_image(lims_image)
                              except:
                                  logging.getLogger("HWR").exception("Could not store store image in LIMS")
                          
                              self.generate_image_jpeg(str(file_path), str(jpeg_full_path), str(jpeg_thumbnail_full_path),wait=False)
                          if data_collect_parameters.get("processing", False)=="True":
                            self.trigger_auto_processing("image",
                                                         self.xds_directory, 
                                                         data_collect_parameters["EDNA_files_dir"],
                                                         data_collect_parameters["anomalous"],
                                                         data_collect_parameters["residues"],
                                                         data_collect_parameters["do_inducedraddam"],
                                                         data_collect_parameters.get("sample_reference", {}).get("spacegroup", ""),
                                                         data_collect_parameters.get("sample_reference", {}).get("cell", ""))

                          self.emit("collectImageTaken", frame)

                          # skip the following, only do one subwedge
                          # don't check the last image, in the oscil task, put wait=True instead   
                          break 
 			   
                          if data_collect_parameters.get("shutterless"):
                              with gevent.Timeout(10, RuntimeError("Timeout waiting for detector trigger, no image taken")):
   			          while self.last_image_saved() == 0:
                                      time.sleep(exptime)
                          
                              last_image_saved = self.last_image_saved()
                              if last_image_saved < wedge_size:
                                  time.sleep(exptime*wedge_size/100.0)
                                  last_image_saved = self.last_image_saved()
                              frame = max(start_image_number+1, start_image_number+last_image_saved-1)
                              self.emit("collectImageTaken", frame)
                              j = wedge_size - last_image_saved
                          else:
                              j -= 1
                              self.emit("collectImageTaken", frame)
                              frame += 1
                              if j == 0:
                                break
                
    def get_beam_centre(self):
        #values from resolution obj is length, not pixel
        print self.bl_control.resolution
        return 0,0
        return self.bl_control.resolution.get_beam_centre() # length, not pixel
        
    def get_beam_centre_pixel(self):
        return 0,0
        x, y = self.bl_control.resolution.get_beam_centre()  # unit m
        return float (x / self.detector.get_x_pixel_size()), float (y / self.detector.get_y_pixel_size()) 

    def get_detector_distance(self):
        #return 750
        #todo, return self.bl_control.detector_distance.getPosition()
        return 150.0 # unit, mm
    
