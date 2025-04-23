import math
import time

import numpy
import logging
import gevent
from gevent import Timeout, sleep
from mxcubecore.HardwareObjects import Microdiff
from mxcubecore.HardwareObjects.sample_centring import CentringMotor
from mxcubecore import HardwareRepository as HWR


class MD2(Microdiff.Microdiff):
    def __init__(self, *args, **kwargs):
        Microdiff.Microdiff.__init__(self, *args, **kwargs)


    def init(self):
        Microdiff.Microdiff.init(self)
        try:
            phiy_ref = self["centringReferencePosition"].getProperty("phiy")
        except:
            phiy_ref = None

        self.readPhase.connectSignal("update", self.current_phase_changed)
        self.centringPhi = CentringMotor(self.phiMotor, direction=-1)
        self.centringPhiz = CentringMotor(self.phizMotor)
        self.centringPhiy = CentringMotor(
            self.phiyMotor, direction=-1, reference_position=None
        )
        self.centringSamplex = CentringMotor(self.sampleXMotor, direction=-1)   #-1 for MD2-S
        self.centringSampley = CentringMotor(self.sampleYMotor, direction=1)
        self.scan_nb_frames = -1


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

        self.state_chan = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "state_chan",
            },
            "State",
        )
        self.sample_isloaded_magnet = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "sample_isloaded_magnet",
            },
            "SampleIsLoaded",
        )
        # Cryo_Is_Back get_value得到的是bool type
        self.Cryo_Is_Back = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "Cryo_Is_Back",
            },
            "CryoIsBack",
        )

        self.Cryo_Is_Out = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "Cryo_Is_Out",
            },
            "CryoIsOut",
        )

        # self.Get_Rex_Position = self.add_channel(
        #     {
        #         "type": "exporter",
        #         "exporter_address": self.exporter_addr,
        #         "name": "Get_Rex_Position",
        #     },
        #     "GetRexPosition",
        # )
        #
        # self.Set_Rex_Position = self.add_channel(
        #     {
        #         "type": "exporter",
        #         "exporter_address": self.exporter_addr,
        #         "name": "Set_Rex_Position",
        #     },
        #     "SetRexPosition",
        # )

        self.centring_table_vertical_state = self.add_channel(
            {
                "type":"exporter",
                "exporter_address": self.exporter_addr,
                "name":"centring_table_vertical_state",
            },
            "CentringTableVerticalState",
        )

        self.save_centring_positions = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "save_centring_positions",
            },
            "saveCentringPositions",
        )

        self.start_auto_sample_centring = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "start_auto_sample_centring",
            },
            "startAutoSampleCentring",
        )
        # self.save_centring_positions.set_value()

        self.connect("update", self.state_changed)
    def abort(self):
        self.abort_cmd()

    def state_changed(self, state):
        logging.getLogger("HWR").debug("MD2 State changed %s" % str(state))
        self.emit("minidiffStateChanged", (self.current_state))

    def getBeamPosX(self):
        return self.beam_info.get_beam_position_on_screen()[0]

    def getBeamPosY(self):
        return self.beam_info.get_beam_position_on_screen()[1]

    def current_phase_changed(self, current_phase):
        """
        Descript. :
        """
        logging.getLogger("HWR").info("==== MD2 phase changed to %s" % current_phase)
        # self.emit("phaseChanged", (current_phase))
        self.emit("phaseChanged", current_phase)

    def update_scale(self):
        pixelsPerMmY = self.x_calib.get_value()
        pixelsPerMmZ = self.y_calib.get_value()
        logging.getLogger("HWR").debug("CENTRING DEBUG !!!!!!! scale changed to %f" % pixelsPerMmY)

    def zoomMotorPredefinedPositionChanged(self, positionName, offset=None):
        self.emit("zoomMotorPredefinedPositionChanged", (positionName, offset))

    def get_state(self):
        state = self.state_chan.get_value()
        #print("###################### MD2 State = " + str(state))
        return state

    def setNbImages(self, number_of_images):
        """ Set number of hardware triggers
        """
        self.scan_nb_frames = number_of_images

    def oscilScan(self, start, end, exptime, wait=False):
        if self.in_plate_mode():
            scan_speed = math.fabs(end - start) / exptime
            low_lim, hi_lim = map(float, self.scanLimits(scan_speed))
            if start < low_lim:
                raise ValueError("Scan start below the allowed value %f" % low_lim)
            elif end > hi_lim:
                raise ValueError("Scan end above the allowed value %f" % hi_lim)
        self.nb_frames.set_value(self.scan_nb_frames)

        params = "1\t%0.3f\t%0.3f\t%0.4f\t1" % (start, (end - start), exptime)  # 1,起始角度，扫描范围，暴光时间，1
        print("OSC SCAN's parameter: ",params)
        scan = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "start_scan",
            },
            "startScanEx",
        )

        self._wait_ready(30000)
        start_time=time.time()
        scan(params)
        print("OSC SCAN's time cost: ",time.time()-start_time)
        end_scan_time = time.time()
        if wait:
            # Timeout of 5 min
            self._wait_ready(30000)
        print("wait time after scan end: ",  time.time()-end_scan_time) #这个时间才是应该有的暴光时间

    def oscilScan4d(self, start, end, exptime, motors_pos, wait=False):
        if self.in_plate_mode():
            scan_speed = math.fabs(end - start) / exptime
            low_lim, hi_lim = map(float, self.scanLimits(scan_speed))
            if start < low_lim:
                raise ValueError("Scan start below the allowed value %f" % low_lim)
            elif end > hi_lim:
                raise ValueError("Scan end abobe the allowed value %f" % hi_lim)

        self.nb_frames.set_value(self.scan_nb_frames)

        params = "%0.3f\t%0.3f\t%f\t" % (start, (end - start), exptime)
        params += "%0.3f\t" % motors_pos["1"]["phiy"]
        params += "%0.3f\t" % motors_pos["1"]["phiz"]
        params += "%0.3f\t" % motors_pos["1"]["sampx"]
        params += "%0.3f\t" % motors_pos["1"]["sampy"]
        params += "%0.3f\t" % motors_pos["2"]["phiy"]
        params += "%0.3f\t" % motors_pos["2"]["phiz"]
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

    def wait_ready(self):
        self._wait_ready(300)

    # def oscilScanMesh(
    #     self,
    #     start,
    #     end,
    #     exptime_per_frame,
    #     dead_time,
    #     mesh_num_lines,
    #     mesh_total_nb_frames,
    #     mesh_center,
    #     mesh_range,
    #     wait=False,
    # ):
    #
    #     self.scan_detector_gate_pulse_enabled.set_value(True)
    #
    #     # Adding the servo time to the readout time to avoid any
    #     # servo cycle jitter
    #     servo_time = 0.110
    #
    #     self.scan_detector_gate_pulse_readout_time.set_value(
    #         dead_time * 1000 + servo_time
    #     )
    #
    #     # Prepositionning at the center of the grid
    #     self.move_motors(mesh_center.as_dict())
    #
    #     positions = self.get_positions()
    #     #import pdb;pdb.set_trace()
    #     """
    #     # TODO the hack below overrides the num_lines from queue entry
    #     # that is correct for MD2 but not for MD3
    #     # a better implementation would be to fix the value in the set_dc_params
    #     shape = HWR.beamline.sample_view.get_selected_shapes()[0].as_dict()
    #     mesh_num_lines = shape.get("num_cols")
    #     # TODO the hack below overrides the mesh_total_nb_frames from queue entry
    #     mesh_total_nb_frames = shape.get("num_cols") * shape.get("num_rows")
    #     """
    #     num_rows =  mesh_total_nb_frames / mesh_num_lines
    #     params = "%0.3f\t" % (end - start)
    #     # Set positive pitch to move phiz towards the top because it starts from grid top left corner
    #     params += "%0.3f\t" % (mesh_range["vertical_range"] / 1000.0)   # TODO check why BIOMAX used to pass micrometers
    #     # Set negative pitch to move CT towards the left because it starts from grid top left corner
    #     params += "%0.3f\t" % (mesh_range["horizontal_range"] / 1000.0)
    #     params += "%0.3f\t" % start
    #     params += "%0.3f\t" % positions["phiz"]
    #     params += "%0.3f\t" % (positions["phiy"])
    #     params += "%0.3f\t" % positions["sampx"]
    #     params += "%0.3f\t" % positions["sampy"]
    #     params += "%d\t" % num_rows
    #     params += "%d\t" % mesh_num_lines
    #     params += "%0.3f\t" % exptime_per_frame  # MD expects time per line (per column in MD2)
    #     params += "%r\t" % True
    #     params += "%r\t" % True
    #     params += "%r\t" % True
    #     print("Params of startRasterScanEX of expoter method: ",params)
    #     scan = self.add_command(
    #         {
    #             "type": "exporter",
    #             "exporter_address": self.exporter_addr,
    #             "name": "start_raster_scan",
    #         },
    #         "startRasterScanEx",
    #     )
    #     # self.abort_cmd()
    #     self._wait_ready()
    #     scan(params)
    #
    #     if wait:
    #         # Timeout of 30 min
    #         self._wait_ready()


    # 修改测试
    def oscilScanMesh(
        self,
        start,
        end,
        exptime_per_frame,
        dead_time,
        mesh_num_lines,
        mesh_total_nb_frames,
        mesh_center,
        mesh_range,
        mesh_center_topRightPoint_phiy =None ,
        wait=False,
    ):

        self.scan_detector_gate_pulse_enabled.set_value(True)

        # Adding the servo time to the readout time to avoid any
        # servo cycle jitter
        servo_time = 0.110

        self.scan_detector_gate_pulse_readout_time.set_value(
            dead_time * 1000 + servo_time
        )

        # Prepositionning at the center of the grid
        self.move_motors(mesh_center.as_dict())

        positions = self.get_positions()
        print("mesh scan method in md2, positions: ",positions)
        #import pdb;pdb.set_trace()
        """
        # TODO the hack below overrides the num_lines from queue entry
        # that is correct for MD2 but not for MD3
        # a better implementation would be to fix the value in the set_dc_params
        shape = HWR.beamline.sample_view.get_selected_shapes()[0].as_dict()
        mesh_num_lines = shape.get("num_cols")
        # TODO the hack below overrides the mesh_total_nb_frames from queue entry
        mesh_total_nb_frames = shape.get("num_cols") * shape.get("num_rows")
        """
        num_rows =  mesh_total_nb_frames / mesh_num_lines
        params = "%0.3f\t" % (end - start)
        # Set positive pitch to move phiz towards the top because it starts from grid top left corner
        # params += "%0.3f\t" % (mesh_range["vertical_range"] / 1000.0)   # TODO check why BIOMAX used to pass micrometers
        # # Set negative pitch to move CT towards the left because it starts from grid top left corner
        # params += "%0.3f\t" % (mesh_range["horizontal_range"] / 1000.0)

        #感觉 上面两个参数前后顺序反了
        # params += "%0.3f\t" % (mesh_range["horizontal_range"] / 1000.0)   # TODO check why BIOMAX used to pass micrometers
        # # Set negative pitch to move CT towards the left because it starts from grid top left corner
        # params += "%0.3f\t" % (mesh_range["vertical_range"] / 1000.0)
        #改，放大两倍,20240507,改回，不放大了
        params += "%0.3f\t" % (mesh_range["horizontal_range"] / 1000.0)  # TODO check why BIOMAX used to pass micrometers
        # Set negative pitch to move CT towards the left because it starts from grid top left corner
        params += "%0.3f\t" % (mesh_range["vertical_range"] / 1000.0)
        params += "%0.3f\t" % start
        # params += "%0.3f\t" % positions["phiy"]
        params += "%0.3f\t" % mesh_center_topRightPoint_phiy    #改
        params += "%0.3f\t" % (positions["phiz"])
        params += "%0.3f\t" % positions["sampx"]
        params += "%0.3f\t" % positions["sampy"]
        params += "%d\t" % num_rows
        params += "%d\t" % mesh_num_lines
        params += "%0.3f\t" % exptime_per_frame  # MD expects time per line (per column in MD2)
        params += "%r\t" % True
        params += "%r\t" % True
        params += "%r\t" % True
        print("[RasterScanEX info] Params of startRasterScanEX of expoter method: ",params)
        scan = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "start_raster_scan",
            },
            "startRasterScanEx",
        )
        # self.abort_cmd()
        self._wait_ready()
        scan(params)

        if wait:
            # Timeout of 30 min
            self._wait_ready()

    # def get_centred_point_from_coord(self, x, y, return_by_names=None):
    #     self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(
    #         self.zoomMotor.get_value()
    #     )
    #
    #     if None in (self.pixelsPerMmY, self.pixelsPerMmZ):
    #         return 0, 0
    #
    #     beam_pos_x, beam_pos_y = HWR.beamline.beam.get_beam_position_on_screen()
    #     dx = (x - beam_pos_x) / self.pixelsPerMmY
    #     dy = (y - beam_pos_y) / self.pixelsPerMmZ
    #
    #     phi_angle = math.radians(
    #         self.centringPhi.direction * self.centringPhi.get_value()
    #     )
    #
    #     #import pdb; pdb.set_trace()
    #     sampx = self.centringSamplex.direction * self.centringSamplex.get_value()
    #     sampy = self.centringSampley.direction * self.centringSampley.get_value()
    #
    #     phiy = -self.centringPhiy.direction * self.centringPhiy.get_value()
    #     phiz = self.centringPhiz.direction * self.centringPhiz.get_value()
    #
    #     # Focus df and horizontal move (along dx) result from sampx,sampy * RotMatrix
    #     rotMatrix = numpy.matrix(
    #         [
    #             [math.cos(phi_angle), -math.sin(phi_angle)],
    #             [math.sin(phi_angle), math.cos(phi_angle)],
    #         ]
    #     )
    #
    #     invRotMatrix = numpy.array(rotMatrix.I)
    #
    #     # calculate the shift with sampx sampy to do inside focus plan to reach x from beam center (move vector 0,dx in MD frame cs)
    #     dsampx, dsampy = numpy.dot(numpy.array([0, dx]), invRotMatrix)
    #
    #     chi_angle = math.radians(-self.chiAngle)
    #     chiRot = numpy.matrix(
    #         [
    #             [math.cos(chi_angle), -math.sin(chi_angle)],
    #             [math.sin(chi_angle), math.cos(chi_angle)],
    #         ]
    #     )
    #
    #     sx, sy = numpy.dot(numpy.array([dsampx, dsampy]), numpy.array(chiRot))
    #
    #     sampx = sampx + sx
    #     sampy = sampy + sy
    #     phiz = phiz + dy
    #
    #
    #     dict = {
    #         "phi": round(self.centringPhi.get_value()),
    #         "phiz": round(phiz, 4),
    #         "phiy": round(phiy, 4),
    #         "sampx": round(sampx, 4),
    #         "sampy": round(sampy, 4),
    #     }
    #
    #     logging.getLogger("HWR").debug("MD2: centring point from coord (%d,%d) -> %s" %(x, y, str(dict)))
    #
    #     return dict





    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        # 20240312
        # 此函数根据 mesh scan画的正方形的点坐标生成对应移动 md2 的参数
        # 初步判断，mesh scan时，会传送左上和右下的坐标到此函数，其中左上的坐标和gotobeam函数所获得的坐标是一致的，右下不是


        #20240319
        # 此函数作用是
        # 根据坐标点求出对应电机位置：
        # "phi": round(self.centringPhi.get_value()),
        # "phiz": round(phiz, 4),
        # "phiy": round(phiy, 4),
        # "sampx": round(sampx, 4),
        # "sampy": round(sampy, 4),
        # 其中phi ， phiz 不变, 需要知道sampx 和 sampy 和 phiy 的位置
        # phiy 的位置可以根据move_to_beam的代码得知，
        # 但sampx与sampy的具体位置不知道，只能得到centring vertical的值,因此需要先通过move_to_beam实际移动过去，再分别读取
        #   sampx 和 sampy


        logging.getLogger("HWR.MX3").info("get into get_centred_point_from_coord in MD2")
        self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(
            self.zoomMotor.get_value()
        )
        if None in (self.pixelsPerMmY, self.pixelsPerMmZ):
            return 0, 0
        self.log.debug(
            "the pixelsPerMmY: %d, Z:%d. the selected x: %d, y: %d. " % (self.pixelsPerMmY, self.pixelsPerMmZ, x, y))



        beam_pos_x, beam_pos_y = HWR.beamline.beam.get_beam_position_on_screen()
        self.log.debug("the beam_pos_x: %d, y:%d. " % (beam_pos_x, beam_pos_y))

        dx = (x - beam_pos_x) / (self.pixelsPerMmY)
        dy = (y - beam_pos_y) / (self.pixelsPerMmZ)







        # from move to beam
        sampeVertical = self.centringVertical.get_value()
        phiy = self.centringPhiy.get_value()

        # 改变前先记录原始位置
        old_sameVertical = sampeVertical
        old_phiy = phiy
        sampeVertical = sampeVertical + dy
        phiy = phiy - dx

        # 让md2移动到目标点来获取对应的 samp-x 与 samp-y 的值
        self.centringVertical.set_value(sampeVertical)  # 此函数控制md2上下移动，会移动mxcube界面Samp-X 和 Samp-Y电机
        self.centringPhiy.set_value(phiy)  # 此函数控制md2左右移动，会移动mxcube界面上的phiy电机

        # 等待centringVertical重新变回ready
        # if self.centring_table_vertical_state.get_value() == "Ready":
        self.centringVertical.wait_move()
        self.centringPhiy.wait_move()




        phiz = self.centringPhiz.direction * self.centringPhiz.get_value()

        # sampx = self.centringSamplex.direction * self.centringSamplex.get_value()
        # sampy = self.centringSampley.direction * self.centringSampley.get_value()
        sampx = -self.centringSamplex.direction * self.centringSamplex.get_value()
        sampy = self.centringSampley.direction * self.centringSampley.get_value()

        # 按照源代码尝试解决sampx 与sampy问题：
        # 尝试的不太行
        # sampx = self.centringSamplex.direction * self.centringSamplex.get_value()
        # sampy = self.centringSampley.direction * self.centringSampley.get_value()
        # phi_angle = math.radians(
        #     self.centringPhi.direction * self.centringPhi.get_value()
        # )
        # rotMatrix = numpy.matrix(
        #     [
        #         [math.cos(phi_angle), -math.sin(phi_angle)],
        #         [math.sin(phi_angle), math.cos(phi_angle)],
        #     ]
        # )
        # invRotMatrix = numpy.array(rotMatrix.I)
        # dsampx, dsampy = numpy.dot(numpy.array([0, dx]), invRotMatrix)
        # chi_angle = math.radians(-self.chiAngle)
        # chiRot = numpy.matrix(
        #     [
        #         [math.cos(chi_angle), -math.sin(chi_angle)],
        #         [math.sin(chi_angle), math.cos(chi_angle)],
        #     ]
        # )
        # sx, sy = numpy.dot(numpy.array([dsampx, dsampy]), numpy.array(chiRot))
        # sampx = sampx + sx
        # sampy = sampy + sy

        # 移动完之后再移动回来，否则影响整体坐标系的位置
        self.centringVertical.set_value(old_sameVertical)
        self.centringPhiy.set_value(old_phiy)
        self.centringVertical.wait_move()
        self.centringPhiy.wait_move()


        dict = {
            "phi": round(self.centringPhi.get_value()),
            "phiz": round(phiz, 4),
            "phiy": round(phiy, 4),
            "sampx": round(sampx, 4),
            "sampy": round(sampy, 4),
        }

        logging.getLogger("HWR").debug("MD2: centring point from coord (%d,%d) -> %s" %(x, y, str(dict)))

        return dict



    # Override using value from Camera device instead than from exporter MD2 server
    def getCalibrationData(self, offset):
        #return self.zoomMotor.get_pixels_per_mm()
        (x, y) = (1.0 / self.x_calib.get_value(), 1.0 / self.y_calib.get_value())
        # print("pixelsPerMmY: %d pixelsPerMmZ: %d" % (x, y))
        return (x/2, y/2)


    def getCalibrationData_custom(self):
        (x, y) = (1.0 / self.x_calib.get_value(), 1.0 / self.y_calib.get_value())
        # print("pixelsPerMmY: %d pixelsPerMmZ: %d" % (x, y))
        return (x, y)

    def motor_positions_to_screen(self, centred_positions_dict):
        self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(
            self.zoomMotor.get_value()
        )

        if None in (self.pixelsPerMmY, self.pixelsPerMmZ):
            return 0, 0

        #print("+++++++ motor_positions_to_screen " + str(centred_positions_dict))
        #print("Mapping motor positions to screen: scale = %f pix/mm %f um/pix" %
        #      (self.pixelsPerMmY, 1000 / self.pixelsPerMmY)
        #      )

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

        beam_pos_x, beam_pos_y = HWR.beamline.beam.get_beam_position_on_screen()
        x = (sy + phiy) * self.pixelsPerMmY + beam_pos_x
        y = phiz * self.pixelsPerMmZ + beam_pos_y

        #print("MD2 centring point on screen = (%d,%d) from mpos = %s" % (int(x), int(y), str(centred_positions_dict)))

        return float(x), float(y)

    def move_to_beam(self, x, y):
        self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(
            self.zoomMotor.get_value()
        )
        self.log.debug("the pixelsPerMmY: %d, y:%d. the selected x: %d, y: %d. "%(self.pixelsPerMmY,self.pixelsPerMmZ,x,y))

        if None in (self.pixelsPerMmY, self.pixelsPerMmZ):
            return 0, 0

        beam_pos_x, beam_pos_y = HWR.beamline.beam.get_beam_position_on_screen()
        self.log.debug("the beam_pos_x: %d, y:%d. "%(beam_pos_x,beam_pos_y))

        # dx = (x - beam_pos_x) / self.pixelsPerMmY
        # dy = (y - beam_pos_y) / self.pixelsPerMmZ
        # worked for now
        dx = (x - beam_pos_x) / (self.pixelsPerMmY)
        dy = (y - beam_pos_y) / (self.pixelsPerMmZ)

        phi_angle = math.radians(
            self.centringPhi.direction * self.centringPhi.get_value()
        )
        # cx
       # sampx = self.centringSamplex.direction * self.centringSamplex.get_value()
        #sampx = -self.centringSamplex.direction * self.centringSamplex.get_value()
        # cy
       # sampy = self.centringSampley.direction * self.centringSampley.get_value()
        sampy = self.centringVertical.get_value()
        # Ay
        phiy = self.centringPhiy.get_value()
        # phiz = self.centringPhiz.direction * self.centringPhiz.get_value()


        # rotMatrix = numpy.matrix(
        #     [
        #         [math.cos(phi_angle), -math.sin(phi_angle)],
        #         [math.sin(phi_angle), math.cos(phi_angle)],
        #     ]
        # )
        # invRotMatrix = numpy.array(rotMatrix.I)
        #
        # dsampx, dsampy = numpy.dot(numpy.array([dy, 0]), invRotMatrix)
        #dsampx, dsampy = numpy.dot(numpy.array([dx, 0]), invRotMatrix)

        # chi_angle = math.radians(-self.chiAngle)
        # chiRot = numpy.matrix(
        #     [
        #         [math.cos(chi_angle), -math.sin(chi_angle)],
        #         [math.sin(chi_angle), math.cos(chi_angle)],
        #     ]
        # )
        #
        # sx, sy = numpy.dot(numpy.array([dsampx, dsampy]), numpy.array(chiRot))


        #sampx = sampx + sy
        sampy = sampy + dy
        phiy = phiy - dx
        # sampx = sampx + sx
        # sampy = sampy + sy
        # phiz = phiz + dy
        # import pdb; pdb.set_trace()
        try:
            self.log.debug("try to set cantringVertical to : %f, centringPhiy to :%f. " % (sampy, phiy))
            # self.centringSamplex.set_value(sampx)
            # self.centringSampley.set_value(sampy)
            self.centringVertical.set_value(sampy)      #此函数控制md2上下移动，会移动mxcube界面Samp-X 和 Samp-Y电机
            #self.centringFocus(phiy)
            self.centringPhiy.set_value(phiy)           # 此函数控制md2左右移动，会移动mxcube界面上的phiy电机
            #self.centringPhiz.set_value(phiz)
        except Exception:
            msg = "MiniDiff: could not center to beam, aborting"
            logging.getLogger("HWR").exception(msg)

