
import gevent

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
        detector_tower_dev = DeviceProxy(self.get_property("detector_tower_device"))
        

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
    
    def get_detector_distance(self):
        det_tower_distance =  self.detector_tower_dev.read_attribute("DetectorDistance").value
        self.log.debug("EIGER - current detector distance is : %s" % current_det_tower_distance) 
        return det_tower_distance


    def prepare_common(self, exptime, filepath):
        if not self.inited:
            self.init_acquisition()

        self.eiger_dev.write_attribute("CountTime", float(exptime))
        self.eiger_dev.write_attribute("FrameTime", float(exptime))
        self.eiger_dev.write_attribute("TriggerStartDelay", 0.003)

        if filepath.startswith("/gpfs"):
            filepath = filepath[len("/gpfs"):]

        self.writer_dev.write_attribute("NamePattern", filepath)

        #==== Setting the beam center ======================
        #Beam center is depending on the detector distance as for the CrystalControl. 
        #Emulate of the same hardcoded config parameters as before.
        
        #Beam center params after calibration in October 2022 from CC
        #self.dataCollector.setParameter("beamX", self.beamOriginX + 63.5 * (self.ui.doubleSpinBoxDetectorDistance.value() - 160) / 1000.0)
        #self.dataCollector.setParameter("beamY", self.beamOriginY - 14.2 * (self.ui.doubleSpinBoxDetectorDistance.value() - 160) / 1000.0)

        current_det_tower_distance =  self.get_detector_distance()
        corrected_originx = self.originx + 63.5 * (current_det_tower_distance - 160) / 1000.0
        corrected_originy = self.originy - 14.2 * (current_det_tower_distance - 160) / 1000.0

        self.eiger_dev.write_attribute("BeamCenterX", float(corrected_originx))
        self.eiger_dev.write_attribute("BeamCenterY", float(corrected_originy))
        #=================================================

        #============ Other params from CC ===================
         #Eiger
            # if(self.petraThread.currentMonoEnergy > (self.eigerThread.photonEnergy + self.DETECTOR_ENERGY_TOLERANCE) or \
            #     self.petraThread.currentMonoEnergy < (self.eigerThread.photonEnergy - self.DETECTOR_ENERGY_TOLERANCE)):
            #     if(str(self.eigerThread.proxyEiger.state()) == "ON"):
            #         print("Setting Eiger threshold")
            #         self.emit(SIGNAL("logSignal(PyQt_PyObject)"),"Setting Eiger energy threshold.")
            #         if self.petraThread.currentMonoEnergy > 5500:
            #             self.eigerThread.setPhotonEnergy(self.petraThread.currentMonoEnergy)
            #         else:
            #             self.eigerThread.setPhotonEnergy(5500)
            #         time.sleep(1.5)
            #         conditions = False
            #         self.conditionsList["DetectorThresholdSet"] = False
            # elif (str(self.eigerThread.proxyEiger.state()) == "ON"):
            #     self.conditionsList["DetectorThresholdSet"] = True
            #     self.emit(SIGNAL("waitConditionsUpdate()"))
            # elif (not (str(self.eigerThread.proxyEiger.state()) == "ON")):
            #     conditions = False
            #     self.conditionsList["DetectorThresholdSet"] = False
            #     self.emit(SIGNAL("waitConditionsUpdate()"))
        #=====================================================


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

        #metadata = {}
        #metadata["start_angle"] = start
        #metadata["angle_increment"] = osc_range
        #metadata["beam_x"] = beam_x
        #metadata["beam_y"] = beam_y
        #metadata["detector_distance"] = detdist

        #self.set_medatata(metadata)

    def set_metadata(self, metadata):
        pass

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

