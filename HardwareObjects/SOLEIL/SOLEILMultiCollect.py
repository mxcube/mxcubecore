# -*- coding: utf-8 -*-
from HardwareRepository.BaseHardwareObjects import HardwareObject
from AbstractMultiCollect import *
from gevent.event import AsyncResult
import logging
import time
import os
import math
import httplib
import PyTango
import threading
from collections import namedtuple


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
        logging.info("<SOLEIL MultiCollect TUNABLE ENERGY> VERIFY - set wavelength")
        energy_obj = self.bl_control.energy
        try:
            energy_obj.startMoveWavelength(wavelength)
        except:
            import traceback
            logging.info("<SOLEIL MultiCollect TUNABLE ENERGY> exception %s" % traceback.print_exc())
            print traceback.print_exc()
        while energy_obj.getState() != 'STANDBY':
            time.sleep(0.5)

    @task
    def set_energy(self, energy):
        logging.info("<SOLEIL MultiCollect TUNABLE ENERGY> VERIFY - set energy")
        logging.getLogger("user_level_log").info("Setting energy before collect")
        logging.info("self.bl_control.energy %s" % self.bl_control.energy)
        energy_obj = self.bl_control.energy
        energy_obj.startMoveEnergy(energy)
        logging.info("energy_obj.getState() %s " % energy_obj.getState())
        while energy_obj.getState() != 'STANDBY':
            time.sleep(0.5)

    def getCurrentEnergy(self):
        logging.info("<SOLEIL MultiCollect TUNABLE ENERGY> VERIFY - get current energy")
        return self.bl_control.energy.getCurrentEnergy()

    def get_wavelength(self):
        logging.info("<SOLEIL MultiCollect TUNABLE ENERGY> VERIFY - get wavelenth")
        return self.bl_control.energy.getCurrentWavelength()

class DummyDetector:
    @task
    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""):
        logging.info("<SOLEIL MultiCollect> DETECTOR DUMMY - prepare acquisition")

    @task
    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
        logging.info("<SOLEIL MultiCollect> DETECTOR DUMMY - set filenames")
       
    @task
    def prepare_oscillation(self, start, osc_range, exptime, npass):
        logging.info("<SOLEIL MultiCollect> DETECTOR DUMMY - prepare oscillation")
        return (start, start+osc_range)
        
    @task
    def do_oscillation(self, start, end, exptime, npass):
        logging.info("<SOLEIL MultiCollect> DETECTOR DUMMY - do oscillation")

    @task
    def start_acquisition(self, exptime, npass, first_frame):
        logging.info("<SOLEIL MultiCollect> DETECTOR DUMMY - start acquisition")
      
    @task
    def write_image(self, last_frame):
        logging.info("<SOLEIL MultiCollect> DETECTOR DUMMY - write image")

    @task
    def stop_acquisition(self):
        logging.info("<SOLEIL MultiCollect> DETECTOR DUMMY - stop acquisition")
      
    @task
    def reset_detector(self):   
        logging.info("<SOLEIL MultiCollect> DETECTOR DUMMY - reset acquisition")

