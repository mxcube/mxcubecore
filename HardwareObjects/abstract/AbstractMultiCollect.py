import os
import sys
import types
import logging
import time
import errno
import abc
import collections
import gevent
import autoprocessing
import gevent
from HardwareRepository.TaskUtils import *

BeamlineControl = collections.namedtuple('BeamlineControl',
                                         ['diffractometer',
                                          'sample_changer',
                                          'lims',
                                          'safety_shutter',
                                          'machine_current',
                                          'cryo_stream',
                                          'energy',
                                          'resolution',
                                          'detector_distance',
                                          'transmission',
                                          'undulators',
                                          'flux',
                                          'detector',
                                          'beam_info'])

BeamlineConfig = collections.namedtuple('BeamlineConfig',
                                        ['synchrotron_name',
                                         'directory_prefix',
                                         'default_exposure_time',
                                         'minimum_exposure_time',
                                         'detector_fileext',
                                         'detector_type',
                                         'detector_manufacturer',
                                         'detector_model',
                                         'detector_px',
                                         'detector_py',
                                         'undulators',
                                         'focusing_optic', 
                                         'monochromator_type', 
                                         'beam_divergence_vertical',
                                         'beam_divergence_horizontal',
                                         'polarisation',
                                         'input_files_server'])


class AbstractMultiCollect(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.bl_control = BeamlineControl(*[None]*14)
        self.bl_config = BeamlineConfig(*[None]*17)
        self.data_collect_task = None
        self.oscillations_history = []
        self.current_lims_sample = None
        self.__safety_shutter_close_task = None
        self.run_without_loop = None
        self.run_autoprocessing = None
        #wait for the 1st image from detector for 30 seconds by default
        self.first_image_timeout = 30

        self.mesh = None
        self.mesh_num_lines = None
        self.mesh_total_nb_frames = None
        self.mesh_range = None
        self.mesh_center = None

    def setControlObjects(self, **control_objects):
      self.bl_control = BeamlineControl(**control_objects)
  

    def setBeamlineConfiguration(self, **configuration_parameters):
      self.bl_config = BeamlineConfig(**configuration_parameters)


    @abc.abstractmethod
    @task
    def data_collection_hook(self, data_collect_parameters):
      pass

   
    @task
    def data_collection_end_hook(self, data_collect_parameters):
      pass

    @task
    def set_detector_mode(self, detector_mode):
        """
        Descript. :
        """
        if self.bl_control.detector is not None:
            self.bl_control.detector.set_detector_mode(detector_mode)

    @abc.abstractmethod
    @task
    def set_transmission(self, transmission_percent):
        pass


    @abc.abstractmethod
    @task
    def set_wavelength(self, wavelength):
        pass


    @abc.abstractmethod
    @task
    def set_resolution(self, new_resolution):
      pass


    @abc.abstractmethod
    @task
    def set_energy(self, energy):
      pass   


    @abc.abstractmethod
    @task
    def close_fast_shutter(self):
        pass


    @abc.abstractmethod
    @task
    def move_detector(self, distance):
        pass


    @abc.abstractmethod
    @task
    def move_motors(self, motor_position_dict):
        return


    @abc.abstractmethod
    @task
    def open_safety_shutter(self):
        pass

   
    def safety_shutter_opened(self):
        return False


    @abc.abstractmethod
    @task
    def close_safety_shutter(self):
        pass


    @abc.abstractmethod
    @task
    def prepare_intensity_monitors(self):
        pass


    @abc.abstractmethod
    @task
    def prepare_oscillation(self, start, osc_range, exptime, npass):
        """Should return osc_start and osc_end positions -
        gonio should be ready for data collection after this ;
        Remember to check for still image if range is too small !
        """
        pass


    @abc.abstractmethod
    @task
    def do_oscillation(self, start, end, exptime, npass):
        pass


    @abc.abstractmethod
    @task
    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
      pass

    @abc.abstractmethod
    def last_image_saved(self):
      pass

    @abc.abstractmethod
    @task
    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment):
        pass
      

    @abc.abstractmethod
    @task
    def start_acquisition(self, exptime, npass, first_frame):
        pass


    @abc.abstractmethod
    @task
    def stop_acquisition(self):
      # detector's readout
      pass


    @abc.abstractmethod
    @task
    def write_image(self, last_frame):
        pass


    @abc.abstractmethod
    @task
    def reset_detector(self):
        pass


    @abc.abstractmethod
    @task
    def data_collection_cleanup(self):
        pass


    @abc.abstractmethod
    def get_wavelength(self):
      pass


    @abc.abstractmethod
    def get_detector_distance(self):
      pass


    @abc.abstractmethod
    def get_resolution(self):
      pass


    @abc.abstractmethod
    def get_transmission(self):
      pass


    @abc.abstractmethod
    def get_undulators_gaps(self):
      pass


    @abc.abstractmethod
    def get_resolution_at_corner(self):
      pass


    @abc.abstractmethod
    def get_beam_size(self):
      pass


    @abc.abstractmethod
    def get_slit_gaps(self):
      pass


    @abc.abstractmethod
    def get_beam_shape(self):
      pass

    @abc.abstractmethod
    def get_beam_centre(self):
      pass

    @abc.abstractmethod
    def get_measured_intensity(self):
      pass


    @abc.abstractmethod
    def get_machine_current(self):
      pass

    @abc.abstractmethod
    def get_machine_fill_mode(self):
      pass

    
    @abc.abstractmethod
    def get_machine_message(self):
      pass


    @abc.abstractmethod
    def get_cryo_temperature(self):
      pass


    @abc.abstractmethod
    def get_flux(self):
      """Return flux in photons/second"""
      pass


    @abc.abstractmethod
    def store_image_in_lims(self, frame, first_frame, last_frame):
      pass

    
    @abc.abstractmethod
    @task
    def generate_image_jpeg(self, filename, jpeg_path, jpeg_thumbnail_path):
        pass
    

    def get_sample_info_from_parameters(self, parameters):
        """Returns sample_id, sample_location and sample_code from data collection parameters"""
        sample_info = parameters.get("sample_reference")
        try:
            sample_id = int(sample_info["blSampleId"])
        except:
            sample_id = None
        
        try:
            sample_code = sample_info["code"]
        except:
            sample_code = None

        sample_location = None
        
        try:
            sample_container_number = int(sample_info['container_reference'])
        except:
            pass
        else:
            try:
                vial_number = int(sample_info["sample_location"])
            except:
                pass
            else:
                sample_location = (sample_container_number, vial_number)
            
        return sample_id, sample_location, sample_code


    def create_directories(self, *args):
        for directory in args:
            try:
                os.makedirs(directory)
            except os.error as e:
                if e.errno != errno.EEXIST:
                    raise
     

    def _take_crystal_snapshots(self, number_of_snapshots):
      if isinstance(number_of_snapshots, bool):
        # backward compatibility, if number_of_snapshots is True|False
        if number_of_snapshots:
          return self.take_crystal_snapshots(4)
        else:
          return
      if number_of_snapshots:
          return self.take_crystal_snapshots(number_of_snapshots)


    @abc.abstractmethod
    @task
    def take_crystal_snapshots(self, number_of_snapshots):
      pass

       
    @abc.abstractmethod
    def set_helical(self, helical_on):
      pass


    @abc.abstractmethod
    def set_helical_pos(self, helical_pos):
      pass

 
    def prepare_wedges_to_collect(self, start, nframes, osc_range, subwedge_size=1, overlap=0):
        if overlap == 0:
          wedge_sizes_list = [nframes//subwedge_size]*subwedge_size
        else:
          wedge_sizes_list = [subwedge_size]*(nframes//subwedge_size)
        remaining_frames = nframes % subwedge_size
        if remaining_frames:
            wedge_sizes_list.append(remaining_frames)
        
        wedges_to_collect = []

        for wedge_size in wedge_sizes_list:
            orig_start = start
            
            wedges_to_collect.append((start, wedge_size))
            start += wedge_size*osc_range - overlap

        return wedges_to_collect

    def update_oscillations_history(self, data_collect_parameters):
      sample_id, sample_code, sample_location = self.get_sample_info_from_parameters(data_collect_parameters)
      self.oscillations_history.append((sample_id, sample_code, sample_location, data_collect_parameters))
      return len(self.oscillations_history), sample_id, sample_code, sample_location


    @abc.abstractmethod
    def get_archive_directory(self, directory):
      pass


    @abc.abstractmethod
    def prepare_input_files(self, files_directory, prefix, run_number, process_directory):
        """Return XDS input file directory"""
        pass


    @abc.abstractmethod
    @task
    def write_input_files(self, collection_id):
        pass

    def execute_collect_without_loop(self, data_collect_parameters):
        return

    def do_collect(self, owner, data_collect_parameters):
        if self.__safety_shutter_close_task is not None:
            self.__safety_shutter_close_task.kill()

        logging.getLogger("user_level_log").info("Closing fast shutter")
        self.close_fast_shutter()

        # reset collection id on each data collect
        self.collection_id = None

        # Preparing directory path for images and processing files
        # creating image file template and jpegs files templates
        file_parameters = data_collect_parameters["fileinfo"]

        file_parameters["suffix"] = self.bl_config.detector_fileext
        image_file_template = "%(prefix)s_%(run_number)s_%%04d.%(suffix)s" % file_parameters
        file_parameters["template"] = image_file_template

        archive_directory = self.get_archive_directory(file_parameters["directory"])
        data_collect_parameters["archive_dir"] = archive_directory

        if archive_directory:
          jpeg_filename="%s.jpeg" % os.path.splitext(image_file_template)[0]
          thumb_filename="%s.thumb.jpeg" % os.path.splitext(image_file_template)[0]
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
        self.xds_directory, self.mosflm_directory, self.hkl2000_directory = self.prepare_input_files(file_parameters["directory"], file_parameters["prefix"], file_parameters["run_number"], file_parameters['process_directory'])
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
        take_snapshots = data_collect_parameters.get("take_snapshots", False)
        if take_snapshots:
            logging.getLogger("user_level_log").info("Taking sample snapshosts")
            self._take_crystal_snapshots(take_snapshots)
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
                if 'kappa' in data_collect_parameters['actualCenteringPosition']:
                    data_collect_parameters['oscillation_sequence'][0]['kappaStart'] = current_diffractometer_position['kappa']
                    data_collect_parameters['oscillation_sequence'][0]['phiStart'] = current_diffractometer_position['kappa_phi']
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
        self.first_image_timeout = 30+oscillation_parameters["exposure_time"]
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

        # 0: software binned, 1: unbinned, 2:hw binned
        self.set_detector_mode(data_collect_parameters["detector_mode"])

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
                    beam_centre_x, beam_centre_y = self.get_beam_centre()
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
                self.write_input_files(self.collection_id, wait=False) 

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
                for start, wedge_size in wedges_to_collect:
                    logging.getLogger("user_level_log").info("Preparing acquisition, start=%f, wedge size=%d", start, wedge_size)
                    self.prepare_acquisition(1 if data_collect_parameters.get("dark", 0) else 0,
                                             start,
                                             osc_range,
                                             exptime,
                                             npass,
                                             wedge_size,
                                             data_collect_parameters["comment"])
                    data_collect_parameters["dark"] = 0

                    i = 0
                    j = wedge_size
                    while j > 0: 
                      frame_start = start+i*osc_range
                      i+=1

                      filename = image_file_template % frame
                      try:
                        jpeg_full_path = jpeg_file_template % frame
                        jpeg_thumbnail_full_path = jpeg_thumbnail_file_template % frame
                      except:
                        jpeg_full_path = None
                        jpeg_thumbnail_full_path = None
                      file_location = file_parameters["directory"]
                      file_path  = os.path.join(file_location, filename)

                      self.set_detector_filenames(frame, frame_start, str(file_path), str(jpeg_full_path), str(jpeg_thumbnail_full_path))
                      osc_start, osc_end = self.prepare_oscillation(frame_start, osc_range, exptime, npass)

                      with error_cleanup(self.reset_detector):
                          self.start_acquisition(exptime, npass, j == wedge_size)
                          self.do_oscillation(osc_start, osc_end, exptime, npass)
                          self.stop_acquisition()
                          self.write_image(j == 1)
                                     
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

                          if data_collect_parameters.get("shutterless"):
                              with gevent.Timeout(self.first_image_timeout, RuntimeError("Timeout waiting for detector trigger, no image taken")):
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

        # data collection done
        self.data_collection_end_hook(data_collect_parameters)

                
    @task
    def loop(self, owner, data_collect_parameters_list):
        failed_msg = "Data collection failed!"
        failed = True
        collections_analyse_params = []

        try:
            self.emit("collectReady", (False, ))
            self.emit("collectStarted", (owner, 1))
            for data_collect_parameters in data_collect_parameters_list:
                logging.debug("collect parameters = %r", data_collect_parameters)
                failed = False
                try:
                  # emit signals to make bricks happy
                  osc_id, sample_id, sample_code, sample_location = self.update_oscillations_history(data_collect_parameters)
                  self.emit('collectOscillationStarted', (owner, sample_id, sample_code, sample_location, data_collect_parameters, osc_id))
                  data_collect_parameters["status"]='Running'
                  
                  # now really start collect sequence
                  self.do_collect(owner, data_collect_parameters)
                except:
                  failed = True
                  exc_type, exc_value, exc_tb = sys.exc_info()
                  logging.exception("Data collection failed")
                  data_collect_parameters["status"] = 'Data collection failed!' #Message to be stored in LIMS
                  failed_msg = 'Data collection failed!\n%s' % exc_value
                  self.emit("collectOscillationFailed", (owner, False, failed_msg, self.collection_id, osc_id))
                else:
                  data_collect_parameters["status"]='Data collection successful'

                try:
                  if data_collect_parameters.get("processing", False)=="True":
                    self.trigger_auto_processing("after",
                                                 self.xds_directory,
                                                 data_collect_parameters["EDNA_files_dir"],
                                                 data_collect_parameters["anomalous"],
                                                 data_collect_parameters["residues"],
                                                 data_collect_parameters["do_inducedraddam"],
                                                 data_collect_parameters.get("sample_reference", {}).get("spacegroup", ""),
                                                 data_collect_parameters.get("sample_reference", {}).get("cell", ""))
                except:
                  pass
                else:
                   collections_analyse_params.append((self.collection_id,
                                                      self.xds_directory, 
                                                      data_collect_parameters["EDNA_files_dir"],
                                                      data_collect_parameters["anomalous"],
                                                      data_collect_parameters["residues"],
                                                      "reference_interval" in data_collect_parameters["oscillation_sequence"][0],
                                                      data_collect_parameters["do_inducedraddam"]))
  
                if self.bl_control.lims:    
                  data_collect_parameters["flux_end"]=self.get_flux()
                  try:
                    self.bl_control.lims.update_data_collection(data_collect_parameters)
                  except:
                    logging.getLogger("HWR").exception("Could not store data collection into LIMS")
                                  
                if failed:
                  # if one dc fails, stop the whole loop
                  break
                else:
                  self.emit("collectOscillationFinished", (owner, True, data_collect_parameters["status"], self.collection_id, osc_id, data_collect_parameters))

            try:
              self.__safety_shutter_close_task = gevent.spawn_later(10*60, self.close_safety_shutter, timeout=10)
            except:
              logging.exception("Could not close safety shutter")
        finally:
           self.emit("collectEnded", owner, not failed, failed_msg if failed else "Data collection successful")
           self.emit("collectReady", (True, ))

    def collect_without_loop(self, data_collect_parameters_list):
        in_multicollect = len(data_collect_parameters_list) > 1
        collections_analyse_params = []
        self.emit("collectReady", (False, ))
        #self.emit("collectStarted", (self.owner, 1))
        total_frames = 0
        total_time_sec = 0
        # in principle data_collect_parameters_list always has one element
        # Two options: rename this module to AbstractCollect
        # or fully implement multicollect 
        for data_collect_parameters in data_collect_parameters_list:
            total_frames = total_frames + data_collect_parameters['oscillation_sequence'][0]['number_of_images']
            total_time_sec = total_time_sec + total_frames + 2* \
                             (data_collect_parameters['oscillation_sequence'][0]['exposure_time'] + 0.02)
        self.emit("collectOverallFramesTime", (total_frames, int(total_time_sec)))
        for data_collect_parameters in data_collect_parameters_list:
            self.actual_data_collect_parameters = data_collect_parameters
            self.osc_id, sample_id, sample_code, sample_location = \
                 self.update_oscillations_history(self.actual_data_collect_parameters)
            self.emit('collectOscillationStarted', (self.owner, sample_id, \
                 sample_code, sample_location, self.actual_data_collect_parameters, self.osc_id))
            self.actual_data_collect_parameters["status"]='Running'
            self.do_collect(self.owner, self.actual_data_collect_parameters)

    def collect(self, owner, data_collect_parameters_list): #, finished_callback=None):
        if self.run_without_loop: 
            self.owner = owner
            self.ready_event.clear()
            self.data_collect_task = gevent.spawn(self.collect_without_loop,
                                         data_collect_parameters_list)
            self.ready_event.wait()
            self.ready_event.clear()
        else:
            self.data_collect_task = self.loop(owner, data_collect_parameters_list, wait = False)
        return self.data_collect_task


    #TODO: rename to stop_collect
    def stopCollect(self, owner):
        if self.data_collect_task is not None:
            self.data_collect_task.kill(block = False)


    """
    processDataScripts
        Description    : executes a script after the data collection has finished
        Type           : method
    """
    def trigger_auto_processing(self, process_event, xds_dir, EDNA_files_dir=None, anomalous=None, residues=200, do_inducedraddam=False, spacegroup=None, cell=None):
      # quick fix for anomalous, do_inducedraddam... passed as a string!!!
      # (comes from the queue)
      if type(anomalous) == types.StringType:
        anomalous = anomalous == "True"      
      if type(do_inducedraddam) == types.StringType:
        do_inducedraddam = do_inducedraddam == "True" 
      if type(residues) == types.StringType:
        try:
          residues = int(residues)
        except:
          residues = 200

      # residues = zero should be interpreted as if no value was provided
      # use default of 200
      if residues == 0:
          residues = 200

      processAnalyseParams = {}
      processAnalyseParams['EDNA_files_dir'] = EDNA_files_dir

      try:
        if type(xds_dir) == types.ListType:
            processAnalyseParams["collections_params"] = xds_dir
        else:
            processAnalyseParams['datacollect_id'] = self.collection_id
            processAnalyseParams['xds_dir'] = xds_dir
        processAnalyseParams['anomalous'] = anomalous
        processAnalyseParams['residues'] = residues
        processAnalyseParams["spacegroup"]=spacegroup
        processAnalyseParams["cell"]=cell
      except Exception as msg:
        logging.getLogger().exception("DataCollect:processing: %r" % str(msg))
      else:
        #logging.info("AUTO PROCESSING: %s, %s, %s, %s, %s, %s, %r, %r", process_event, EDNA_files_dir, anomalous, residues, do_inducedraddam, spacegroup, cell)
            
        try: 
            autoprocessing.start(self["auto_processing"], process_event, processAnalyseParams)
        except:
            logging.getLogger().exception("Error starting processing")
          
        if process_event=="after" and do_inducedraddam:
            try:
              autoprocessing.startInducedRadDam(processAnalyseParams)
            except:
              logging.exception("Error starting induced rad.dam")
    
    def set_run_autoprocessing(self, status):
        pass

    # specifies the next scan will be a mesh scan
    def set_mesh(self, mesh_on):
        self.mesh = mesh_on

    def set_mesh_scan_parameters(self, num_lines, total_nb_frames, mesh_center_param, mesh_range_param):
        """
        sets the mesh scan parameters :
         - vertcal range
         - horizontal range
         - nb lines
         - nb frames per line
         - invert direction (boolean)  # NOT YET DONE
         """
        self.mesh_num_lines = num_lines
        self.mesh_total_nb_frames = total_nb_frames
        self.mesh_range = mesh_range_param
        self.mesh_center = mesh_center_param
