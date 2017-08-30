import Microdiff
import gevent
import sample_centring
import time

class MD3UP(Microdiff.Microdiff):
    def __init__(self, *args, **kwargs):
        Microdiff.Microdiff.__init__(self, *args, **kwargs) 
       
    def init(self):
        Microdiff.Microdiff.init(self)
 
        self.centringPhi=sample_centring.CentringMotor(self.phiMotor, direction=1)
        # centringPhiz => should be renamed centringVertical
        self.centringPhiz=sample_centring.CentringMotor(self.phizMotor)
        # centringPhiy => should be renamed centringHorizontal
        self.centringPhiy=sample_centring.CentringMotor(self.phiyMotor, direction=-1, reference_position=0.0037)
        self.centringSamplex=sample_centring.CentringMotor(self.sampleXMotor, direction=-1)
        self.centringSampley=sample_centring.CentringMotor(self.sampleYMotor)
        self.scan_nb_frames=1

        # raster scan attributes
        self.nb_frames =  self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"nbframes" }, "ScanNumberOfFrames")
        self.scan_range = self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"scan_range" }, "ScanRange")
        self.scan_exposure_time = self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"exposure_time" }, "ScanExposureTime")
        self.scan_start_angle = self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"start_angle" }, "ScanStartAngle")
        self.scan_detector_gate_pulse_enabled = self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"detector_gate_pulse_enabled" }, "DetectorGatePulseEnabled")
        self.scan_detector_gate_pulse_readout_time = self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"detector_gate_pulse_readout_time" }, "DetectorGatePulseReadoutTime")


    def getBeamPosX(self):
        return self.beam_info.get_beam_position()[0]

    def getBeamPosY(self):
        return self.beam_info.get_beam_position()[1]

    def setNbImages(self,number_of_images):
        self.scan_nb_frames=number_of_images

        
    def oscilScan(self, start, end, exptime, wait=False):
        if self.in_plate_mode():
            scan_speed = math.fabs(end-start) / exptime
            low_lim, hi_lim = map(float, self.scanLimits(scan_speed))
            if start < low_lim:
                raise ValueError("Scan start below the allowed value %f" % low_lim)
            elif end > hi_lim:
                raise ValueError("Scan end abobe the allowed value %f" % hi_lim)
        self.nb_frames.setValue(self.scan_nb_frames)

        scan_params = "1\t%0.3f\t%0.3f\t%0.4f\t1"% (start, (end-start), exptime)
        scan = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"start_scan" }, "startScanEx")
        scan(scan_params)
        if wait:
            self._wait_ready(300) #timeout of 5 min

    def oscilScan4d(self, start, end, exptime,  motors_pos, wait=False):
        if self.in_plate_mode():
            scan_speed = math.fabs(end-start) / exptime
            low_lim, hi_lim = map(float, self.scanLimits(scan_speed))
            if start < low_lim:
                raise ValueError("Scan start below the allowed value %f" % low_lim)
            elif end > hi_lim:
                raise ValueError("Scan end abobe the allowed value %f" % hi_lim)
                
        self.nb_frames.setValue(self.scan_nb_frames)

        scan_params = "%0.3f\t%0.3f\t%f\t"% (start, (end-start), exptime)
        scan_params += "%0.3f\t" % motors_pos['1']['phiz']
        scan_params += "%0.3f\t" % motors_pos['1']['phiy']
        scan_params += "%0.3f\t" % motors_pos['1']['sampx']
        scan_params += "%0.3f\t" % motors_pos['1']['sampy']
        scan_params += "%0.3f\t" % motors_pos['2']['phiz']
        scan_params += "%0.3f\t" % motors_pos['2']['phiy']
        scan_params += "%0.3f\t" % motors_pos['2']['sampx']
        scan_params += "%0.3f" % motors_pos['2']['sampy']

        scan = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"start_scan4d" }, "startScan4DEx")
        scan(scan_params)
        if wait:
            self._wait_ready(900) #timeout of 15 min


    def oscilScanMesh(self,start, end, exptime, dead_time, mesh_num_lines, mesh_total_nb_frames, mesh_center, mesh_range, wait=False):
        self.scan_detector_gate_pulse_enabled.setValue(True)
        servo_time = 0.110 # adding the servo time to the readout time to avoid any servo cycle jitter 
        self.scan_detector_gate_pulse_readout_time.setValue(dead_time*1000 +servo_time)  # TODO

        # Prepositionning at the center of the grid
        self.moveMotors(mesh_center.as_dict())
        
        positions = self.getPositions()

        scan_params =  "%0.3f\t" % (end-start)
        scan_params += "%0.3f\t" % mesh_range['vertical_range']
        scan_params += "%0.3f\t" % (-mesh_range['horizontal_range'])
        scan_params += "%0.3f\t" % start
        scan_params += "%0.3f\t" % positions['phiz']
        scan_params += "%0.3f\t" % positions['phiy']
        scan_params += "%0.3f\t" % positions['sampx']
        scan_params += "%0.3f\t" % positions['sampy']
        scan_params += "%d\t"    % mesh_num_lines
        scan_params += "%d\t"    % (mesh_total_nb_frames / mesh_num_lines)
        scan_params += "%0.3f\t" % (exptime / mesh_num_lines)
        scan_params += "%r\t" % True
        scan_params += "%r\t" % True
        scan_params += "%r\t" % True

        scan = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"start_raster_scan" }, "startRasterScanEx")

        scan(scan_params)
        if wait:
            self._wait_ready(1800) #timeout of 30 min