class LimaPilatusDetector:
    def __init__(self):
        self.shutterless = True
        self.new_acquisition = True
        self.oscillation_task = None
        self.shutterless_exptime = None
        self.shutterless_range = None

        self.ready = False
        self.adscdev           = None
        self.limaadscdev       = None
        self.xformstatusfile   = None

    def initDetector(self, adscname, limaadscname, xformstatusfile):
        try: 
           self.adscdev           = PyTango.DeviceProxy(adscname) 
           self.limaadscdev       = PyTango.DeviceProxy(limaadscname) 
           self.xformstatusfile   = xformstatusfile
        except:
           import traceback
           logging.error("<SOLEIL MultiCollect> Cannot initialize LIMA detector")
           logging.error( traceback.format_exc() )
            
        else:
           self.ready = True
    @task
    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""):
        self.new_acquisition = True
        if  osc_range < 0.0001:
            self.shutterless = False
        take_dark = 0
        if self.shutterless:
            self.shutterless_range = osc_range*number_of_images
            self.shutterless_exptime = (exptime + 0.003)*number_of_images

        logging.getLogger("PILATUS").info("prepare acquisition. empty")      
        #self.execute_command("prepare_acquisition", take_dark, start, osc_range, exptime, npass, comment)
        #self.getCommandObject("build_collect_seq").executeCommand("write_dp_inputs(COLLECT_SEQ,MXBCM_PARS)",wait=True)
        
    @task
    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
      if self.shutterless and not self.new_acquisition:
          return

      logging.getLogger("PILATUS").info("set detector filenames. empty")      
      #self.getCommandObject("prepare_acquisition").executeCommand('setMxCollectPars("current_phi", %f)' % start)
      #self.getCommandObject("prepare_acquisition").executeCommand('setMxCurrentFilename("%s")' % filename)
      #self.getCommandObject("prepare_acquisition").executeCommand("ccdfile(COLLECT_SEQ, %d)" % frame_number, wait=True)

    @task
    def prepare_oscillation(self, start, osc_range, exptime, npass):
        if self.shutterless:
            if self.new_acquisition:
                logging.getLogger("PILATUS").info("prepare oscillation new. empty")      
                #self.execute_command("prepare_oscillation", start, start+self.shutterless_range, self.shutterless_exptime, npass)
        else:
            if osc_range < 1E-4:
                # still image
                pass
            else:
                logging.getLogger("PILATUS").info("prepare oscillation 2. empty")      
                #self.execute_command("prepare_oscillation", start, start+osc_range, exptime, npass)
        return (start, start+osc_range)

    @task
    def start_acquisition(self, exptime, npass, first_frame):
      if not first_frame and self.shutterless:
        time.sleep(exptime) 
      else:
        logging.getLogger("PILATUS").info("start acquisition. empty")      
        #self.execute_command("start_acquisition")

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
              logging.getLogger("PILATUS").info("do oscillation. empty")      
          else:
              try:
                 self.oscillation_task.get(block=False)
              except gevent.Timeout:
                 pass #no result yet, it is normal
              except:
                 # an exception occured in task! Pilatus server died?
                 raise
      else:
          #self.execute_command("do_oscillation", start, end, exptime, npass)
          logging.getLogger("PILATUS").info("do oscillation. empty")      
    
    @task
    def write_image(self, last_frame):
      if last_frame:
        if self.shutterless:
            self.oscillation_task.get()
            logging.getLogger("PILATUS").info("write image. empty")      
            #self.execute_command("specific_collect_frame_hook")

    def stop_acquisition(self):
        self.new_acquisition = False
      
    @task
    def reset_detector(self):
      if self.shutterless:
          self.oscillation_task.kill()
      logging.getLogger("PILATUS").info("resetting detector. empty")      
      #self.execute_command("reset_detector")


