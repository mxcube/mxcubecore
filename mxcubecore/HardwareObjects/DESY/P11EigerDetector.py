
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

        self.chan_status = self.get_channel_object("_status")
        self.chan_status.connect_signal("update", self.status_changed) 

        self._exposure_time_limits = eval(self.get_property("exposure_time_limits"))
        self._beam_centre = eval(self.get_property("beam_centre"))

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

    def prepare_common(self, exptime, filepath):
        if not self.inited:
            self.init_acquisition()

        self.eiger_dev.write_attribute("CountTime", float(exptime))
        self.eiger_dev.write_attribute("FrameTime", float(exptime))
        self.eiger_dev.write_attribute("TriggerStartDelay", 0.003)

        if filepath.startswith("/gpfs"):
            filepath = filepath[len("/gpfs"):]

        self.writer_dev.write_attribute("NamePattern", filepath)

    def prepare_characterisation(self, exptime, number_of_images, angle_inc, filepath):
        #self.writer_dev.write_attribute("NImagesPerFile", 1) # To write one image per characterisation.
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

