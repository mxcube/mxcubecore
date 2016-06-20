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
from MAXIV.BIOMAXPilatus import BIOMAXPilatus

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


class PixelDetector:
    def __init__(self, detector_class=None):
        self._detector = detector_class() if detector_class else None
        self.shutterless = True
        self.new_acquisition = True
        self.oscillation_task = None
        self.shutterless_exptime = None
        self.shutterless_range = None

    def init(self, config, collect_obj):
        self.collect_obj = collect_obj
        if self._detector:
          self._detector.addChannel = self.addChannel
          self._detector.addCommand = self.addCommand
          self._detector.getChannelObject = self.getChannelObject
          self._detector.getCommandObject = self.getCommandObject
          self._detector.init(config, collect_obj)

    def last_image_saved(self):
        return self._detector.last_image_saved()

    @task
    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment="", energy=None):
        self.new_acquisition = True
        if osc_range < 1E-4:
            still = True
        else:
            still = False
        take_dark = 0
        if self.shutterless:
            self.shutterless_range = osc_range*number_of_images
            self.shutterless_exptime = (exptime + self._detector.get_deadtime())*number_of_images
        if self._detector:
            self._detector.prepare_acquisition(take_dark, start, osc_range, exptime, npass, number_of_images, comment, energy, still)
        
    @task
    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
      if self.shutterless and not self.new_acquisition:
          return
 
      if self._detector:
          self._detector.set_detector_filenames(frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path)

    @task
    def prepare_oscillation(self, start, osc_range, exptime, npass):
        if self.shutterless:
            end = start+self.shutterless_range
            if self.new_acquisition:
                self.collect_obj.do_prepare_oscillation(start, end, self.shutterless_exptime, npass)
            return (start, end)
        else:
            if osc_range < 1E-4:
                # still image
                pass
            else:
                self.collect_obj.do_prepare_oscillation(start, start+osc_range, exptime, npass)
            return (start, start+osc_range)

    @task
    def start_acquisition(self, exptime, npass, first_frame):
        try:
            self.collect_obj.getObjectByRole("detector_cover").set_out()
        except:
            pass

        if not first_frame and self.shutterless:
            pass 
        else:
            if self._detector:
                self._detector.start_acquisition()

    @task
    def no_oscillation(self, exptime):
        self.collect_obj.open_fast_shutter()
        time.sleep(exptime)
        self.collect_obj.close_fast_shutter()

    @task
    def do_oscillation(self, start, end, exptime, npass):
      still = math.fabs(end-start) < 1E-4
      if self.shutterless:
          if self.new_acquisition:
              # only do this once per collect
              # make oscillation an asynchronous task => do not wait here
              if still:
                  self.oscillation_task = self.no_oscillation(self.shutterless_exptime, wait=False)
              else:
                  self.oscillation_task = self.collect_obj.oscil(start, end, self.shutterless_exptime, 1, wait=False)
          if self.oscillation_task.ready():
              self.oscillation_task.get()
      else:
          if still:
              self.no_oscillation(exptime)
          else:
              self.collect_obj.oscil(start, end, exptime, npass)
   
    @task
    def write_image(self, last_frame):
      if last_frame:
        if self.shutterless:
            self.oscillation_task.get()

    def stop_acquisition(self):
        self.new_acquisition = False
      
    @task
    def reset_detector(self):
      if self.shutterless:
          self.oscillation_task.kill()
      if self._detector:
          self._detector.stop()


