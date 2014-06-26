from HardwareRepository.BaseHardwareObjects import HardwareObject
from AbstractMultiCollect import *
from gevent.event import AsyncResult
import logging
import time
import os
import httplib

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


class CcdDetector:
    @task
    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""):
        self.getChannelObject("take_dark").setValue(take_dark)
        self.execute_command("prepare_acquisition", take_dark, start, osc_range, exptime, npass, comment)
        #self.getCommandObject("build_collect_seq").executeCommand("write_dp_inputs(COLLECT_SEQ,MXBCM_PARS)", wait=True)

    @task
    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
        self.getCommandObject("prepare_acquisition").executeCommand('setMxCollectPars("current_phi", %f)' % start)
        self.getCommandObject("prepare_acquisition").executeCommand('setMxCurrentFilename("%s")' % filename)
        self.getCommandObject("prepare_acquisition").executeCommand("ccdfile(COLLECT_SEQ, %d)" % frame_number, wait=True)
       
    @task
    def prepare_oscillation(self, start, osc_range, exptime, npass):
        if osc_range < 1E-4:
            # still image
            return (start, start+osc_range)
        else:
            self.execute_command("prepare_oscillation", start, start+osc_range, exptime, npass)
            return (start, start+osc_range)
        
    @task
    def do_oscillation(self, start, end, exptime, npass):
        self.execute_command("do_oscillation", start, end, exptime, npass)

    @task
    def start_acquisition(self, exptime, npass, first_frame):
        self.execute_command("start_acquisition")  
      
    @task
    def write_image(self, last_frame):
        if last_frame:
            self.execute_command("flush_detector")
        else:
            self.execute_command("write_image")

    @task
    def stop_acquisition(self):
        self.execute_command("detector_readout")
      
    @task
    def reset_detector(self):   
        self.getCommandObject("reset_detector").abort()
        self.execute_command("reset_detector")


class PixelDetector:
    def __init__(self):
        self.shutterless = True
        self.new_acquisition = True
        self.oscillation_task = None
        self.shutterless_exptime = None
        self.shutterless_range = None

    @task
    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""):
        self.new_acquisition = True
        if  osc_range < 0.0001:
            self.shutterless = False
        take_dark = 0
        if self.shutterless:
            self.shutterless_range = osc_range*number_of_images
            self.shutterless_exptime = (exptime + 0.003)*number_of_images
        self.execute_command("prepare_acquisition", take_dark, start, osc_range, exptime, npass, comment)
        #self.getCommandObject("build_collect_seq").executeCommand("write_dp_inputs(COLLECT_SEQ,MXBCM_PARS)",wait=True)
        
    @task
    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
      if self.shutterless and not self.new_acquisition:
          return

      self.getCommandObject("prepare_acquisition").executeCommand('setMxCollectPars("current_phi", %f)' % start)
      self.getCommandObject("prepare_acquisition").executeCommand('setMxCurrentFilename("%s")' % filename)
      self.getCommandObject("prepare_acquisition").executeCommand("ccdfile(COLLECT_SEQ, %d)" % frame_number, wait=True)

    @task
    def prepare_oscillation(self, start, osc_range, exptime, npass):
        if self.shutterless:
            if self.new_acquisition:
                self.execute_command("prepare_oscillation", start, start+self.shutterless_range, self.shutterless_exptime, npass)
        else:
            if osc_range < 1E-4:
                # still image
                pass
            else:
                self.execute_command("prepare_oscillation", start, start+osc_range, exptime, npass)
        return (start, start+osc_range)

    @task
    def start_acquisition(self, exptime, npass, first_frame):
      if not first_frame and self.shutterless:
        pass 
      else:
        self.execute_command("start_acquisition")

    @task
    def do_oscillation(self, start, end, exptime, npass):
      if self.shutterless:
          if self.new_acquisition:
              # only do this once per collect
              npass = 1
              exptime = self.shutterless_exptime
              end = start + self.shutterless_range
          
              # make oscillation an asynchronous task => do not wait here
              self.oscillation_task = self.execute_command("do_oscillation", start, end, exptime, npass, wait=False)
          else:
              time.sleep(0.89*exptime)

              try:
                 self.oscillation_task.get(block=False)
              except gevent.Timeout:
                 pass #no result yet, it is normal
              except:
                 # an exception occured in task! Pilatus server died?
                 raise
      else:
          self.execute_command("do_oscillation", start, end, exptime, npass)
    
    @task
    def write_image(self, last_frame):
      if last_frame:
        if self.shutterless:
            self.oscillation_task.get()
            self.execute_command("specific_collect_frame_hook")

    def stop_acquisition(self):
        self.new_acquisition = False
      
    @task
    def reset_detector(self):
      if self.shutterless:
          self.oscillation_task.kill()
      self.getCommandObject("reset_detector").abort()    
      self.execute_command("reset_detector")


