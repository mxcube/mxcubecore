# JN, 20150629, mxcube-qt4 version 
from HardwareRepository.BaseHardwareObjects import HardwareObject
from AbstractMultiCollect import *
from gevent.event import AsyncResult
import logging
import time
import os
import httplib
import urllib
import math

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
    def __init__(self, detector_class=None):
        self._detector = detector_class() if detector_class else None
    
    def init(self, config, collect_obj): 
        self.collect_obj = collect_obj
        if self._detector:
          self._detector.addChannel = self.addChannel
          self._detector.addCommand = self.addCommand
          self._detector.getChannelObject = self.getChannelObject
          self._detector.getCommandObject = self.getCommandObject
          self._detector.init(config, collect_obj)
    
    @task
    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment="", energy=None):
        if osc_range < 1E-4:
            still = True
        else:
            still = False
        
        if self._detector:
            self._detector.prepare_acquisition(take_dark, start, osc_range, exptime, npass, number_of_images, comment, energy, still)
        else:
            self.getChannelObject("take_dark").setValue(take_dark)
            self.execute_command("prepare_acquisition", take_dark, start, osc_range, exptime, npass, comment)

    @task
    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
      if self._detector:
          self._detector.set_detector_filenames(frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path)
      else:
          self.getCommandObject("prepare_acquisition").executeCommand('setMxCollectPars("current_phi", %f)' % start)
          self.getCommandObject("prepare_acquisition").executeCommand('setMxCurrentFilename("%s")' % filename)
          self.getCommandObject("prepare_acquisition").executeCommand('setMxThumbnailPaths("%s","%s")' % (jpeg_full_path, jpeg_thumbnail_full_path))
          self.getCommandObject("prepare_acquisition").executeCommand("ccdfile(COLLECT_SEQ, %d)" % frame_number, wait=True)

    @task
    def prepare_oscillation(self, start, osc_range, exptime, npass):
        if osc_range < 1E-4:
            # still image
            pass
        else:
            self.collect_obj.do_prepare_oscillation(start, start+osc_range, exptime, npass)
        return (start, start+osc_range)

    @task
    def start_acquisition(self, exptime, npass, first_frame):
        if self._detector:
            self._detector.start_acquisition(exptime, npass, first_frame)
        else:
            self.execute_command("start_acquisition")

    @task
    def no_oscillation(self, exptime):
        self.collect_obj.open_fast_shutter()
        time.sleep(exptime)
        self.collect_obj.close_fast_shutter()
 
    @task
    def do_oscillation(self, start, end, exptime, npass):
      still = math.fabs(end-start) < 1E-4
      if still:
          self.no_oscillation(exptime)
      else:
          self.collect_obj.oscil(start, end, exptime, npass)
   
    @task
    def write_image(self, last_frame):
        if self._detector:
            self._detector.write_image(last_frame)
        else:
            if last_frame:
                self.execute_command("flush_detector")
            else:
                self.execute_command("write_image")
    
    def stop_acquisition(self):
        # detector readout
        if self._detector:
            self._detector.stop_acquisition()
        else:
            self.execute_command("detector_readout")

    @task
    def reset_detector(self):     
        if self._detector:
            self._detector.stop()
        else:
            self.getCommandObject("reset_detector").abort()
            self.execute_command("reset_detector")
 

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
        else:
            self.execute_command("prepare_acquisition", take_dark, start, osc_range, exptime, npass, comment)
        
    @task
    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
      if self.shutterless and not self.new_acquisition:
          return
 
      if self._detector:
          self._detector.set_detector_filenames(frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path)
      else:
          self.getCommandObject("prepare_acquisition").executeCommand('setMxCollectPars("current_phi", %f)' % start)
          self.getCommandObject("prepare_acquisition").executeCommand('setMxCurrentFilename("%s")' % filename)
          self.getCommandObject("prepare_acquisition").executeCommand("ccdfile(COLLECT_SEQ, %d)" % frame_number, wait=True)

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
      if not first_frame and self.shutterless:
        pass 
      else:
        if self._detector:
            self._detector.start_acquisition()
        else:
            self.execute_command("start_acquisition")

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
          else:
              try:
                 self.oscillation_task.get(block=False)
              except gevent.Timeout:
                 pass #no result yet, it is normal
              except:
                 # an exception occured in task! Pilatus server died?
                 raise
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
      else:
          self.getCommandObject("reset_detector").abort()    
          self.execute_command("reset_detector")


