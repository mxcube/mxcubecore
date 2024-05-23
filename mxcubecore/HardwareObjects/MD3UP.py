import math
import numpy
import logging
import time

from mxcubecore.HardwareObjects import Microdiff
from mxcubecore.HardwareObjects.sample_centring import CentringMotor
from mxcubecore import HardwareRepository as HWR


class MD3UP(Microdiff.Microdiff):
    def __init__(self, *args, **kwargs):
        Microdiff.Microdiff.__init__(self, *args, **kwargs)

    def init(self):
        Microdiff.Microdiff.init(self)
        phiy_ref = self["centringReferencePosition"].get_property("phiy")

        self.centringPhi = CentringMotor(self.phiMotor, direction=1)
        self.centringPhiz = CentringMotor(self.phizMotor)
        self.centringPhiy = CentringMotor(
            self.phiyMotor, direction=-1, reference_position=phiy_ref
        )
        self.centringSamplex = CentringMotor(self.sampleXMotor, direction=-1)
        self.centringSampley = CentringMotor(self.sampleYMotor)
        self.scan_nb_frames = 1

        # Raster scan attributes
        self.nb_frames = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "nbframes",
            },
            "ScanNumberOfFrames",
        )
        self.scan_range = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "scan_range",
            },
            "ScanRange",
        )
        self.scan_exposure_time = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "exposure_time",
            },
            "ScanExposureTime",
        )
        self.scan_start_angle = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "start_angle",
            },
            "ScanStartAngle",
        )
        self.scan_detector_gate_pulse_enabled = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "detector_gate_pulse_enabled",
            },
            "DetectorGatePulseEnabled",
        )
        self.scan_detector_gate_pulse_readout_time = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "detector_gate_pulse_readout_time",
            },
            "DetectorGatePulseReadoutTime",
        )

    # def getBeamPosX(self):
    #     return self.beam_info.get_beam_position_on_screen()[0]
    #
    # def getBeamPosY(self):
    #     return self.beam_info.get_beam_position_on_screen()[1]

    def setNbImages(self, number_of_images):
        self.scan_nb_frames = number_of_images

    def oscilScan(self, start, end, exptime, number_of_images, wait=False):
        if self.in_plate_mode():
            scan_speed = math.fabs(end - start) / exptime
            low_lim, hi_lim = map(float, self.scanLimits(scan_speed))
            if start < low_lim:
                raise ValueError("Scan start below the allowed value %f" % low_lim)
            elif end > hi_lim:
                raise ValueError("Scan end abobe the allowed value %f" % hi_lim)

        dead_time = HWR.beamline.config.detector.get_deadtime()

        self.scan_detector_gate_pulse_enabled.set_value(True)
        self.scan_detector_gate_pulse_readout_time.set_value(dead_time * 1000)

        if self.get_property("md_set_number_of_frames", False):
            self.nb_frames.set_value(number_of_images)
        else:
            self.nb_frames.set_value(1)

        scan_params = "1\t%0.3f\t%0.3f\t%0.4f\t1" % (start, (end - start), exptime)
        scan = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "start_scan",
            },
            "startScanEx",
        )
        scan(scan_params)
        print("oscil scan started at ----------->", time.time())
        if wait:
            self._wait_ready(20 * 60)  # Timeout of 20 min
            print("finished at ---------->", time.time())

    def oscilScan4d(
        self, start, end, exptime, number_of_images, motors_pos, wait=False
    ):
        if self.in_plate_mode():
            scan_speed = math.fabs(end - start) / exptime
            low_lim, hi_lim = map(float, self.scanLimits(scan_speed))
            if start < low_lim:
                raise ValueError("Scan start below the allowed value %f" % low_lim)
            elif end > hi_lim:
                raise ValueError("Scan end abobe the allowed value %f" % hi_lim)

        if self.get_property("md_set_number_of_frames", False):
            self.nb_frames.set_value(number_of_images)
        else:
            self.nb_frames.set_value(1)

        params = "%0.3f\t%0.3f\t%f\t" % (start, (end - start), exptime)
        params += "%0.3f\t" % motors_pos["1"]["phiz"]
        params += "%0.3f\t" % motors_pos["1"]["phiy"]
        params += "%0.3f\t" % motors_pos["1"]["sampx"]
        params += "%0.3f\t" % motors_pos["1"]["sampy"]
        params += "%0.3f\t" % motors_pos["2"]["phiz"]
        params += "%0.3f\t" % motors_pos["2"]["phiy"]
        params += "%0.3f\t" % motors_pos["2"]["sampx"]
        params += "%0.3f" % motors_pos["2"]["sampy"]

        scan = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "start_scan4d",
            },
            "startScan4DEx",
        )

        scan(params)

        if wait:
            # Timeout of 15 min
            self._wait_ready(900)

    def oscilScanMesh(
        self,
        start,
        end,
        exptime,
        dead_time,
        mesh_num_lines,
        mesh_total_nb_frames,
        mesh_center,
        mesh_range,
        wait=False,
    ):
        self.scan_detector_gate_pulse_enabled.set_value(True)
        dead_time = HWR.beamline.config.detector.get_deadtime()
        self.scan_detector_gate_pulse_readout_time.set_value(dead_time * 1000)
        self.move_motors(mesh_center.as_dict())
        positions = self.get_positions()

        params = "%0.3f\t" % (end - start)
        params += "%0.3f\t" % mesh_range["vertical_range"]
        params += "%0.3f\t" % (-mesh_range["horizontal_range"])
        params += "%0.3f\t" % start
        params += "%0.3f\t" % positions["phiz"]
        params += "%0.3f\t" % positions["phiy"]
        params += "%0.3f\t" % positions["sampx"]
        params += "%0.3f\t" % positions["sampy"]
        params += "%d\t" % mesh_num_lines
        params += "%d\t" % (mesh_total_nb_frames / mesh_num_lines)
        params += "%0.3f\t" % (exptime / mesh_num_lines)
        params += "%r\t" % True
        params += "%r\t" % True
        params += "%r\t" % True

        scan = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "start_raster_scan",
            },
            "startRasterScanEx",
        )

        scan(params)

        if wait:
            # Timeout of 30 min
            self._wait_ready(1800)

    def timeresolved_mesh_scan(self, timeout=900):
        """Start timeresolved mesh.
        Args:
            timeout(float): Timeout to wait the execution of the scan [s].
                            Default value is 15 min
        """
        scan = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "start_timeresolved_mesh",
            },
            "startContinuousTimeResolvedRasterScan",
        )
        scan()

        # wait for the execution of the scan
        self._wait_ready(timeout)

    def get_timeresolved_mesh_nbframes(self):
        """Get the calculated number of frames for the continuous timeresolved
           mesh scan.
        Returns:
            (int): Number of frames.
        """
        cmd = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "timeresolved_mesh_nbframes",
            },
            "ContinuousTimeResolvedRasterScanNbFrames",
        )
        return cmd.get_value()

    def get_timeresolved_mesh_exptime(self):
        """Get the calculated exposure time for the continuous timeresolved
           mesh scan.
        Returns:
            (float): Exposure time [s].
        """

        cmd = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "timeresolved_mesh_exptime",
            },
            "ContinuousTimeResolvedRasterScanExposureTime",
        )
        return cmd.get_value()

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(
            self.zoomMotor.get_value()
        )

        if None in (self.pixelsPerMmY, self.pixelsPerMmZ):
            return 0, 0

        beam_pos_x, beam_pos_y = HWR.beamline.config.beam.get_beam_position_on_screen()
        dx = (x - beam_pos_x) / self.pixelsPerMmY
        dy = (y - beam_pos_y) / self.pixelsPerMmZ

        phi_angle = math.radians(
            self.centringPhi.direction * self.centringPhi.get_value()
        )

        sampx = -self.centringSamplex.direction * self.centringSamplex.get_value()
        sampy = self.centringSampley.direction * self.centringSampley.get_value()

        phiy = -self.centringPhiy.direction * self.centringPhiy.get_value()
        phiz = self.centringPhiz.direction * self.centringPhiz.get_value()

        rotMatrix = numpy.matrix(
            [
                [math.cos(phi_angle), -math.sin(phi_angle)],
                [math.sin(phi_angle), math.cos(phi_angle)],
            ]
        )
        invRotMatrix = numpy.array(rotMatrix.I)

        dsampx, dsampy = numpy.dot(numpy.array([dx, dy]), invRotMatrix)

        chi_angle = math.radians(-self.chiAngle)
        chiRot = numpy.matrix(
            [
                [math.cos(chi_angle), -math.sin(chi_angle)],
                [math.sin(chi_angle), math.cos(chi_angle)],
            ]
        )

        sx, sy = numpy.dot(numpy.array([dsampx, dsampy]), numpy.array(chiRot))

        sampx = sampx + sx
        sampy = sampy + sy
        phiz = phiz + dy

        return {
            "phi": self.centringPhi.get_value(),
            "phiz": float(phiz),
            "phiy": float(phiy),
            "sampx": float(sampx),
            "sampy": float(sampy),
        }

    def motor_positions_to_screen(self, centred_positions_dict):
        self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(
            self.zoomMotor.get_value()
        )

        if None in (self.pixelsPerMmY, self.pixelsPerMmZ):
            return 0, 0

        phi_angle = math.radians(
            self.centringPhi.direction * self.centringPhi.get_value()
        )
        sampx = self.centringSamplex.direction * (
            centred_positions_dict["sampx"] - self.centringSamplex.get_value()
        )
        sampy = self.centringSampley.direction * (
            centred_positions_dict["sampy"] - self.centringSampley.get_value()
        )
        phiy = self.centringPhiy.direction * (
            centred_positions_dict["phiy"] - self.centringPhiy.get_value()
        )
        phiz = self.centringPhiz.direction * (
            centred_positions_dict["phiz"] - self.centringPhiz.get_value()
        )

        rotMatrix = numpy.matrix(
            [
                math.cos(phi_angle),
                -math.sin(phi_angle),
                math.sin(phi_angle),
                math.cos(phi_angle),
            ]
        )
        rotMatrix.shape = (2, 2)
        invRotMatrix = numpy.array(rotMatrix.I)

        dsx, dsy = numpy.dot(numpy.array([sampx, sampy]), invRotMatrix)

        chi_angle = math.radians(self.chiAngle)
        chiRot = numpy.matrix(
            [
                math.cos(chi_angle),
                -math.sin(chi_angle),
                math.sin(chi_angle),
                math.cos(chi_angle),
            ]
        )
        chiRot.shape = (2, 2)

        sx, sy = numpy.dot(numpy.array([0, dsy]), numpy.array(chiRot))

        beam_pos_x, beam_pos_y = HWR.beamline.config.beam.get_beam_position_on_screen()
        x = (sx + phiy) * self.pixelsPerMmY + beam_pos_x
        y = (sy + phiz) * self.pixelsPerMmZ + beam_pos_y

        return float(x), float(y)

    def move_to_beam(self, x, y):
        self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(
            self.zoomMotor.get_value()
        )

        if None in (self.pixelsPerMmY, self.pixelsPerMmZ):
            return 0, 0

        beam_pos_x, beam_pos_y = HWR.beamline.config.beam.get_beam_position_on_screen()
        dx = (x - beam_pos_x) / self.pixelsPerMmY
        dy = (y - beam_pos_y) / self.pixelsPerMmZ

        phi_angle = math.radians(
            self.centringPhi.direction * self.centringPhi.get_value()
        )

        sampx = -self.centringSamplex.direction * self.centringSamplex.get_value()
        sampy = self.centringSampley.direction * self.centringSampley.get_value()
        phiz = self.centringPhiz.direction * self.centringPhiz.get_value()

        rotMatrix = numpy.matrix(
            [
                [math.cos(phi_angle), -math.sin(phi_angle)],
                [math.sin(phi_angle), math.cos(phi_angle)],
            ]
        )
        invRotMatrix = numpy.array(rotMatrix.I)

        dsampx, dsampy = numpy.dot(numpy.array([dx, 0]), invRotMatrix)

        chi_angle = math.radians(-self.chiAngle)
        chiRot = numpy.matrix(
            [
                [math.cos(chi_angle), -math.sin(chi_angle)],
                [math.sin(chi_angle), math.cos(chi_angle)],
            ]
        )

        sx, sy = numpy.dot(numpy.array([dsampx, dsampy]), numpy.array(chiRot))

        sampx = sampx + sx
        sampy = sampy + sy
        phiz = phiz + dy

        try:
            self.centringSamplex.set_value(sampx)
            self.centringSampley.set_value(sampy)
            self.centringPhiz.set_value(phiz)
        except Exception:
            msg = "MiniDiff: could not center to beam, aborting"
            logging.getLogger("HWR").exception(msg)