class ESRFMultiCollect(AbstractMultiCollect, HardwareObject):
    def __init__(self, name, detector, tunable_bl):
        AbstractMultiCollect.__init__(self)
        HardwareObject.__init__(self, name)
        self._detector = detector
        self._tunable_bl = tunable_bl
        self._centring_status = None

    def execute_command(self, command_name, *args, **kwargs): 
      wait = kwargs.get("wait", True)
      cmd_obj = self.getCommandObject(command_name)
      return cmd_obj(*args, wait=wait)
          
        
    def init(self):
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
                               flux = self.getObjectByRole("flux"))

        mxlocalHO = self.getObjectByRole("beamline_configuration")
        bcm_pars = mxlocalHO["BCM_PARS"]
        spec_pars = mxlocalHO["SPEC_PARS"]
        try:
          undulators = bcm_pars["undulator"]
        except IndexError:
          undulators = []
        self.setBeamlineConfiguration(directory_prefix = self.getProperty("directory_prefix"),
                                      default_exposure_time = bcm_pars.getProperty("default_exposure_time"),
                                      default_number_of_passes = bcm_pars.getProperty("default_number_of_passes"),
                                      maximum_radiation_exposure = bcm_pars.getProperty("maximum_radiation_exposure"),
                                      nominal_beam_intensity = bcm_pars.getProperty("nominal_beam_intensity"),
                                      minimum_exposure_time = bcm_pars.getProperty("minimum_exposure_time"),
                                      minimum_phi_speed = bcm_pars.getProperty("minimum_phi_speed"),
                                      minimum_phi_oscillation = bcm_pars.getProperty("minimum_phi_oscillation"),
                                      maximum_phi_speed = bcm_pars.getProperty("maximum_phi_speed"),
                                      detector_fileext = bcm_pars.getProperty("FileSuffix"),
                                      detector_type = bcm_pars["detector"].getProperty("type"),
                                      detector_mode = spec_pars["detector"].getProperty("binning"),
                                      detector_manufacturer = bcm_pars["detector"].getProperty("manufacturer"),
                                      detector_model = bcm_pars["detector"].getProperty("model"),
                                      detector_px = bcm_pars["detector"].getProperty("px"),
                                      detector_py = bcm_pars["detector"].getProperty("py"),
                                      beam_ax = spec_pars["beam"].getProperty("ax"),
                                      beam_ay = spec_pars["beam"].getProperty("ay"),
                                      beam_bx = spec_pars["beam"].getProperty("bx"),
                                      beam_by = spec_pars["beam"].getProperty("by"),
                                      undulators = undulators,
                                      focusing_optic = bcm_pars.getProperty('focusing_optic'),
                                      monochromator_type = bcm_pars.getProperty('monochromator'),
                                      beam_divergence_vertical = bcm_pars.getProperty('beam_divergence_vertical'),
                                      beam_divergence_horizontal = bcm_pars.getProperty('beam_divergence_horizontal'),     
                                      polarisation = bcm_pars.getProperty('polarisation'),
                                      input_files_server = self.getProperty("input_files_server"))
  
	self.getChannelObject("spec_messages").connectSignal("update", self.log_message_from_spec)

        self._detector.getCommandObject = self.getCommandObject
        self._detector.getChannelObject = self.getChannelObject
        self._detector.execute_command = self.execute_command
        self._tunable_bl.bl_control = self.bl_control

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True, ))


    def log_message_from_spec(self, msg):
        logging.getLogger("user_level_log").info(msg)      


    @task
    def take_crystal_snapshots(self, number_of_snapshots):
        self.bl_control.diffractometer.takeSnapshots(number_of_snapshots, wait=True)

    #TODO: remove this hook!!!
    @task
    def data_collection_hook(self, data_collect_parameters):
        return
 

    @task
    def set_transmission(self, transmission_percent):
        self.bl_control.transmission.setTransmission(transmission_percent)


    def set_wavelength(self, wavelength):
        return self._tunable_bl.set_wavelength(wavelength)


    def set_energy(self, energy):
        return self._tunable_bl.set_energy(energy)


    @task
    def set_resolution(self, new_resolution):
        return
        

    @task
    def move_detector(self, detector_distance):
        return


    @task
    def data_collection_cleanup(self):
        self.execute_command("close_fast_shutter")


    @task
    def close_fast_shutter(self):
        self.execute_command("close_fast_shutter")


    @task
    def open_fast_shutter(self):
        self.execute_command("open_fast_shutter")

        
    @task
    def move_motors(self, motor_position_dict):
        for motor in motor_position_dict.keys(): #iteritems():
            position = motor_position_dict[motor]
            if isinstance(motor, str) or isinstance(motor, unicode):
                # find right motor object from motor role in diffractometer obj.
                motor_role = motor
                motor = self.bl_control.diffractometer.getDeviceByRole(motor_role)
                del motor_position_dict[motor_role]
                if motor is None:
                  continue
                motor_position_dict[motor]=position

            logging.getLogger("HWR").info("Moving motor '%s' to %f", motor.getMotorMnemonic(), position)
            motor.move(position)

        while any([motor.motorIsMoving() for motor in motor_position_dict.iterkeys()]):
            logging.getLogger("HWR").info("Waiting for end of motors motion")
            time.sleep(0.5)  


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


    @task
    def prepare_intensity_monitors(self):
        self.execute_command("adjust_gains")


    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""):
        return self._detector.prepare_acquisition(take_dark, start, osc_range, exptime, npass, number_of_images, comment)


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


    def stop_acquisition(self):
        return self._detector.stop_acquisition()
        
      
    def reset_detector(self):
        return self._detector.reset_detector()
        

    def prepare_input_files(self, files_directory, prefix, run_number, process_directory):
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

        for dir in (self.raw_data_input_file_dir, xds_directory):
          self.create_directories(dir)
          logging.info("Creating XDS processing input file directory: %s", dir)
          os.chmod(dir, 0777)
        for dir in (self.mosflm_raw_data_input_file_dir, mosflm_directory):
          self.create_directories(dir)
          logging.info("Creating MOSFLM processing input file directory: %s", dir)
          os.chmod(dir, 0777)
        for dir in (self.raw_hkl2000_dir, hkl2000_directory):
          self.create_directories(dir)
          os.chmod(dir, 0777)
 
        try: 
          try: 
              os.symlink(files_directory, os.path.join(process_directory, "links"))
          except os.error, e:
              if e.errno != errno.EEXIST:
                  raise
        except:
            logging.exception("Could not create processing file directory")

        return xds_directory, mosflm_directory, hkl2000_directory


    @task
    def write_input_files(self, collection_id):
        # assumes self.xds_directory and self.mosflm_directory are valid
        conn = httplib.HTTPConnection(self.bl_config.input_files_server)

        # hkl input files 
        for input_file_dir, file_prefix in ((self.raw_hkl2000_dir, "../.."), (self.hkl2000_directory, "../links")): 
            hkl_file_path = os.path.join(input_file_dir, "def.site")
            conn.request("GET", "/def.site/%d?basedir=%s" % (collection_id, file_prefix))
            hkl_file = open(hkl_file_path, "w")
            r = conn.getresponse()

            if r.status != 200:
                logging.error("Could not create input file")
                return

            hkl_file.write(r.read())
            hkl_file.close()
            os.chmod(hkl_file_path, 0666)

        for input_file_dir, file_prefix in ((self.raw_data_input_file_dir, "../.."), (self.xds_directory, "../links")): 
	  xds_input_file = os.path.join(input_file_dir, "XDS.INP")
          conn.request("GET", "/xds.inp/%d?basedir=%s" % (collection_id, file_prefix))
          xds_file = open(xds_input_file, "w")
          r = conn.getresponse()
          if r.status != 200:
            logging.error("Could not create input file")
            return
          xds_file.write(r.read())
          xds_file.close()
          os.chmod(xds_input_file, 0666)

        for input_file_dir, file_prefix in ((self.mosflm_raw_data_input_file_dir, "../.."), (self.mosflm_directory, "../links")): 
	  mosflm_input_file = os.path.join(input_file_dir, "mosflm.inp")
          conn.request("GET", "/mosflm.inp/%d?basedir=%s" % (collection_id, file_prefix))
          mosflm_file = open(mosflm_input_file, "w")
          mosflm_file.write(conn.getresponse().read()) 
          mosflm_file.close()
          os.chmod(mosflm_input_file, 0666)
        
        # also write input file for STAC
        for stac_om_input_file_name, stac_om_dir in (("mosflm.descr", self.mosflm_directory), 
                                                     ("xds.descr", self.xds_directory),
                                                     ("mosflm.descr", self.mosflm_raw_data_input_file_dir),
                                                     ("xds.descr", self.raw_data_input_file_dir)):
          stac_om_input_file = os.path.join(stac_om_dir, stac_om_input_file_name)
          conn.request("GET", "/stac.descr/%d" % collection_id)
          stac_om_file = open(stac_om_input_file, "w")
          stac_template = conn.getresponse().read()
          if stac_om_input_file_name.startswith("xds"):
            om_type="xds"
            if stac_om_dir == self.raw_data_input_file_dir:
              om_filename=os.path.join(stac_om_dir, "CORRECT.LP")
            else:
              om_filename=os.path.join(stac_om_dir, "xds_fastproc", "CORRECT.LP")
          else:
            om_type="mosflm"
            om_filename=os.path.join(stac_om_dir, "bestfile.par")
       
          stac_om_file.write(stac_template.format(omfilename=om_filename, omtype=om_type, 
                             phi=self.bl_control.diffractometer.phiMotor.getPosition(), 
                             sampx=self.bl_control.diffractometer.sampleXMotor.getPosition(), 
                             sampy=self.bl_control.diffractometer.sampleYMotor.getPosition(), 
                             phiy=self.bl_control.diffractometer.phiyMotor.getPosition()))
          stac_om_file.close()
          os.chmod(stac_om_input_file, 0666)


    def get_wavelength(self):
        return self._tunable_bl.get_wavelength()
      

    def get_detector_distance(self):
        return

       
    def get_resolution(self):
        return self.bl_control.resolution.getPosition()


    def get_transmission(self):
        return self.bl_control.transmission.getAttFactor()


    def get_undulators_gaps(self):
        """
        und_gaps = [None]*3
        i = 0
        try:
            for undulator_cfg in self.bl_config.undulators:
                und_gaps[i]=self.bl_control.undulators.getUndulatorGap(undulator_cfg.getProperty("type"))
                i+=1
        except:
            logging.getLogger("HWR").exception("Could not get undulator gaps")
        return und_gaps
        """
        all_gaps = {'Unknown': None}
        try:
            _gaps = self.bl_control.undulators.getUndulatorGaps()
        except:
            logging.getLogger("HWR").exception("Could not get undulator gaps")
        all_gaps.clear()
        for key in _gaps:
            if  '_Position' in key:
                nkey = key[:-9]
                all_gaps[nkey] = _gaps[key]
            else:
                all_gaps = _gaps
        return all_gaps

    def get_resolution_at_corner(self):
      return self.execute_command("get_resolution_at_corner")


    def get_beam_size(self):
      return (self.execute_command("get_beam_size_x"), self.execute_command("get_beam_size_y"))


    def get_slit_gaps(self):
      return (self.execute_command("get_slit_gap_h"), self.execute_command("get_slit_gap_v"))


    def get_beam_shape(self):
      return self.execute_command("get_beam_shape")

    
    def get_measured_intensity(self):
      try:
        val = self.getChannelObject("image_intensity").getValue()
        return float(val)
      except:
        return 0


    def get_machine_current(self):
        if self.bl_control.machine_current:
            return self.bl_control.machine_current.getCurrent()
        else:
            return 0


    def get_machine_message(self):
        if  self.bl_control.machine_current:
            return self.bl_control.machine_current.getMessage()
        else:
            return ''


    def get_machine_fill_mode(self):
        if self.bl_control.machine_current:
            return self.bl_control.machine_current.getFillMode()
        else:
            ''

    def get_cryo_temperature(self):
      return self.bl_control.cryo_stream.getTemperature()


    def getCurrentEnergy(self):
      return self._tunable_bl.getCurrentEnergy()


    def get_beam_centre(self):
      return (self.execute_command("get_beam_centre_x"), self.execute_command("get_beam_centre_y"))

    
    def getBeamlineConfiguration(self, *args):
      # TODO: change this to stop using a dictionary at the other end
      return self.bl_config._asdict()


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


    def sanityCheck(self, collect_params):
        return
    

    def setBrick(self, brick):
        return


    def directoryPrefix(self):
        return self.bl_config.directory_prefix


    def store_image_in_lims(self, frame, first_frame, last_frame):
        if isinstance(self._detector, CcdDetector):
            return True

        if isinstance(self._detector, PixelDetector):
            if first_frame or last_frame:
                return True

    def get_flux(self):
        return self.bl_control.flux.getCurrentFlux()

    """
    getOscillation
        Description: Returns the parameters (and results) of an oscillation.
        Type       : method
        Arguments  : oscillation_id (int; the oscillation id, the last parameters of the collectOscillationStarted
                                     signal)
        Returns    : tuple; (blsampleid,barcode,location,parameters)
    """
    def getOscillation(self, oscillation_id):
      return self.oscillations_history[oscillation_id - 1]
       

    def sampleAcceptCentring(self, accepted, centring_status):
      self.sample_centring_done(accepted, centring_status)


    def setCentringStatus(self, centring_status):
      self._centring_status = centring_status


    """
    getOscillations
        Description: Returns the history of oscillations for a session
        Type       : method
        Arguments  : session_id (int; the session id, stored in the "sessionId" key in each element
                                 of the parameters list in the collect method)
        Returns    : list; list of all oscillation_id for the specified session
    """
    def getOscillations(self,session_id):
      #TODO
      return []


    def get_archive_directory(self, directory):
        res = None
       
        dir_path_list = directory.split(os.path.sep)
        try:
          suffix_path=os.path.join(*dir_path_list[4:])
        except TypeError:
          return None
        else:
          if 'inhouse' in directory:
            archive_dir = os.path.join('/data/pyarch/', dir_path_list[2], suffix_path)
          else:
            archive_dir = os.path.join('/data/pyarch/', dir_path_list[4], dir_path_list[3], *dir_path_list[5:])
          if archive_dir[-1] != os.path.sep:
            archive_dir += os.path.sep
            
          return archive_dir