class BIOMAXMultiCollect(AbstractMultiCollect, HardwareObject):

    def __init__(self, name):

        AbstractMultiCollect.__init__(self)
        HardwareObject.__init__(self, name)
        self._detector = PixelDetector(BIOMAXPilatus)
        self._tunable_bl = FixedEnergy(1.125, 11.0)
        self._centring_status = None
        self.helical = False

    def execute_command(self, command_name, *args, **kwargs): 
      wait = kwargs.get("wait", True)
      cmd_obj = self.getCommandObject(command_name)
      return cmd_obj(*args, wait=wait)
        
    def init(self):
        self.setControlObjects(diffractometer = self.getObjectByRole("diffractometer"),
                               sample_changer = self.getObjectByRole("sample_changer"),
                               #lims = self.getObjectByRole("dbserver"),
                               lims = None, # disable lims for the moment
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
                                      minimum_exposure_time = self.bl_control.detector.getProperty("minimum_exposure_time"),
                                      detector_fileext = self.bl_control.detector.getProperty("file_suffix"),
                                      detector_type = self.bl_control.detector.getProperty("type"),
                                      detector_manufacturer = self.bl_control.detector.getProperty("manufacturer"),
                                      detector_model = self.bl_control.detector.getProperty("model"),
                                      detector_px = self.bl_control.detector.getProperty("px"),
                                      detector_py = self.bl_control.detector.getProperty("py"),
                                      undulators = undulators,
                                      focusing_optic = self.getProperty('focusing_optic'),
                                      monochromator_type = self.getProperty('monochromator'),
                                      beam_divergence_vertical = self.bl_control.beam_info.get_beam_divergence_ver(),
                                      beam_divergence_horizontal = self.bl_control.beam_info.get_beam_divergence_hor(),
                                      polarisation = self.getProperty('polarisation'),
                                      input_files_server = self.getProperty("input_files_server"))
  
        self.archive_directory= self.getProperty("archive_directory")

        self._detector.addCommand = self.addCommand
        self._detector.addChannel = self.addChannel
        self._detector.getCommandObject = self.getCommandObject
        self._detector.getChannelObject = self.getChannelObject
        #self._detector.execute_command = self.execute_command
        self._detector.init(self.bl_control.detector, self)
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

    # to implement
    @task
    def loop_todel(self, owner, data_collect_parameters_list):
        failed_msg = "Data collection failed!"
        failed = True
        collections_analyse_params = []
        self.emit("collectReady", (False, ))
        self.emit("collectStarted", (owner, 1))

        print data_collect_parameters_list

        for data_collect_parameters in data_collect_parameters_list:
            logging.debug("collect parameters = %r", data_collect_parameters)
            failed = False
            data_collect_parameters["status"]='Data collection successful'
            osc_id, sample_id, sample_code, sample_location = self.update_oscillations_history(data_collect_parameters)
            self.emit('collectOscillationStarted', (owner, sample_id, sample_code, sample_location, data_collect_parameters, osc_id))

            for image in range(data_collect_parameters["oscillation_sequence"][0]["number_of_images"]):
                time.sleep(data_collect_parameters["oscillation_sequence"][0]["exposure_time"])
                self.emit("collectImageTaken", image)

            data_collect_parameters["status"]='Running'
            data_collect_parameters["status"]='Data collection successful'
            self.emit("collectOscillationFinished", (owner, True, data_collect_parameters["status"], "12345", osc_id, data_collect_parameters))

        self.emit("collectEnded", owner, not failed, failed_msg if failed else "Data collection successful")
        logging.getLogger('HWR').info("data collection successful in loop")
        self.emit("collectReady", (True, ))


    #TODO: remove this hook!!!
    @task
    def data_collection_hook(self, data_collect_parameters):
        return
 
    def do_prepare_oscillation(self, start, end, exptime, npass):
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
        print "osil now...."
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


    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""):
        energy = self._tunable_bl.getCurrentEnergy()
        return self._detector.prepare_acquisition(take_dark, start, osc_range, exptime, npass, number_of_images, comment, energy)


    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
        return self._detector.set_detector_filenames(frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path)

    def prepare_oscillation(self, start, osc_range, exptime, npass):
        return self._detector.prepare_oscillation(start, osc_range, exptime, npass)
    
    def do_oscillation(self, start, end, exptime, npass):
        return self._detector.do_oscillation(start, end, exptime, npass)
    
  
    def start_acquisition(self, exptime, npass, first_frame):
        return self._detector.start_acquisition(exptime, npass, first_frame)
    
      
    def write_image(self, last_frame):
        return self._detector.write_image(last_frame)


    def last_image_saved(self):
        return self._detector.last_image_saved()

    def stop_acquisition(self):
        return self._detector.stop_acquisition()
        
      
    def reset_detector(self):
        return self._detector.reset_detector()
        

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


    def get_beam_centre(self):
      return self.bl_control.beam_info.get_beam_position()
      #return (self.execute_command("get_beam_centre_x"), self.execute_command("get_beam_centre_y"))


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
        return self.archive_directory

    @task
    def generate_image_jpeg(self, filename, jpeg_path, jpeg_thumbnail_path):
        pass

    def get_cryo_temperature(self):
        if self.bl_control.cryo_stream is not None: 
            return self.bl_control.cryo_stream.getTemperature()
        else:
            return "NA"

    def get_detector_distance(self):
        return 120

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
        return

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
        self.actual_frame_num = 0
        i = 1
        while True:
          xds_input_file_dirname = "xds_%s_run%s_%d" % (prefix, run_number, i)
          xds_directory = os.path.join(process_directory, xds_input_file_dirname)

          if not os.path.exists(xds_directory):
            break

          i+=1

        mosflm_input_file_dirname = "mosflm_%s_run%s_%d" % (prefix, run_number, i)
        mosflm_directory = os.path.join(process_directory, mosflm_input_file_dirname)

        hkl2000_dirname = "hkl2000_%s_run%s_%d" % (prefix, run_number, i)
        hkl2000_directory = os.path.join(process_directory, hkl2000_dirname)

        self.raw_data_input_file_dir = os.path.join(files_directory, "process", xds_input_file_dirname)
        self.mosflm_raw_data_input_file_dir = os.path.join(files_directory, "process", mosflm_input_file_dirname)
        self.raw_hkl2000_dir = os.path.join(files_directory, "process", hkl2000_dirname)

        return xds_directory, mosflm_directory, hkl2000_directory

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
        return

    def set_helical_pos(self, helical_oscil_pos):
        return

    @task
    def write_input_files(self, collection_id):
        return

    def get_beam_centre(self):
        #x=723
        #y=808
        x = 731.89
        y = 822.40
        return (x*0.172, y*0.172)
        return self.bl_control.resolution.get_beam_centre()

    def get_detector_distance(self):
        #return 750
        return 150.0 # unit, mm
    