class MAXLABMultiCollect(AbstractMultiCollect, HardwareObject):
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
                               flux = self.getObjectByRole("flux"),
                               detector = self.getObjectByRole("detector"),
                               beam_info = self.getObjectByRole("beam_info"))

        try:
          undulators = self["undulator"]
        except IndexError:
          undulators = []

         
        self.setBeamlineConfiguration(synchrotron_name = self.getProperty("synchrotron_name"),
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
                                      beam_divergence_vertical = self.bl_control.beam_info.getProperty('beam_divergence_vertical'),
                                      beam_divergence_horizontal = self.bl_control.beam_info.getProperty('beam_divergence_horizontal'),     
                                      polarisation = self.getProperty('polarisation'),
                                      input_files_server = self.getProperty("input_files_server"))
  
        self._detector.addCommand = self.addCommand
        self._detector.addChannel = self.addChannel
        self._detector.getCommandObject = self.getCommandObject
        self._detector.getChannelObject = self.getChannelObject
        self._detector.execute_command = self.execute_command
        self._detector.init(self.bl_control.detector, self)
        self._tunable_bl.bl_control = self.bl_control

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True, ))

    @task
    def take_crystal_snapshots(self, number_of_snapshots):
        self.bl_control.diffractometer.takeSnapshots(number_of_snapshots, wait=True)

    #TODO: remove this hook!!!
    @task
    def data_collection_hook(self, data_collect_parameters):
        return
 
    def do_prepare_oscillation(self, start, end, exptime, npass):
        return self.execute_command("prepare_oscillation", start, end, exptime, npass)
    
    @task
    def oscil(self, start, end, exptime, npass):
      if math.fabs(end-start) < 1E-4:
        self.open_fast_shutter()
        time.sleep(exptime)
        self.close_fast_shutter()
      else:
        return self.execute_command("do_oscillation", start, end, exptime, npass)
    
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
        self.close_fast_shutter()


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
        return
        #self.bl_control.safety_shutter.openShutter()
        #while self.bl_control.safety_shutter.getShutterState() == 'closed':
        #  time.sleep(0.1)


    def safety_shutter_opened(self):
        return self.bl_control.safety_shutter.getShutterState() == "opened"


    @task
    def close_safety_shutter(self):
        return
        #self.bl_control.safety_shutter.closeShutter()
        #while self.bl_control.safety_shutter.getShutterState() == 'opened':
        #  time.sleep(0.1)


    @task
    def prepare_intensity_monitors(self):
        self.execute_command("adjust_gains")


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
        

    def prepare_input_files(self, files_directory, prefix, run_number, process_directory):
        i = 1
        logging.info("Creating XDS (MAXLAB) processing input file directories")

        self.xds_template    = "/home/blissadm/mxCuBE-Qt4/config/dp_file_templates/xdstemplate_maxlab.inp"
        self.mosflm_template = "/home/blissadm/mxCuBE-Qt4/config/dp_file_templates/mosflmtemplate_maxlab.inp"

        try:
           self.xds_template_buf    = open(self.xds_template).read()
           self.mosflm_template_buf = open(self.mosflm_template).read()
           self.write_files = True
        except:
           print "Cannot find template for xds and mosflm input files "
           self.write_files = False 

        while True:
          xds_input_file_dirname = "xds_%s_run%s_%d" % (prefix, run_number, i)
          xds_directory = os.path.join(process_directory, xds_input_file_dirname)

          if not os.path.exists(xds_directory):
            break

          i+=1

        mosflm_input_file_dirname = "mosflm_%s_run%s_%d" % (prefix, run_number, i)
        mosflm_directory = os.path.join(process_directory, mosflm_input_file_dirname)

        self.raw_data_input_file_dir = os.path.join(files_directory, "process", xds_input_file_dirname)
        self.mosflm_raw_data_input_file_dir = os.path.join(files_directory, "process", mosflm_input_file_dirname)

        for dir in (self.raw_data_input_file_dir, xds_directory):
          self.create_directories(dir)
          logging.info("Creating XDS processing input file directory: %s", dir)
          os.chmod(dir, 0777)
        for dir in (self.mosflm_raw_data_input_file_dir, mosflm_directory):
          self.create_directories(dir)
          logging.info("Creating MOSFLM processing input file directory: %s", dir)
          os.chmod(dir, 0777)

 
        try: 
          try: 
              os.symlink(files_directory, os.path.join(process_directory, "links"))
          except os.error, e:
              if e.errno != errno.EEXIST:
                  raise
        except:
            logging.exception("Could not create processing file directory")

        return xds_directory, mosflm_directory

    @task
    def write_input_files(self, collection_id):

        # assumes self.xds_directory and self.mosflm_directory are valid

        #print "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"
        #print "WRITING INPUT FILES"
        #print "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"

        dp_pars   = self.collect_pars_dp

        print "\nDATA COLLECT PARS"
        print "-------------------------------------------"
        pprint.pprint(dp_pars)
        print "-------------------------------------------"

        # get info from HWR server (is this updated when file is changed?)
        # GET some info from beamline control and beamline config objects
        mxlocalHO = self.getObjectByRole("beamline_configuration")
        self.detm = self.getObjectByRole("detector_distance")

        bcm_pars  = mxlocalHO["BCM_PARS"]
        spec_pars = mxlocalHO["SPEC_PARS"]

        # prepare / calculate some values (configured in mxlocal.xml - updated with lab6calibrate script)

        AXBeam = spec_pars["beam"].getProperty("ax")
        AYBeam = spec_pars["beam"].getProperty("ay")
        BXBeam = spec_pars["beam"].getProperty("bx")
        BYBeam = spec_pars["beam"].getProperty("by")

        # obtained from detm motor hardware object configured in mxcollect.xml
        detdistpos = self.detm.getPosition()

        XBeam = (AXBeam * detdistpos) + BXBeam
        YBeam = (AYBeam * detdistpos) + BYBeam

        # obtained from energy hardware object configured in mxcollect.xml
        wavelength = self.bl_control.energy.getCurrentWavelength()

