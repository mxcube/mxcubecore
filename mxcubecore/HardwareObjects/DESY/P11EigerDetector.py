
import gevent
import time

from mxcubecore.Command.Tango import DeviceProxy
from mxcubecore.HardwareObjects.abstract.AbstractDetector  import (
        AbstractDetector, )

class P11EigerDetector(AbstractDetector):
    def __init__(self, *args):
        AbstractDetector.__init__(self, *args)

    def init(self):
        AbstractDetector.init(self)

        self.eiger_devname = self.get_property("eiger_device")
        self.filewriter_name = self.get_property("filewriter_device")
        self._roi_mode = self.get_property("roi_mode", "disabled")

        self.log.debug("EIGER - device name is : %s" % self.eiger_devname)
        self.log.debug("EIGER - filewriter name is : %s" % self.filewriter_name)
        self.log.debug("EIGER - detector distance is : %s" % self._distance_motor_hwobj)
        self.log.debug("EIGER - shutterless : %s" % self.has_shutterless())

        self.eiger_dev = DeviceProxy(self.eiger_devname)
        self.writer_dev = DeviceProxy(self.filewriter_name)
        
        #Get the detector distance device
        self.detector_tower_dev = DeviceProxy(self.get_property("detector_tower_device"))
        self.dcm_energy_dev = DeviceProxy(self.get_property("dcm_energy_device"))
        

        self.chan_status = self.get_channel_object("_status")
        self.chan_status.connect_signal("update", self.status_changed) 

        self._exposure_time_limits = eval(self.get_property("exposure_time_limits"))
        
        self._beam_centre = eval(self.get_property("beam_centre"))
        self.originx=self._beam_centre[0]
        self.originy=self._beam_centre[1]

        self.log.debug("EIGER - beamcenter: %s" % str(self._beam_centre))  
        self.log.debug("EIGER - originx: %s" % str(self.originx))  
        self.log.debug("EIGER - originy: %s" % str(self.originy))
        

        self.inited = False
        
    def init_acquisition(self):
        #  set parameters like exts, images_per_file, etc...
        # self.roi_mode = "4M"
        # self.roi_mode = "disabled"

        self.set_eiger_enum("TriggerMode", "exts")
        self.set_eiger_enum("RoiMode", self._roi_mode)
        self.set_eiger_enum("Compression", "bslz4")
        self.set_writer_enum("Mode", "enabled")
        self.writer_dev.write_attribute("NImagesPerFile", 1000)
        self.inited = True

    def has_shutterless(self):
        return True

    # def prepare_acquisition(self,
                            # take_dark,
                            # start,
                            # osc_range,
                            # exptime,
                            # npass,
                            # number_of_images,
                            # comment,
                            # mesh,
                            # mesh_nb_lines
   #                          ):

    def get_radius(self, distance=None):
        # a proper calculation should be done here
        # this value comes from crystalControlMaxwell hardcoded value to
        # estimate resolution
        return 311 / 2.0
    
    def get_eiger_detector_distance(self):
        #Get current detector distance from detector tower server
        det_tower_distance =  self.detector_tower_dev.read_attribute("DetectorDistance").value
        self.log.debug("EIGER: DetectorTower distance is : %s" % det_tower_distance) 
        return det_tower_distance
    
    def set_eiger_detector_distance(self):
        #Set detector distance in the Detector server for the header.
        # It does not set the actual detector distance! 

        # in mm from detector tower server
        current_det_tower_distance =  self.get_eiger_detector_distance()
        #in meters for the detector header info
        # self.eiger_dev.write_attribute("DetectorDistance", float(current_det_tower_distance/1000.0))

        self.eiger_dev.write_attribute("DetectorDistance", float(current_det_tower_distance))

    #TODO add if needed
    def get_eiger_beam_center(self):
        return True

    def set_eiger_beam_center(self): 
        #==== Setting the beam center ======================
        #Beam center is depending on the detector distance as for the CrystalControl. 
        #Emulate of the same hardcoded config parameters as before.
        #originx and originy (set in eiger.xml) are the X and Y of the beam mark at the detector distance of 160 mm.
        
        #Beam center params after calibration in October 2022 from CC:
        current_det_tower_distance =  self.get_eiger_detector_distance()
        corrected_originx = self.originx + 63.5 * (current_det_tower_distance - 160) / 1000.0
        corrected_originy = self.originy - 14.2 * (current_det_tower_distance - 160) / 1000.0

        self.eiger_dev.write_attribute("BeamCenterX", float(corrected_originx))
        self.eiger_dev.write_attribute("BeamCenterY", float(corrected_originy))

        self.log.debug("EIGER - current beamcenter X and Y: %f, %f at detector distance %f mm" % (corrected_originx, corrected_originy, current_det_tower_distance))
    
    #TODO add if needed
    def get_eiger_photon_energy(self):
        return True
    
    #FIXME: Add the same conditions as for CC
    def set_eiger_photon_energy(self):
        #Sets photon energy in the detector server for the header   
        current_dcm_energy = float(self.dcm_energy_dev.read_attribute("Position").value)
        
        if current_dcm_energy > 5500:
            self.eiger_dev.write_attribute("PhotonEnergy", float(current_dcm_energy))
        else:
            self.eiger_dev.write_attribute("PhotonEnergy", float(5500))

    def set_eiger_start_angle(self, arg):
        #Sets Detector start angle for the header
        arg = float(arg)
        self.eiger_dev.write_attribute("OmegaStart", arg)

    def set_eiger_angle_increment(self, arg):
        #Sets detector angle increment
        arg = float(arg)
        self.eiger_dev.write_attribute("OmegaIncrement", arg)


    def prepare_common(self, exptime, filepath):
        if not self.inited:
            self.init_acquisition()

        self.eiger_dev.write_attribute("CountTime", float(exptime))
        self.eiger_dev.write_attribute("FrameTime", float(exptime))
        self.eiger_dev.write_attribute("TriggerStartDelay", 0.003)

        if filepath.startswith("/gpfs"):
            filepath = filepath[len("/gpfs"):]

        self.writer_dev.write_attribute("NamePattern", filepath)

        #Sets the metadata for the header
        self.set_metadata()
 
    def prepare_characterisation(self, exptime, number_of_images, angle_inc, filepath):
        self.writer_dev.write_attribute("NImagesPerFile", 1) # To write one image per characterisation.
        self.prepare_common(exptime, filepath)
        self.eiger_dev.write_attribute("Nimages", 1) #Number of images per trigger
        self.log.debug("Eiger. preparing characterization. Number of triggers is: %d" % number_of_images)
        self.eiger_dev.write_attribute("Ntrigger", int(number_of_images))
        
    def prepare_std_collection(self, exptime, number_of_images, filepath):  
        self.prepare_common(exptime, filepath)

        self.eiger_dev.write_attribute("Nimages", int(number_of_images))
        self.eiger_dev.write_attribute("Ntrigger", 1)
        self.writer_dev.write_attribute("NImagesPerFile", 1000) # Default

        self.writer_dev.write_attribute("ImageNrStart", 1) 

        
    def set_metadata(self):
        self.set_eiger_detector_distance() #set detector distance for the header
        self.set_eiger_beam_center() #set detector beam center for the header
        self.set_eiger_photon_energy() #set detector photon energy

    def start_acquisition(self):
        self.eiger_dev.Arm()

    def stop_acquisition(self):
        self.eiger_dev.Abort()
        gevent.sleep(1)
        self.eiger_dev.Disarm()
        self.wait_ready()

    def wait_ready(self, timeout=30):
        with gevent.Timeout(timeout, RuntimeError("timeout waiting detector ready")):
             while self.chan_status.get_value().lower() not in ["ready", "idle"]:
                 gevent.sleep(1)

    def status_changed(self, status):
        self.log.debug("P11EigerDetector - status changed. now is %s" % status)

    def get_beam_position(self, distance=None, wavelength=None):
        return self._beam_centre
    
    # managing enum device server attributes
    def set_eiger_enum(self, attr, value):
        dev = self.eiger_dev
        self.set_attr_enum(dev,attr,value)
    def set_writer_enum(self, attr, value):
        dev = self.writer_dev
        self.set_attr_enum(dev,attr,value)
    def set_attr_enum(self,dev,attr,value):
        values = list(dev.get_attribute_config(attr).enum_labels)

        no = values.index(value)
        if no >= 0:
             print("writing no %s for value %s (%s)" % (no,value, str(values)))
             dev.write_attribute(attr,no)
        else:
            self.log.error("Trying to write invalid value %s for attribute %s" % (value,attr))

    def get_eiger_enum(self, attr):
        dev = self.eiger_dev
        return self.get_attr_enum(dev,attr)

    def get_writer_enum(self,attr):
        dev = self.writer_dev
        return self.get_attr_enum(dev,attr)

    def get_attr_enum(self,dev,attr):
        values = list(dev.get_attribute_config(attr).enum_labels)
        no = dev.read_attribute(attr).value
        return values[no]