class LimaAdscDetector:
    def __init__(self):
        self.ready = False
        self.adscdev           = None
        self.limaadscdev       = None
        self.xformstatusfile   = None

    def initDetector(self, adscname, limaadscname, xformstatusfile):
        logging.info("<SOLEIL MultiCollect> Initializing LIMA detector")
        try: 
           self.adscdev           = PyTango.DeviceProxy(adscname) 
           self.limaadscdev       = PyTango.DeviceProxy(limaadscname) 
           self.xformstatusfile   = xformstatusfile
        except:
           import traceback
           logging.error("<SOLEIL MultiCollect> Cannot initialize LIMA detector")
           logging.error( traceback.format_exc() )
            
        else:
           self.ready = True

    @task
    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment="", lima_overhead=0.):
        if not self.ready:
            return
            
        logging.info('Preparing LIMA Detector')
        #if self.limaadscdev.state().name != 'STANDBY':
            #self.limaadscdev.Stop()
            #time.sleep(0.1)

        #if self.adscdev.state().name != 'STANDBY':
            #time.sleep(0.1)
        
        self.wait(self.adscdev)
        self.wait(self.limaadscdev)
        
        self.limaadscdev.exposuretime = (exptime + lima_overhead) * 1e3
        if (self.limaadscdev.get_timeout_millis() - self.limaadscdev.exposuretime) < 2000:
            self.limaadscdev.set_timeout_millis(int(self.limaadscdev.exposuretime) + 2000)
        
        self.wait(self.limaadscdev)
        self.limaadscdev.write_attribute('nbFrames', number_of_images)

    @task
    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
        if not self.ready:
          return

        self.imagePath   = os.path.dirname(filename)
        self.fileName    = os.path.basename(filename)
        self.imageNumber = frame_number

        logging.info('LIMA Detector - set filenames - imagePath is %s / filename is %s' % (self.imagePath, self.fileName))
        logging.info('   - thumbnail full path %s' % jpeg_thumbnail_full_path )
        logging.info('   - snapshot full path %s' % jpeg_full_path )

        if not self.imagePath.endswith('/'):
            self.imagePath += '/'
        
        self.wait(self.adscdev)
        self.adscdev.write_attribute('imagePath', self.imagePath)
        self.adscdev.write_attribute('fileName',  os.path.basename(self.fileName))
       
    @task
    def prepare_oscillation(self, start, osc_range, exptime, npass):
        logging.info("<SOLEIL MultiCollect> prepare_acquisition")
        if self.ready:
           head = self.prepareHeader()
           self.adscdev.SetHeaderParameters( head )
           #self.limaadscdev.exposureTime = (exptime + 0.6) * 1e3
           #if self.limaadscdev.exposureTime > 2500:
               #logging.info("<SOLEIL MultiCollect> prepare_acquisition setting timeout to %s " % (self.limaadscdev.exposureTime + 1500))
               #self.limaadscdev.set_timeout_millis(int(self.limaadscdev.exposureTime + 1500))
           self.wait(self.adscdev)

        return (start, start+osc_range)
        
    @task
    def do_oscillation(self, start, end, exptime, npass):
        pass

    @task
    def start_acquisition(self, exptime, npass, first_frame):
        logging.info("<SOLEIL MultiCollect> start_acquisition")
        # Comes from   self.limaadscSnap() in original Martin's thread program
        if not self.ready:
            return
        logging.info("<SOLEIL MultiCollect> start_acquisition limaadscdev timeout %s" % self.limaadscdev.get_timeout_millis())
        self.limaadscdev.Snap()
        time.sleep(0.05)
        #while self.limaadscdev.log[-1].find('yat::DEVICE_SNAP_MSG') == -1:
            #time.sleep(0.05)
            #self.limaadscdev.Snap()
        return
      
    @task
    def write_image(self, last_frame, jpeg_full_path='/tmp/jfp.jpeg', jpeg_thumbnail_full_path='/tmp/jtfp.jpeg'):
        start = time.time()
        logging.info("<SOLEIL MultiCollect> write last image, converting jpegs")
        logging.info("jpeg_full_path %s" % jpeg_full_path)
        logging.info("jpeg_thumbnail_full_path %s" % jpeg_thumbnail_full_path)
        self.lastImage(integer=last_frame, imagePath=self.imagePath, fileName=self.fileName)
        img_full_path = os.path.join(self.imagePath, self.fileName)
        
        logging.info("<SOLEIL MultiCollect> write last image, converting jpegs, time spent %s " % str(time.time() - start))
        
    def analyze_thread(self, filename):
        logging.info.info('Starting Analyze Thread')
        logging.info.info('filename %s ' % filename)
        self.athread = threading.Thread(target=self.analyze_image, args=(filename,))
        self.athread.daemon = True
        self.athread.start()

    def analyze_image(self, filename):
        logging.info.info('Analyzing image %s' % filename)
        while not os.path.exists(filename):
            time.sleep(0.1)
        os.system('ssh p10 "rsync -av %s /ramdisk/"' % img_full_path)
        #os.system('ssh p10 "adxv -sa -jpeg_scale 0.08 %s %s"' % (img_full_path, jpeg_full_path))
        #os.system('ssh p10 "adxv -sa -jpeg_scale 0.016 %s %s"' % (img_full_path, jpeg_thumbnail_full_path))
        os.system('ssh p10 "ola.py -f %s"' % filename)
        
    @task
    def stop_acquisition(self):
        # Comes from   self.limaadscStop() in original Martin's thread program
        if not self.ready:
           return

        k = 0
        while self.limaadscdev.log[-1].find('Acquisition is Stopped.') == -1 and self.limaadscdev.state().name == 'RUNNING' and k < 3:
            try:
                k += 1
                self.limaadscdev.Stop()
                if k > 1:
                    logging.info('Problem executing Stop command on limaadsc. Attempt %d to stop it.' % k)
                time.sleep(0.1)
            except:
                import traceback
                logging.info('Problem executing Stop command on limaadsc. Attempt %d to stop it. Exception %s' % (k, traceback.format_exc()))
        return

    @task
    def reset_detector(self):   
        return

    def lastImage(self, integer=1, imagePath='/927bis/ccd/test/', fileName='test.img'):
        logging.info("<SOLEIL MultiCollect> lastImage, xformstatusfile %s " % self.xformstatusfile)
        line = str(integer) + ' ' + os.path.join(imagePath, fileName)
        try:
            f = open( self.xformstatusfile, 'w')
            f.write('%s\n' % line)
            f.close()
        except IOError:
            import traceback
            logging.info('Problem writing the last image %s' % (traceback.format_exc()))
        try:
            f = open('/927bis/ccd/log/.goimg/goimg.db', 'w')
            f.write('%s' % os.path.join(imagePath, 'process'))
            f.close()
        except IOError:
            import traceback
            logging.info('Problem writing goimg.db %s' % (traceback.format_exc()))
    
    def wait(self, device):
        green_light = False
        k = 0
        while green_light is False:
            try:
                if device.state().name not in ['STANDBY']:
                    logging.info("Device %s wait" % device)
                else:
                    green_light = True
                    return
            except:
                k += 1
                import traceback
                traceback.print_exc()
                logging.info('Problem occured in wait %s, attempt %s ' % (device, k))
                logging.info(traceback.print_exc())
            time.sleep(.1)
        
    def waitReady(self, device):
        while device.state().name in [ 'MOVING', 'RUNNING'] :
            time.sleep(.1)

    def prepareHeader(self):
        '''Should return a nice header. Implemented in PX2MultiCollect.py'''
        return ""

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
        time.sleep(exptime) 
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
      self.execute_command("reset_detector")