# FROM SPEC - FOR XDS - DP_INPUTS (pixel size) are set in setup file with dp_files_setup macro
#  bcmpars["beam"]["x"] and "y" are those just calculated above XBeam, YBeam
#    _DP_INPUTS["orgx"] = bcmpars["beam"]["x"]/DP_INPUTS["pixel_size_x"]
#    _DP_INPUTS["orgy"] = bcmpars["beam"]["y"]/DP_INPUTS["pixel_size_y"]
#
        pixsize_x =  bcm_pars.getProperty("pixel_size_x")
        pixsize_y =  bcm_pars.getProperty("pixel_size_y")

        orgx = XBeam / pixsize_x
        orgy = YBeam / pixsize_y
       
        # XDS content goes here
        finfo    = dp_pars["fileinfo"]
        osc_seq  = dp_pars["oscillation_sequence"][0]

        xds_file_template    = "%(prefix)s_%(run_number)s_???.%(suffix)s" % finfo
        mosflm_file_template = "%(prefix)s_%(run_number)s_###.%(suffix)s" % finfo

        for input_file_dir, file_prefix in ((self.raw_data_input_file_dir, "../.."), (self.xds_directory, "../links")): 
          xds_input_file = os.path.join(input_file_dir, "XDS.INP")

          xds_file = open(xds_input_file, "w")

          # IMAGE NUMBERING FOR XDS
          startImageNumber     = osc_seq["start_image_number"]
          endImageNumber       = osc_seq["start_image_number"] + osc_seq["number_of_images"] - 1

          startImageNumber_beg = osc_seq["start_image_number"]
          endImageNumber_beg   = osc_seq["start_image_number"] + 4
          if endImageNumber_beg > endImageNumber:
             endImageNumber_beg = endImageNumber

          startImageNumber_end = osc_seq["start_image_number"] + osc_seq["number_of_images"] - 5
          if startImageNumber_end < startImageNumber:
             startImageNumber_end = startImageNumber 

          endImageNumber_end   = osc_seq["start_image_number"] + osc_seq["number_of_images"] - 1

          startImageNumber_bkg = osc_seq["start_image_number"]
          endImageNumber_bkg   = osc_seq["start_image_number"] + 9
          if endImageNumber_bkg > endImageNumber: 
             endImageNumber_bkg = endImageNumber

          xdswait_exposure_time = int(osc_seq["exposure_time"]) + 20

          try:
              valdict = {
                  "user_comment":                 self.collect_pars_dp["comment"],
                  "I911-collection_start_time":   time.strftime("%Y-%m-%d %H:%M:%S"), # just a hack for now (2013-09-09) should be taken from the lims system in AbstractMultiCollect.py, so we are certain it's the same
                  "startImageNumber":             startImageNumber,
                  "endImageNumber":               endImageNumber,
                  "startImageNumber_bkg":         startImageNumber_bkg,
                  "endImageNumber_bkg":           endImageNumber_bkg,
                  "startImageNumber_beg":         startImageNumber_beg,
                  "endImageNumber_beg":           endImageNumber_beg,
                  "startImageNumber_end":         startImageNumber_end,
                  "endImageNumber_end":           endImageNumber_end,
                  "axisRange":                    osc_seq["range"],
                  "axisStart":                    osc_seq["start"],
                  "exposure_time":                osc_seq["exposure_time"],
                  "xdswait_exposure_time":        xdswait_exposure_time,
                  "wavelength":                   wavelength,
                  "imageDirectory":               finfo["directory"],
                  "fileTemplate":                 xds_file_template,
                  "detectorDistance":             detdistpos,
                  "xbeam_px":                     orgy,    
                  "ybeam_px":                     orgx,    
                  "detectorPixelSizeHorizontal":  pixsize_y,    
                  "detectorPixelSizeVertical":    pixsize_x,   
             } 
          except:
             import traceback
             traceback.print_exc()

          try:
             xds_buf = self.xds_template_buf % valdict
          except:
             import traceback
             traceback.print_exc()

          xds_file.write( xds_buf )
          xds_file.close()

          os.chmod(xds_input_file, 0666)

        for input_file_dir, file_prefix in ((self.mosflm_raw_data_input_file_dir, "../.."), (self.mosflm_directory, "../links")): 
          mosflm_input_file = os.path.join(input_file_dir, "mosflm.inp")

          mosflm_file = open(mosflm_input_file, "w")

          # MOSFLM content goes here
          valdict = {
                  "user_comment":      self.collect_pars_dp["comment"],
                  "wavelength":        wavelength,
                  "detectorDistance":  detdistpos,
                  "xbeam":             YBeam,   
                  "ybeam":             XBeam,   
                  "imageDirectory":    finfo["directory"],
                  "fileTemplate":      mosflm_file_template,
                  "imageSuffix":       finfo["suffix"],
                  "startImageNumber":  osc_seq["start_image_number"],
                  "axisStart":         osc_seq["start"],
                  "axisEnd":           osc_seq["start"] + osc_seq["range"] * osc_seq["number_of_images"] - osc_seq["overlap"] * (osc_seq["number_of_images"] - 1),
          } 


          try:
             mosflm_buf  = self.mosflm_template_buf % valdict
          except:
             import traceback
             traceback.print_exc()

          mosflm_file.write( mosflm_buf )
          mosflm_file.close()
          os.chmod(mosflm_input_file, 0666)

        # write input file for STAC, JN,20140709
        stac_template = "/home/blissadm/mxCuBE-Qt4/config/dp_file_templates/stactemplate_maxlab.inp"
        try:
          stac_template_buf  =open(stac_template).read()
        except:
          print "Cannot find template for stac input files "
          return
       
        omega=self.bl_control.diffractometer.phiMotor.getPosition()
        kappa=self.bl_control.diffractometer.kappaMotor.getPosition()
        phi=self.bl_control.diffractometer.kappaPhiMotor.getPosition()
        sampx=self.bl_control.diffractometer.sampleXMotor.getPosition()
        sampy=self.bl_control.diffractometer.sampleYMotor.getPosition()
        phiy=self.bl_control.diffractometer.phiyMotor.getPosition()
       
         
        for stac_om_input_file_name, stac_om_dir in (("mosflm.descr", self.mosflm_directory), 
                                                     ("xds.descr", self.xds_directory),
                                                     ("mosflm.descr", self.mosflm_raw_data_input_file_dir),
                                                     ("xds.descr", self.raw_data_input_file_dir)):
          stac_om_input_file = os.path.join(stac_om_dir, stac_om_input_file_name)
          stac_om_file = open(stac_om_input_file, "w")

          if stac_om_input_file_name.startswith("xds"):
            om_type="xds"
            if stac_om_dir == self.raw_data_input_file_dir:
              om_filename=os.path.join(stac_om_dir, "CORRECT.LP")
            else:
              om_filename=os.path.join(stac_om_dir, "xds_fastproc", "CORRECT.LP")
          else:
            om_type="mosflm"
            om_filename=os.path.join(stac_om_dir, "bestfile.par")

          valdict = {
                  "omfilename":       om_filename,
                  "omtype":           om_type,
                  "omega":            omega,
                  "kappa":            kappa,
                  "sampx":            sampx,
                  "sampy":            sampy,
                  "phiy":             phiy,
                  "phi":              phi,
               
          }
          try:
             stac_buf  = stac_template_buf % valdict
          except:
             import traceback
             traceback.print_exc()

          stac_om_file.write(stac_buf)
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
        und_gaps = [None]*3
        #i = 0
        #for undulator_cfg in self.bl_config.undulators:
        #    und_gaps[i]=self.bl_control.undulators.getUndulatorGap(undulator_cfg.getProperty("type"))
        #    i+=1
        return und_gaps

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
        return ""
        if  self.bl_control.machine_current:
            return self.bl_control.machine_current.getMessage()
        else:
            return ''


    def get_machine_fill_mode(self):
        return ""

        if self.bl_control.machine_current:
            return self.bl_control.machine_current.getFillMode()
        else:
            ''

    def get_cryo_temperature(self):
      try:
        val = self.bl_control.cryo_stream.getTemperature()
        return float(val)
      except:
        return 0

    def getCurrentEnergy(self):
      return self._tunable_bl.getCurrentEnergy()


    def get_beam_centre(self):
       return (self.execute_command("get_beam_centre_y"), self.execute_command("get_beam_centre_x"))

    
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
        return 0
#        return self.bl_control.flux.getCurrentFlux()

    @task
    def generate_image_jpeg(self, filename, jpeg_path, jpeg_thumbnail_path):
        pass

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


    def set_helical(self, helical_on):
        self.getChannelObject("helical").setValue(1 if helical_on else 0)


    def set_helical_pos(self, helical_oscil_pos):
        self.getChannelObject('helical_pos').setValue(helical_oscil_pos)


    def get_archive_directory(self, directory):
        res = None

        dir_path_list = directory.split(os.path.sep)
        try:
          suffix_path=os.path.join(*dir_path_list[4:])
        except TypeError:
          return None
        else:
          if 'inhouse' in directory:
            #albnar 20/08/2014: Try to have the same behavior of the visitors
            #archive_dir = os.path.join('/data/ispyb/', dir_path_list[3], suffix_path)
            archive_dir = os.path.join('/data/ispyb/', dir_path_list[4], *dir_path_list[5:])
          else:
            archive_dir = os.path.join('/data/ispyb/', dir_path_list[4], *dir_path_list[5:])
          if archive_dir[-1] != os.path.sep:
            archive_dir += os.path.sep

          return archive_dir


    # JN, 20140904, save snapshot in the RAW_DATA folder in the end of the data collection 
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
        image_file_template = self.image_file_format % file_parameters
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
                if current_diffractometer_position[motor] is not None:
                    positions_str += "%s=%f " % (motor, current_diffractometer_position[motor])

        # this is for the LIMS
        positions_str += " ".join([motor+("=%f" % pos) for motor, pos in motors_to_move_before_collect.iteritems()])
        data_collect_parameters['actualCenteringPosition'] = positions_str
        ###
        self.move_motors(motors_to_move_before_collect)

        # take snapshots, then assign centring status (which contains images) to centring_info variable
        self._take_crystal_snapshots(data_collect_parameters.get("take_snapshots", False))
        centring_info = self.bl_control.diffractometer.getCentringStatus()
        # move *again* motors, since taking snapshots may change positions
        self.move_motors(motors_to_move_before_collect)

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
                else:
                  f.close()

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

        file_parameters = data_collect_parameters["fileinfo"] 
        snapshot_directory = self.get_archive_directory(file_parameters["directory"])
        snapshot_filename = "%s_%s_*.snapshot.jpeg" % (file_parameters["prefix"],
                                                                file_parameters["run_number"]) 
        full_snapshot = os.path.join(snapshot_directory,
                                             snapshot_filename)
        os.system("cp %s %s" % (full_snapshot,file_parameters["directory"]))
        #logging.info("cp %s %s" % (full_snapshot,file_parameters["directory"]))