SOLEILBeamlineConfig = namedtuple('SOLEILBeamlineConfig', BeamlineConfig._fields+('detector_radius', ))

class SOLEILMultiCollect(AbstractMultiCollect, HardwareObject):
    def __init__(self, name, detector, tunable_bl):
        AbstractMultiCollect.__init__(self)
        HardwareObject.__init__(self, name)
        self._detector = detector
        self._tunable_bl = tunable_bl
        self._centring_status = None

    def stopCollect(self, owner):
        self.stop_acquisition()
        if self.data_collect_task is not None:
            self.data_collect_task.kill(block = False)
            
    def execute_command(self, command_name, *args, **kwargs): 
      wait = kwargs.get("wait", True)
      cmd_obj = self.getCommandObject(command_name)
      return cmd_obj(*args, wait=wait)
          
        
    def init(self):
        self.setControlObjects(diffractometer    = self.getObjectByRole("diffractometer"),
                               sample_changer    = self.getObjectByRole("sample_changer"),
                               lims              = self.getObjectByRole("dbserver"),
                               safety_shutter    = self.getObjectByRole("safety_shutter"),
                               machine_current   = self.getObjectByRole("machine_current"),
                               cryo_stream       = self.getObjectByRole("cryo_stream"),
                               energy            = self.getObjectByRole("energy"),
                               resolution        = self.getObjectByRole("resolution"),
                               detector_distance = self.getObjectByRole("detector_distance"),
                               transmission      = self.getObjectByRole("transmission"),
                               undulators        = self.getObjectByRole("undulators"),
                               flux              = self.getObjectByRole("flux"),
                               detector          = self.getObjectByRole("detector"),
                               beam_info         = self.getObjectByRole("beam_info"))

        #fast_shutter      = self.getObjectByRole("fast_shutter"),
        mxlocalHO = self.getObjectByRole("beamline_configuration")
        bcm_pars = mxlocalHO["BCM_PARS"]
        spec_pars = mxlocalHO["SPEC_PARS"]
        bl_pars = mxlocalHO["BEAMLINE_PARS"]

        try:
          undulators = bcm_pars["undulator"]
        except IndexError:
          undulators = []
        self.setBeamlineConfiguration(directory_prefix = self.getProperty("directory_prefix"),
                                      default_exposure_time = bcm_pars.getProperty("default_exposure_time"),
                                      minimum_exposure_time = bcm_pars.getProperty("minimum_exposure_time"),
                                      detector_fileext = bcm_pars.getProperty("FileSuffix"),
                                      detector_type = bcm_pars["detector"].getProperty("type"),
                                      detector_manufacturer = bcm_pars["detector"].getProperty("manufacturer"),
                                      detector_model = bcm_pars["detector"].getProperty("model"),
                                      detector_px = bcm_pars["detector"].getProperty("px"),
                                      detector_py = bcm_pars["detector"].getProperty("py"),
                                      undulators = undulators,
                                      focusing_optic = bcm_pars.getProperty('focusing_optic'),
                                      monochromator_type = bcm_pars.getProperty('monochromator'),
                                      beam_divergence_vertical = bcm_pars.getProperty('beam_divergence_vertical'),
                                      beam_divergence_horizontal = bcm_pars.getProperty('beam_divergence_horizontal'),     
                                      polarisation = bcm_pars.getProperty('polarisation'),
                                      synchrotron_name = bl_pars.getProperty('synchrotron_name'),
                                      detector_radius = bcm_pars.getProperty('detector_radius'),
                                      input_files_server = self.getProperty("input_files_server"))
                                      
                                      #default_number_of_passes = bcm_pars.getProperty("default_number_of_passes"),
                                      #maximum_radiation_exposure = bcm_pars.getProperty("maximum_radiation_exposure"),
                                      #nominal_beam_intensity = bcm_pars.getProperty("nominal_beam_intensity"),
                                      #minimum_exposure_time = bcm_pars.getProperty("minimum_exposure_time"),
                                      #minimum_phi_speed = bcm_pars.getProperty("minimum_phi_speed"),
                                      #minimum_phi_oscillation = bcm_pars.getProperty("minimum_phi_oscillation"),
                                      #maximum_phi_speed = bcm_pars.getProperty("maximum_phi_speed"),
                                      #detector_mode = spec_pars["detector"].getProperty("binning"),
                                      #detector_radius = bcm_pars.getProperty('detector_radius'),     
                                      #beam_ax = spec_pars["beam"].getProperty("ax"),
                                      #beam_ay = spec_pars["beam"].getProperty("ay"),
                                      #beam_bx = spec_pars["beam"].getProperty("bx"),
                                      #beam_by = spec_pars["beam"].getProperty("by"),
                                      #synchrotron_name = bl_pars.getProperty('synchrotron_name'),     
                                      
                                      #auto_processing_server = self.getProperty("auto_processing_server"),
                                      
  
        self._detector.initDetector( self.adscname, self.limaadscname, self.xformstatusfile )
        self._tunable_bl.bl_control = self.bl_control

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True, ))


    def setBeamlineConfiguration(self, **configuration_parameters):
        self.bl_config = SOLEILBeamlineConfig(**configuration_parameters)

    @task
    def take_crystal_snapshots(self):
        logging.info("<SOLEIL MultiCollect> take_crystal_snapshots")
        self.bl_control.diffractometer.takeSnapshots(wait=True)

    #TODO: remove this hook!!!
    @task
    def data_collection_hook(self, data_collect_parameters):
        # TOFILL    initializeDevices()
        return

    @task
    def data_collection_cleanup(self):
        logging.info("<SOLEIL MultiCollect> data_collection_cleanup - close fast shutter")
        self.mono_turnon()
        return
        #self.close_fast_shutter()

    @task
    def set_transmission(self, transmission_percent):
        logging.info("<SOLEIL MultiCollect> set transmission")
        self.bl_control.transmission.setTransmission(transmission_percent)


    def set_wavelength(self, wavelength):
        logging.info("<SOLEIL MultiCollect> set wavelength")
        return self._tunable_bl.set_wavelength(wavelength)


    def set_energy(self, energy):
        return self._tunable_bl.set_energy(energy)


    @task
    def send_resolution(self, new_resolution):
        logging.info("<SOLEIL MultiCollect> send resolution to %s" % new_resolution)
        logging.getLogger("user_level_log").info("Setting resolution -- moving the detector.")
        self.bl_control.resolution.move(new_resolution)
       
    @task
    def verify_resolution(self):
        logging.info("<SOLEIL MultiCollect verify resolution> motor stateValue is %s" % self.bl_control.resolution.motorIsMoving())
        while self.bl_control.resolution.motorIsMoving():
            logging.info("<SOLEIL MultiCollect verify resolution> motor stateValue is %s" % self.bl_control.resolution.motorIsMoving())
            time.sleep(0.5)
        logging.getLogger("user_level_log").info("Setting resolution -- done.")
        
    @task
    def set_resolution(self, new_resolution):
        logging.info("<SOLEIL MultiCollect> set resolution to %s" % new_resolution)
        logging.getLogger("user_level_log").info("Setting resolution -- moving the detector.")
        self.bl_control.resolution.move(new_resolution)
        logging.info("<SOLEIL MultiCollect set resolution> motor stateValue is %s" % self.bl_control.resolution.motorIsMoving())
        while self.bl_control.resolution.motorIsMoving():
            logging.info("<SOLEIL MultiCollect set resolution> motor stateValue is %s" % self.bl_control.resolution.motorIsMoving())
            time.sleep(0.5)
        logging.getLogger("user_level_log").info("Setting resolution -- done.")

    @task
    def send_detector(self, detector_distance):
        logging.info("<SOLEIL MultiCollect> Moving detector to %s" % detector_distance)
        logging.getLogger("user_level_log").info("Moving the detector -- it may take a few seconds.")
        self.bl_control.detector_distance.move(detector_distance)
        
    @task
    def verify_detector_distance(self):
        logging.info("<SOLEIL MultiCollect> verify detector distance")
        while self.bl_control.detector_distance.motorIsMoving():
            time.sleep(0.5)
        logging.getLogger("user_level_log").info("Moving the detector -- done.")

    @task
    def move_detector(self, detector_distance):
        logging.info("<SOLEIL MultiCollect> move detector to %s" % detector_distance)
        logging.getLogger("user_level_log").info("Moving the detector -- it may take a few seconds.")
        self.bl_control.detector_distance.move(detector_distance)
        while self.bl_control.detector_distance.motorIsMoving():
            time.sleep(0.5)
        logging.getLogger("user_level_log").info("Moving the detector -- done.")


    @task
    def close_fast_shutter(self):
        logging.info("<SOLEIL MultiCollect> close fast shutter ")
        self.bl_control.fast_shutter.closeShutter()
        t0 = time.time()
        while self.bl_control.fast_shutter.getShutterState() != 'closed':
            time.sleep(0.1)
            if (time.time() - t0) > 4:
                logging.getLogger("HWR").error("Timeout on closing fast shutter")
                break

    @task
    def open_fast_shutter(self):
        logging.info("<SOLEIL MultiCollect> open fast shutter ")
        self.bl_control.fast_shutter.openShutter()
        t0 = time.time()
        while self.bl_control.fast_shutter.getShutterState() == 'closed':
            time.sleep(0.1)
            if (time.time() - t0) > 4:
                logging.getLogger("HWR").error("Timeout on opening fast shutter")
                break

        
    @task
    def move_motors(self, motor_position_dict):
        logging.info("<SOLEIL MultiCollect> move_motors ")
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
        logging.info("<SOLEIL MultiCollect> VERIFY - open safety shutter" )
        if self.test_mode == 1:
            logging.info("<SOLEIL MultiCollect> simulation mode -- leaving safety shutter as it was" )
            return

        self.bl_control.safety_shutter.openShutter()

        t0 = time.time()
        while self.bl_control.safety_shutter.getShutterState() == 'closed':
            time.sleep(0.1)
            if (time.time() - t0) > 8:
                logging.getLogger("user_level_log").error("Cannot open safety shutter. Please check before restarting data collection")
                break


    @task
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

    @task
    def prepare_intensity_monitors(self):
        logging.info("<SOLEIL MultiCollect> TODO - prepare intensity monitors " )
        #self.execute_command("adjust_gains")

    @task
    def prepare_wedges_to_collect(self, start, nframes, osc_range, reference_interval, inverse_beam, overlap):
        return AbstractMultiCollect.prepare_wedges_to_collect(self, start, nframes, osc_range, reference_interval, overlap)

    @task
    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment="", lima_overhead=0):
        # Program scan and other values in md2 for all the oscillations
        # TOFILL self.monoOff()

        logging.info("<SOLEIL MultiCollect> preparing acquisition " )
        self.diffr_wait_ready(timeout=3.0)
        while self.bl_control.diffractometer.getState() in [ 'MOVING', 'RUNNING' ]:
          time.sleep(0.1)
        
        #self.bl_control.diffractometer.goniometerReady( osc_range, npass, exptime)
        self.bl_control.diffractometer.sendGonioToCollect(osc_range, npass, exptime)
        
        return self._detector.prepare_acquisition(take_dark, start, osc_range, exptime, npass, number_of_images, comment, lima_overhead)

    def finalize_acquisition(self):
        # TOFILL self.monoOn()
        pass

    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
        return self._detector.set_detector_filenames(frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path)

    @task
    def prepare_oscillation(self, start, osc_range, exptime, npass):
        # Program things for one wedge
        #while self.bl_control.diffractometer.getState() in [ 'MOVING', 'RUNNING' ]:
          #time.sleep(0.1)
        self.bl_control.diffractometer.wait()
        self.bl_control.diffractometer.setScanStartAngle(start)
        self.bl_control.diffractometer.phiMotor.move(start - 0.1)
        self.bl_control.diffractometer.wait()
        
        return self._detector.prepare_oscillation(start, osc_range, exptime, npass)
    
    @task
    def diffr_wait_ready(self, timeout=None):
        logging.info("<SOLEIL MultiCollect> diffr_wait_ready " )
        wtime = time.time()
        while True:
            diffstate = self.bl_control.diffractometer.getState()
            if diffstate in [ 'MOVING', 'RUNNING' ]:
                logging.info("<SOLEIL MultiCollect> diffr_wait_ready diff state in [ 'MOVING', 'RUNNING' ] " )
                continue
            else:
                logging.info("<SOLEIL MultiCollect> diffr_wait_ready diff state not in [ 'MOVING', 'RUNNING' ] " )
                break
            if (timeout is not None) and (time.time() - wtime) > timeout:
                logging.warning("SOLEILCollect - diffractometer ended wait due to timeout " )
            time.time(0.02)

    @task
    def do_oscillation(self, start, end, exptime, npass):
        self.bl_control.diffractometer.startScan()
        #while self.bl_control.diffractometer.getMotorState('Omega') in [ 'MOVING', 'RUNNING' ]:
            #time.sleep(0.1)
        return 
    
    def start_acquisition(self, exptime, npass, first_frame):
        return self._detector.start_acquisition(exptime, npass, first_frame)
      
    def write_image(self, last_frame, jpeg_full_path='/tmp/jfp.jpeg', jpeg_thumbnail_full_path='/tmp/jtfp.jpeg'):
        return self._detector.write_image(last_frame, jpeg_full_path=jpeg_full_path, jpeg_thumbnail_full_path=jpeg_thumbnail_full_path)

    def stop_acquisition(self):
        return self._detector.stop_acquisition()
        
    def reset_detector(self):
        return self._detector.reset_detector()
        
    def get_wavelength(self):
        logging.info("<SOLEIL MultiCollect> get wavelength " )
        return self._tunable_bl.get_wavelength()

    def get_detector_distance(self):
        logging.info("<SOLEIL MultiCollect> get detector distance " )
        return self.bl_control.detector_distance.getPosition()
       
    def get_resolution(self):
        return self.bl_control.resolution.getPosition()

    def get_transmission(self):
        logging.info("<SOLEIL MultiCollect> TODO - get transmission " )
        return
        #return self.bl_control.transmission.getAttFactor()


    def get_undulators_gaps(self):
        logging.info("<SOLEIL MultiCollect> TODO - get undulators gaps " )
        und_gaps = [None]*3
        return und_gaps
        i = 0
        try:
            for undulator_cfg in self.bl_config.undulators:
                und_gaps[i]=self.bl_control.undulators.getUndulatorGap(undulator_cfg.getProperty("type"))
                i+=1
        except:
            logging.getLogger("HWR").exception("Could not get undulator gaps")
        
        return und_gaps


    def get_resolution_at_corner(self):

        logging.info("<PX1 MultiCollect> get resolution at corner" )

        radius = self.bl_config.detector_radius  / 1000.0 # meters
        detdist =  self.get_detector_distance() / 1000.0 # meters
        wavelength = self.get_wavelength() # amstrongs

        angle = math.atan( math.sqrt(2)*radius/detdist)
        resatcorner = wavelength / (2*math.sin(0.5*angle))
        return resatcorner


    def get_beam_size(self):
        logging.info("<SOLEIL MultiCollect> TODO - get beam size " )
        #return (0.010, 0.005) #valid only for PX2, should either go to PX2MultiCollect or call general method in BeamInfo for instance
        #return (self.execute_command("get_beam_size_x"), self.execute_command("get_beam_size_y"))
        return (0.010, 0.005)

    def get_horizontal_beam_size(self):
        return self.get_beam_size()[0]
    
    def get_vertical_beam_size(self):
        return self.get_beam_size()[-1]
        
    def get_beam_size_x(self):
        return self.get_beam_size()[0]

    def get_beam_size_y(self):
        return self.get_beam_size()[-1]

    def get_slit_gaps(self):
        logging.info("<SOLEIL MultiCollect> TODO - get slit gaps" )
        return [-999,-999]

    def get_beam_centre(self):
        logging.info("<PX2 MultiCollect> TODO - get beam centre" )
        return [-99,-99]

    def get_beam_shape(self):
        logging.info("<SOLEIL MultiCollect> TODO - get beam shape" )
        return "rectangular"
        #return self.execute_command("get_beam_shape")
    
    def get_measured_intensity(self):
      logging.info("<SOLEIL MultiCollect> TODO - get measured intensity " )
      return 0
      try:
        val = self.getChannelObject("image_intensity").getValue()
        return float(val)
      except:
        return 0

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
        return True
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
        logging.info("<SOLEIL MultiCollect> get archive directory")
        ad = directory.replace('RAW_DATA', 'ARCHIVE')
        try:
            if not os.path.exists(ad):
                os.makedirs(ad)
        except:
            import traceback
            logging.info('problem creating archive %s ' % traceback.format_exc())
        return ad
 
        res = None
       
        dir_path_list = directory.split(os.path.sep)
        try:
          suffix_path=os.path.join(*dir_path_list[4:])
        except TypeError:
          return None
        else:
          if 'inhouse' in directory:
            archive_dir = os.path.join('/927bis/ccd/pyarch/', dir_path_list[2], suffix_path)
          else:
            archive_dir = os.path.join('/927bis/ccd/pyarch/', dir_path_list[4], dir_path_list[3], *dir_path_list[5:])
          if archive_dir[-1] != os.path.sep:
            archive_dir += os.path.sep
            
          return archive_dir

    def prepare_input_files(self, files_directory, prefix, run_number, process_directory):
        return "/tmp", "/tmp"
        
    def write_input_files(self, collection_id):
        pass

    def get_cryo_temperature(self):
        logging.info("<SOLEIL MultiCollect> TODO - get cryo temperature")
        pass

    def get_machine_current(self):
        if self.bl_control.machine_current is not None:
            return self.bl_control.machine_current.getCurrent()
        else:
            return -1

    def get_machine_message(self):
        logging.info("<SOLEIL MultiCollect> getting machine message" )
        return 'Dummy message'
        if  self.bl_control.machine_current is not None:
            return 'Dummy message'
            #return self.bl_control.machine_current.getMessage()
        else:
            return 'Not implemented yet'

    def get_machine_fill_mode(self):
        logging.info("<PX1 MultiCollect> getting machine fill mode" )
        logging.info( self.bl_control.machine_current.getFillMode() )

        if self.bl_control.machine_current is not None:
            return self.bl_control.machine_current.getFillMode()
        else:
            'Not implemented yet'

