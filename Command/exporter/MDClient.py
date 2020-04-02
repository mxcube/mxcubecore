import sys
import time
import string
import threading
from ExporterClient import *

SERVER_ADDRESS = "localhost"
SERVER_PORT = 9001
SERVER_PROTOCOL = PROTOCOL.STREAM
TIMEOUT = 3
RETRIES = 1


class MDClient(ExporterClient):
    # Constants
    STATE_READY = "Ready"
    STATE_INITIALIZING = "Initializing"
    STATE_STARTING = "Starting"
    STATE_RUNNING = "Running"
    STATE_MOVING = "Moving"
    STATE_CLOSING = "Closing"
    STATE_REMOTE = "Remote"
    STATE_STOPPED = "Stopped"
    STATE_COMMUNICATION_ERROR = "Communication Error"
    STATE_INVALID = "Invalid"
    STATE_OFFLINE = "Offline"
    STATE_ALARM = "Alarm"
    STATE_FAULT = "Fault"
    STATE_UNKNOWN = "Unknown"

    DEVICE_PMAC = "Pmac"

    MOTOR_OMEGA = "omega"
    MOTOR_KAPPA = "kappa"
    MOTOR_PHI = "phi"
    MOTOR_CX = "cx"
    MOTOR_CY = "cy"
    MOTOR_X = "x"
    MOTOR_Y = "y"
    MOTOR_Z = "z"
    MOTOR_APERTUREZ = "aperturez"
    MOTOR_APERTUREY = "aperturey"
    MOTOR_CAPILLARYZ = "capillaryz"
    MOTOR_CAPILLARYY = "capillaryy"
    MOTOR_SCINTILLATORZ = "scintillatorpdz"
    MOTOR_SCINTILLATORY = "scintillatorpdy"
    MOTOR_BEAMSTOPX = "beamstopx"
    MOTOR_BEAMSTOPY = "beamstopy"
    MOTOR_BEAMSTOPZ = "beamstopz"
    MOTOR_ZOOM = "zoom"

    ALL_MOTORS = [
        MOTOR_OMEGA,
        MOTOR_KAPPA,
        MOTOR_PHI,
        MOTOR_CX,
        MOTOR_CY,
        MOTOR_X,
        MOTOR_Y,
        MOTOR_Z,
        MOTOR_APERTUREZ,
        MOTOR_APERTUREY,
        MOTOR_CAPILLARYZ,
        MOTOR_CAPILLARYY,
        MOTOR_SCINTILLATORZ,
        MOTOR_SCINTILLATORY,
        MOTOR_BEAMSTOPX,
        MOTOR_BEAMSTOPY,
        MOTOR_BEAMSTOPZ,
        MOTOR_ZOOM,
    ]

    PHASE_CENTRING = "Centring"
    PHASE_BEAM_LOCATION = "BeamLocation"
    PHASE_DATA_COLLECTION = "DataCollection"
    PHASE_TRANSFER = "Transfer"
    PHASE_UNKNOWN = "Unknown"

    POSITION_BEAM = "BEAM"
    POSITION_OFF = "OFF"
    POSITION_PARK = "PARK"
    POSITION_UNKNOWN = "UNKNOWN"
    POSITION_SCINTILLATOR = "SCINTILLATOR"
    POSITION_PHOTODIODE = "PHOTODIODE"

    PROPERTY_STATE = "State"
    PROPERTY_STATUS = "Status"
    PROPERTY_ALARM_LIST = "AlarmList"
    PROPERTY_MOTOR_STATES = "MotorStates"
    PROPERTY_MOTOR_POSITIONS = "MotorPositions"
    PROPERTY_LOCKOUT = "LocalGuiLockOut"
    PROPERTY_VERSION = "Version"
    PROPERTY_UPTIME = "Uptime"
    PROPERTY_KAPPA_ENABLED = "KappaIsEnabled"
    PROPERTY_SCAN_START_ANGLE = "ScanStartAngle"
    PROPERTY_SCAN_EXPOSURE_TIME = "ScanExposureTime"
    PROPERTY_SCAN_RANGE = "ScanRange"
    PROPERTY_SCAN_NUMBER_OF_PASSES = "ScanNumberOfPasses"
    PROPERTY_SCAN_SPEED = "ScanExposureTime"
    PROPERTY_SCAN_PASS_DURATION = "ScanPassDuration"
    PROPERTY_FRAME_NUMBER = "FrameNumber"
    PROPERTY_SAMPLE_UID = "SampleUID"
    PROPERTY_SAMPLE_IMAGE_NAME = "SampleImageName"
    PROPERTY_SAMPLE_LOOP_TYPE = "SampleLoopType"
    PROPERTY_SAMPLE_LOOP_SIZE = "SampleLoopSize"
    PROPERTY_SAMPLE_HOLDER_LENGTH = "SampleHolderLength"
    PROPERTY_BEAM_SIZE_HORIZONTAL = "BeamSizeHorizontal"
    PROPERTY_BEAM_SIZE_VERTICAL = "BeamSizeVertical"
    PROPERTY_FAST_SHUTTER_OPEN = "FastShutterIsOpen"
    PROPERTY_FLUO_DETECTOR_BACK = "FluoDetectorIsBack"
    PROPERTY_CRYO_BACK = "CryoIsBack"
    PROPERTY_SAMPLE_IS_LOADED = "SampleIsLoaded"
    PROPERTY_SAMPLE_IS_CENTRED = "SampleIsCentred"
    PROPERTY_USE_SAMPLE_CHANGER = "UseSampleChanger"
    PROPERTY_CURRENT_PHASE = "CurrentPhase"
    PROPERTY_INTERLOCK_ENABLED = "InterlockEnabled"
    PROPERTY_FRONT_LIGHT_LEVEL = "FrontLightLevel"
    PROPERTY_BACK_LIGHT_LEVEL = "BackLightLevel"
    PROPERTY_ZOOM_LEVEL = "CoaxialCameraZoomValue"
    PROPERTY_SCALE_X = "CoaxCamScaleX"
    PROPERTY_SCALE_Y = "CoaxCamScaleY"
    PROPERTY_IMAGE_JPG = "ImageJPG"

    PROPERTY_ACCESS_READ_ONLY = "READ_ONLY"
    PROPERTY_ACCESS_READ_WRITE = "READ_WRITE"
    PROPERTY_ACCESS_WRITE_ONLY = "WRITE_ONLY"

    READ_ONLY_PROPERTIES = [
        PROPERTY_VERSION,  # string
        PROPERTY_UPTIME,  # string
        PROPERTY_SCAN_SPEED,  # double
        PROPERTY_SCAN_PASS_DURATION,  # double
        PROPERTY_SAMPLE_IS_LOADED,  # boolean
        PROPERTY_SAMPLE_IS_CENTRED,  # boolean
        PROPERTY_USE_SAMPLE_CHANGER,  # boolean
        PROPERTY_CURRENT_PHASE,  # string
        PROPERTY_SCALE_X,  # double
        PROPERTY_SCALE_Y,  # double
    ]

    READ_WRITE_PROPERTIES = [
        PROPERTY_LOCKOUT,  # boolean
        PROPERTY_KAPPA_ENABLED,  # boolean
        PROPERTY_SCAN_START_ANGLE,  # double
        PROPERTY_SCAN_EXPOSURE_TIME,  # double
        PROPERTY_SCAN_RANGE,  # double
        PROPERTY_SCAN_NUMBER_OF_PASSES,  # int
        PROPERTY_FRAME_NUMBER,  # int
        PROPERTY_SAMPLE_UID,  # string
        PROPERTY_SAMPLE_IMAGE_NAME,  # string
        PROPERTY_SAMPLE_LOOP_TYPE,  # string
        PROPERTY_SAMPLE_LOOP_SIZE,  # double
        PROPERTY_SAMPLE_HOLDER_LENGTH,  # double
        PROPERTY_BEAM_SIZE_HORIZONTAL,  # double
        PROPERTY_BEAM_SIZE_VERTICAL,  # double
        PROPERTY_FAST_SHUTTER_OPEN,  # boolean
        PROPERTY_FLUO_DETECTOR_BACK,  # boolean
        PROPERTY_CRYO_BACK,  # boolean
        PROPERTY_INTERLOCK_ENABLED,  # boolean
        PROPERTY_FRONT_LIGHT_LEVEL,  # double
        PROPERTY_BACK_LIGHT_LEVEL,  # double
    ]

    MONITORING_INTERVAL = 0.1
    DEFAULT_TASK_TIMEOUT = 60.0

    # Event receiving callback

    STATE_EVENT = "State"
    STATUS_EVENT = "Status"
    VALUE_EVENT = "Value"
    POSITION_EVENT = "Position"
    MOTOR_STATES_EVENT = "MotorStates"

    def onEvent(self, name, value, timestamp):
        if name == self.STATE_EVENT:
            self.onStateEvent(value)
        elif name == self.STATUS_EVENT:
            self.onStatusEvent(value)
        elif name == self.MOTOR_STATES_EVENT:
            array = self.parseArray(value)
            states_dict = self.createDictFromStringList(array)
            self.onMotorStatesEvent(states_dict)
        elif name.endswith(self.STATE_EVENT):
            device = name[: (len(name) - len(self.STATE_EVENT))]
            self.onDeviceStateEvent(device, value)
        elif name.endswith(self.VALUE_EVENT):
            device = name[: (len(name) - len(self.VALUE_EVENT))]
            self.onDeviceValueEvent(device, value)
        elif name.endswith(self.POSITION_EVENT):
            device = name[: (len(name) - len(self.POSITION_EVENT))]
            self.onDevicePositionEvent(device, value)

    def onStateEvent(self, state):
        pass

    def onStatusEvent(self, status):
        pass

    def onMotorStatesEvent(self, states_dict):
        pass

    def onDeviceValueEvent(self, device, value):
        pass

    def onDeviceStateEvent(self, device, state):
        pass

    def onDevicePositionEvent(self, device, position):
        pass

    # Overall application state

    # STATE_INITIALIZING, STATE_STARTING, STATE_READY, STATE_RUNNING,
    # STATE_CLOSING, STATE_STOPPED, STATE_COMMUNICATION_ERROR, STATE_ALARM or
    # STATE_FAULT

    def get_state(self):
        return self.read_property("State")

    def getStatus(self):
        return self.read_property("Status")

    def restart(self, init_hardware=False):
        return self.execute("restart", (init_hardware,))

    def abort(self):
        return self.execute("abort")

    # Task synchronization

    def wait_ready(self, timeout=0):
        start = time.clock()
        while True:
            state = self.get_state()
            if self.isBusy(state) is False:
                return
            if (timeout > 0) and ((time.clock() - start) > timeout):
                raise "Timeout waiting microdiff ready"
            time.sleep(self.MONITORING_INTERVAL)

    def isTaskRunning(self, task_id=-1):
        if task_id < 0:
            if self.isBusy(self.get_state()):
                return True
        elif self.execute("isTaskRunning", (task_id,)) == "true":
            return True
        return False

    def isBusy(self, state):
        return (state == self.STATE_RUNNING) or (state == self.STATE_MOVING)

    def waitTaskResult(self, task_id=-1, timeout=DEFAULT_TASK_TIMEOUT):
        if task_id < 0:
            self.wait_ready(timeout)
            info = self.getLastTaskInfo()
            exception = info[5]
            if (exception != "") and (exception != "null"):
                raise exception
            return info[5]
        else:
            start = time.clock()
            while self.isTaskRunning(task_id):
                if (timeout > 0) and ((time.clock() - start) > timeout):
                    raise "Timeout waiting end of task"
                time.sleep(self.MONITORING_INTERVAL)
            return self.checkTaskResult(task_id)

    def checkTaskResult(self, task_id):
        return self.execute("checkTaskResult", (task_id,))

    def getTaskInfo(self, task_id):
        ret = self.execute("getLastTaskInfo", (task_id,))
        return self.parseArray(ret)

    def getLastTaskInfo(self):
        ret = self.execute("getLastTaskInfo", None)
        return self.parseArray(ret)

    def getLastTaskOutput(self):
        return self.execute("getLastTaskOutput", None)

    def getLastTaskException(self):
        return self.execute("getTaskException", None)

    # Positive = success, Negative = failure, 0 = aborted
    def getLastTaskResultCode(self):
        info = md.getLastTaskInfo()
        if info[6] == "null":
            return None
        task_result_code = int(info[6])
        return task_result_code

    def waitMotorReady(self, motor, timeout=0):
        start = time.clock()
        while True:
            state = self.getMotorState(motor)
            if state != self.STATE_MOVING:
                return
            if (timeout > 0) and ((time.clock() - start) > timeout):
                raise "Timeout waiting motor ready"
            time.sleep(self.MONITORING_INTERVAL)

    # Asynchronous tasks
    def execTask(self, task_name, pars=None, sync=False, timeout=DEFAULT_TASK_TIMEOUT):
        task_id = self.execute(task_name, pars)
        if sync:
            return self.waitTaskResult(task_id, timeout)
        else:
            return task_id

    def scan(self, sync=False, timeout=DEFAULT_TASK_TIMEOUT):
        return self.execTask("startScan", None, sync, timeout)

    def scanEx(
        self,
        frame_number,
        start_angle,
        scan_range,
        exposure_time,
        number_of_passes,
        sync=False,
        timeout=DEFAULT_TASK_TIMEOUT,
    ):
        return self.execTask(
            "startScanEx",
            (frame_number, start_angle, scan_range, exposure_time, number_of_passes),
            sync,
            timeout,
        )

    def scan4D(self, sync=False, timeout=DEFAULT_TASK_TIMEOUT):
        return self.execTask("startScan4D", None, sync, timeout)

    def scan4DEx(
        self,
        frame_number,
        start_angle,
        scan_range,
        exposure_time,
        start_y,
        start_z,
        start_cx,
        start_cy,
        stop_y,
        stop_z,
        stop_cx,
        stop_cy,
        sync=False,
        timeout=DEFAULT_TASK_TIMEOUT,
    ):
        return self.execTask(
            "startScan4D",
            (
                frame_number,
                start_angle,
                scan_range,
                exposure_time,
                start_y,
                start_z,
                start_cx,
                start_cy,
                stop_y,
                stop_z,
                stop_cx,
                stop_cy,
            ),
            sync,
            timeout,
        )

    def setTransferPhase(self, sync=False, timeout=DEFAULT_TASK_TIMEOUT):
        return self.execTask("startSetPhase", (self.PHASE_TRANSFER,), sync, timeout)

    def setCentringPhase(self, sync=False, timeout=DEFAULT_TASK_TIMEOUT):
        return self.execTask("startSetPhase", (self.PHASE_CENTRING,), sync, timeout)

    def setDataCollectionPhase(self, sync=False, timeout=DEFAULT_TASK_TIMEOUT):
        return self.execTask(
            "startSetPhase", (self.PHASE_DATA_COLLECTION,), sync, timeout
        )

    def setBeamLocationPhase(self, sync=False, timeout=DEFAULT_TASK_TIMEOUT):
        return self.execTask(
            "startSetPhase", (self.PHASE_BEAM_LOCATION,), sync, timeout
        )

    def autoSampleCentring(self, sync=False, timeout=DEFAULT_TASK_TIMEOUT):
        return self.execTask("startAutoSampleCentring", None, sync, timeout)

    def moveSampleOffBeam(self, sync=False, timeout=DEFAULT_TASK_TIMEOUT):
        return self.execTask("startMoveSampleOffBeam", None, sync, timeout)

    def moveSampleOnBeam(self, sync=False, timeout=DEFAULT_TASK_TIMEOUT):
        return self.execTask("startMoveSampleOnBeam", None, sync, timeout)

    def simultaneousMoveMotors(
        self, motor_position_dict, sync=False, timeout=DEFAULT_TASK_TIMEOUT
    ):
        list = self.createStringFromDict(motor_position_dict)
        return self.execTask("startSimultaneousMoveMotors", (list,), sync, timeout)

    def referenceMotor(self, motor, timeout=DEFAULT_TASK_TIMEOUT):
        return self.execTask("startHomingMotor", (motor,), sync, timeout)

    def moveOrganDevices(
        self,
        aperture_position,
        beamstop_position,
        capillary_position,
        scintillator_position,
        timeout=DEFAULT_TASK_TIMEOUT,
    ):
        return self.execTask(
            "startMoveOrganDevices",
            (
                aperture_position,
                beamstop_position,
                capillary_position,
                scintillator_position,
            ),
            sync,
            timeout,
        )

    # Syncronous methods
    def setScanParameters(self, start, range, time, passes):
        self.write_property("ScanStartAngle", start)
        self.write_property("ScanRange", range)
        self.write_property("ScanExposureTime", time)
        self.write_property("ScanNumberOfPasses", passes)

    def setStartScan4D(self):
        return self.execTask("setStartScan4D", None)

    def setStopScan4D(self):
        return self.execTask("setStopScan4D", None)

    def getDeviceState(self, device_name):
        return self.execute("getDeviceState", (device_name,))

    # Motors Returns STATE_READY,STATE_INVALID(not
    # referenced),STATE_INITIALIZING(referencing),STATE_MOVING,STATE_OFFLINE,
    # STATE_FAULT
    def getMotorState(self, motor_name):
        return self.execute("getMotorState", (motor_name,))

    def getMotorPosition(self, motor_name):
        ret = self.execute("getMotorPosition", (motor_name,))
        return float(ret)

    def setMotorPosition(self, motor_name, position, sync=False):
        self.execute("setMotorPosition", (motor_name, position))
        if sync:
            waitMotorReady(motor_name)

    def checkSyncMoveSafety(self, motor_position_dict):
        list = self.createStringFromDict(motor_position_dict)
        return self.execTask("checkSyncMoveSafety", (list,))

    def checkPositionSafety(self, motor_position_dict):
        list = self.createStringFromDict(motor_position_dict)
        return self.execTask("checkPositionSafety", (list,))

    def getMotorLimits(self, motor_name):
        ret = self.execute("getMotorLimits", (motor_name,))
        return self.parseArray(ret)

    def getMotorDynamicLimits(self, motor_name):
        ret = self.execute("getMotorDynamicLimits", (motor_name,))
        return self.parseArray(ret)

    def readPhotodiodeSignal(self, index):
        ret = self.execute("readPhotodiodeSignal", (index,))
        return float(ret)

    def setCentringClick(self, x, y):
        ret = self.execute("setCentringClick", (x, y))
        return float(ret)

    # Return array:
    #  - Aperture (POSITION_BEAM, POSITION_OFF,POSITION_PARK  or POSITION_UNKNOWN)
    #  - Beamstop (POSITION_BEAM, POSITION_OFF,POSITION_PARK  or POSITION_UNKNOWN)
    #  - Capillary (POSITION_BEAM, POSITION_OFF,POSITION_PARK  or POSITION_UNKNOWN)
    #  - Scintillator (POSITION_SCINTILLATOR, POSITION_PHOTODIODE, POSITION_PARK  or POSITION_UNKNOWN)
    def getOrganDevicesPositions(self):
        ret = self.execute("getOrganDevicesPositions", None)
        return self.parseArray(ret)

    def saveApertureBeamPosition(self):
        self.execute("saveApertureBeamPosition", None)

    def saveCapillaryBeamPosition(self):
        self.execute("saveCapillaryBeamPosition", None)

    def saveMotorizedBeamstopBeamPosition(self):
        self.execute("saveMotorizedBeamstopBeamPosition", None)

    def saveCentringPositions(self):
        self.execute("saveCentringPositions", None)

    def createStringFromDict(self, motor_position_dict):
        ret = ""
        for motor in motor_position_dict.keys():
            ret += motor + "=" + str(motor_position_dict[motor]) + ","
        return ret

    def createDictFromStringList(self, list):
        ret = {}
        for str in list:
            tokens = str.split("=")
            ret[tokens[0]] = tokens[1]
        return ret

    # Properties
    def getAlarmList(self):
        return self.read_property_as_string_array(self.PROPERTY_ALARM_LIST)

    def getMotorStates(self):
        array = self.read_property_as_string_array(self.PROPERTY_MOTOR_STATES)
        dict = self.createDictFromStringList(array)
        return dict

    def getMotorPositions(self):
        array = self.read_property_as_string_array(self.PROPERTY_MOTOR_POSITIONS)
        dict = self.createDictFromStringList(array)
        for key in dict.keys():
            dict[key] = float(dict[key])
        return dict

    def getVersion(self):
        return self.read_property(self.PROPERTY_VERSION)

    def getUptime(self):
        return self.read_property(self.PROPERTY_UPTIME)

    def getScanSpeed(self):
        return float(self.read_property(self.PROPERTY_SCAN_SPEED))

    def getScanPassDuration(self):
        return float(self.read_property(self.PROPERTY_SCAN_PASS_DURATION))

    def isSampleLoaded(self):
        return self.read_property(self.PROPERTY_SAMPLE_IS_LOADED) == "true"

    def isSampleCentred(self):
        return self.read_property(self.PROPERTY_SAMPLE_IS_CENTRED) == "true"

    def isSampleChangerUsed(self):
        return self.read_property(self.PROPERTY_USE_SAMPLE_CHANGER) == "true"

    def getScaleX(self):
        return float(self.read_property(self.PROPERTY_SCALE_X))

    def getScaleY(self):
        return float(self.read_property(self.PROPERTY_SCALE_Y))

    def isGUILocked(self):
        return self.read_property(self.PROPERTY_LOCKOUT) == "true"

    def setGUILocked(self, value):
        return self.write_property(self.PROPERTY_LOCKOUT, value)

    def isKappaEnabled(self):
        return self.read_property(self.PROPERTY_KAPPA_ENABLED) == "true"

    def setKappaEnabled(self, value):
        return self.write_property(self.PROPERTY_KAPPA_ENABLED, value)

    def isFastShutterOpen(self):
        return self.read_property(self.PROPERTY_FAST_SHUTTER_OPEN) == "true"

    def setFastShutterOpen(self, value):
        return self.write_property(self.PROPERTY_FAST_SHUTTER_OPEN, value)

    def isFluoDetectorBack(self):
        return self.read_property(self.PROPERTY_FLUO_DETECTOR_BACK) == "true"

    def setFluoDetectorBack(self, value):
        return self.write_property(self.PROPERTY_FLUO_DETECTOR_BACK, value)

    def isCryoBack(self):
        return self.read_property(self.PROPERTY_CRYO_BACK) == "true"

    def setCryoBack(self, value):
        return self.write_property(self.PROPERTY_CRYO_BACK, value)

    def isInterlockEnabled(self):
        return self.read_property(self.PROPERTY_INTERLOCK_ENABLED) == "true"

    def setInterlockEnabled(self, value):
        return self.write_property(self.PROPERTY_INTERLOCK_ENABLED, value)

    def getScanNumberOfPasses(self):
        return int(self.read_property(self.PROPERTY_SCAN_NUMBER_OF_PASSES))

    def setScanNumberOfPasses(self, value):
        return self.write_property(self.PROPERTY_SCAN_NUMBER_OF_PASSES, value)

    def getScanFrameNumber(self):
        return int(self.read_property(self.PROPERTY_FRAME_NUMBER))

    def setScanFrameNumber(self, value):
        return self.write_property(self.PROPERTY_FRAME_NUMBER, value)

    def getScanStartAngle(self):
        return float(self.read_property(self.PROPERTY_SCAN_START_ANGLE))

    def setScanStartAngle(self, value):
        return self.write_property(self.PROPERTY_SCAN_START_ANGLE, value)

    def getScanExposureTime(self):
        return float(self.read_property(self.PROPERTY_SCAN_EXPOSURE_TIME))

    def setScanExposureTime(self, value):
        return self.write_property(self.PROPERTY_SCAN_EXPOSURE_TIME, value)

    def getScanRange(self):
        return float(self.read_property(self.PROPERTY_SCAN_RANGE))

    def setScanRange(self, value):
        return self.write_property(self.PROPERTY_SCAN_RANGE, value)

    def getBeamSizeHorizontal(self):
        return float(self.read_property(self.PROPERTY_BEAM_SIZE_HORIZONTAL))

    def setBeamSizeHorizontal(self, value):
        return self.write_property(self.PROPERTY_BEAM_SIZE_HORIZONTAL, value)

    def getBeamSizeVertical(self):
        return self.read_propertyAsFloat(self.PROPERTY_BEAM_SIZE_VERTICAL)

    def setBeamSizeVertical(self, value):
        return self.write_property(self.PROPERTY_BEAM_SIZE_VERTICAL, value)

    def getFrontLightLevel(self):
        return float(self.read_property(self.PROPERTY_FRONT_LIGHT_LEVEL))

    def setFrontLightLevel(self, value):
        return self.write_property(self.PROPERTY_FRONT_LIGHT_LEVEL, value)

    def getBackLightLevel(self):
        return float(self.read_property(self.PROPERTY_BACK_LIGHT_LEVEL))

    def setBackLightLevel(self, value):
        return self.write_property(self.PROPERTY_BACK_LIGHT_LEVEL, value)

    def getSampleLoopSize(self):
        return self.read_propertyAsFloat(self.PROPERTY_SAMPLE_LOOP_SIZE)

    def setSampleLoopSize(self, value):
        return self.write_property(self.PROPERTY_SAMPLE_LOOP_SIZE, value)

    def getSampleHolderLength(self):
        return float(self.read_property(self.PROPERTY_SAMPLE_HOLDER_LENGTH))

    def setSampleHolderLength(self, value):
        return self.write_property(self.PROPERTY_SAMPLE_HOLDER_LENGTH, value)

    def getSampleUID(self):
        return self.read_property(self.PROPERTY_SAMPLE_UID)

    def setSampleUID(self, value):
        return self.write_property(self.PROPERTY_SAMPLE_UID, value)

    def getSampleLoopType(self):
        return self.read_property(self.PROPERTY_SAMPLE_LOOP_TYPE)

    def setSampleLoopType(self, value):
        return self.write_property(self.PROPERTY_SAMPLE_LOOP_TYPE, value)

    def getSampleImageName(self):
        return self.read_property(self.PROPERTY_SAMPLE_IMAGE_NAME)

    def setSampleImageName(self, value):
        return self.write_property(self.PROPERTY_SAMPLE_IMAGE_NAME, value)

    def getImageJPG(self):
        # TODO: OPTIMIZE
        return self.read_property_as_string_array(self.PROPERTY_IMAGE_JPG)


if __name__ == "__main__":

    class Microdiff(MDClient):
        state = MDClient.STATE_UNKNOWN
        task_finished = False

        def onConnected(self):
            print("     ******   CONNECTED   *******")

        def onDisconnected(self):
            print("     ******  DISCONNECTED  ******")

        def onEvent(self, name, value, timestamp):
            if name == self.STATE_EVENT:
                if self.state != value:
                    self.state = value
                    if self.isBusy(self.state) is False:
                        self.task_finished = True
            elif name == self.MOTOR_STATES_EVENT:
                array = self.parseArray(value)
                value = self.createDictFromStringList(array)
            print("     Event: " + name + " = " + str(value))

    md = Microdiff(SERVER_ADDRESS, SERVER_PORT, PROTOCOL.STREAM, TIMEOUT, RETRIES)

    methods = md.getMethodList()
    print("--------------   Listing methods  ------------------")
    print("Methods:")
    for method in methods:
        print(method)

    print("--------------   Listing properties  ------------------")
    properties = md.getPropertyList()
    print("Properties:")
    for property in properties:
        print(property)

    # Example recovering conection after a MD restart
    # It is not needed to call connect explicitly.
    # Connectiong is set with any command/attributr access.
    # Connection may be explicitly restored though to for receiving events
    if md.isConnected() is False:
        md.connect()

    # print("--------------   Just waiting  events  ------------------")
    # while True:
    #    time.sleep(md.MONITORING_INTERVAL)

    print("--------------   Calling a async task  ------------------")

    # Setting transfer phase synchronously (blocking)
    # md.setTransferPhase(sync=True)

    # Setting centring phase and monitoring the by task id
    task_id = md.setCentringPhase()
    task_output = md.waitTaskResult(task_id)

    # Setting data collection phase and monitoring the by app state
    # md.setDataCollectionPhase()
    # task_output=md.waitTaskResult()

    # Setting beam location phase and monitoring the by state event
    # md.task_finished=False
    # md.setBeamLocationPhase()
    # while md.task_finished==False:
    #    time.sleep(md.MONITORING_INTERVAL)

    task_result_code = md.getLastTaskResultCode()
    if task_result_code is None:
        print("Task still running")
    elif task_result_code > 0:
        print("Task succeeded")
    elif task_result_code < 0:
        print("Task failed" + md.getLastTaskException())
    elif task_result_code == 0:
        print("Task aborted")

    print("--------------   Executing a scan  --------------------")
    scan_time = 3.0
    md.setScanParameters(0.0, 1.0, 3.0, 1)
    md.scan(sync=True, timeout=(scan_time + md.DEFAULT_TASK_TIMEOUT))
    md.wait_ready()
    task_result_code = md.getLastTaskResultCode()
    if task_result_code is None:
        print("Scan still running")
    elif task_result_code > 0:
        print("Scan succeeded")
    elif task_result_code < 0:
        print("Scan failed" + md.getLastTaskException())
    elif task_result_code == 0:
        print("Scan aborted")
    print("--------------   Directly accessing motors --------------------")
    md.setMotorPosition(md.MOTOR_OMEGA, 10.0)
    md.setMotorPosition(md.MOTOR_PHI, 5.0)
    md.waitMotorReady(md.MOTOR_OMEGA)
    md.waitMotorReady(md.MOTOR_PHI)
    motor_position_dict = {md.MOTOR_OMEGA: 0.0, md.MOTOR_PHI: 0.0}
    md.simultaneousMoveMotors(motor_position_dict, sync=True)

    print("--------------   Reading all properties --------------------")
    # Reading all properties
    for property in properties:
        property_info = property.split(" ")
        property_type = property_info[0]
        property_name = property_info[1]
        property_access_type = property_info[2]

        if (
            property_access_type != md.PROPERTY_ACCESS_WRITE_ONLY
            and property_name != md.PROPERTY_IMAGE_JPG
        ):
            try:
                value = md.read_property(property_name)
                if property_type.endswith("[]"):
                    value = md.parseArray(value)
                print(property_name + " = " + str(value))
            except BaseException:
                print("Error reading " + property_name + ": " + str(sys.exc_info()[1]))

    print(
        "--------------   Reading/Writing all properties by their get/set methods --------------------"
    )
    print("State: " + md.get_state())
    print("State: " + md.getStatus())
    print("Alarms")
    print(md.getAlarmList())
    print("Motor states:")
    print(md.getMotorStates())
    print("Motor positions:")
    print(md.getMotorPositions())
    print("Version: " + md.getVersion())
    print("Uptime: " + md.getUptime())
    print("ScanSpeed: " + str(md.getScanSpeed()))
    print("ScanPassDuration: " + str(md.getScanPassDuration()))
    print("SampleLoaded: " + str(md.isSampleLoaded()))
    print("isSampleCentred: " + str(md.isSampleCentred()))
    print("isSampleChangerUsed: " + str(md.isSampleChangerUsed()))
    print("Scale X: " + str(md.getScaleX()))
    print("Scale Y: " + str(md.getScaleY()))

    val = md.isGUILocked()
    print("GUI locked: " + str(val))
    md.setGUILocked(val)

    val = md.isKappaEnabled()
    print("Kappa Enabled: " + str(val))
    md.setKappaEnabled(val)

    val = md.isFastShutterOpen()
    print("Fast Shutter Open: " + str(val))
    md.setFastShutterOpen(val)

    val = md.isFluoDetectorBack()
    print("Fluo Detector Back: " + str(val))
    md.setFluoDetectorBack(val)

    val = md.isCryoBack()
    print("Cryo Back: " + str(val))
    md.setCryoBack(val)

    val = md.isInterlockEnabled()
    print("Interlock Enabled: " + str(val))
    md.setInterlockEnabled(val)

    val = md.getScanNumberOfPasses()
    print("Scan Number Of Passes: " + str(val))
    md.setScanNumberOfPasses(val)

    val = md.getScanFrameNumber()
    print("Scan Frame Number: " + str(val))
    md.setScanFrameNumber(val)

    val = md.getScanStartAngle()
    print("Scan Start Angle: " + str(val))
    md.setScanStartAngle(val)

    val = md.getScanExposureTime()
    print("Scan Exposure Time: " + str(val))
    md.setScanExposureTime(val)

    val = md.getScanRange()
    print("Scan Range: " + str(val))
    md.setScanRange(val)

    val = md.getBeamSizeHorizontal()
    print("Beam Size Horizontal: " + str(val))
    md.setBeamSizeHorizontal(val)

    val = md.getBeamSizeVertical()
    print("Beam Size Vertical: " + str(val))
    md.setBeamSizeVertical(val)

    val = md.getFrontLightLevel()
    print("Front Light Level: " + str(val))
    md.setFrontLightLevel(val)

    val = md.getBackLightLevel()
    print("Back Light Level: " + str(val))
    md.setBackLightLevel(val)

    val = md.getBackLightLevel()
    print("Back Light Level: " + str(val))
    md.setBackLightLevel(val)

    val = md.getSampleLoopSize()
    print("Sample Loop Size: " + str(val))
    md.setSampleLoopSize(val)

    val = md.getSampleHolderLength()
    print("Sample Holder Length: " + str(val))
    md.setSampleHolderLength(val)

    val = md.getSampleUID()
    print("Sample UID: " + val)
    md.setSampleUID(val)

    val = md.getSampleLoopType()
    print("Sample Loop Type: " + val)
    md.setSampleLoopType(val)

    val = md.getSampleImageName()
    print("Sample Image Name: " + val)
    md.setSampleImageName(val)

    snapshot = md.getImageJPG()

    # Calling sync methods
    print("Pmac State: " + md.getDeviceState(md.DEVICE_PMAC))
    print("Omega State: " + md.getMotorState(md.MOTOR_OMEGA))
    print("Omega Position: " + str(md.getMotorPosition(md.MOTOR_OMEGA)))
    print("Organ Positions: " + str(md.getOrganDevicesPositions()))
    md.checkSyncMoveSafety({md.MOTOR_OMEGA: 180.0, md.MOTOR_KAPPA: 180.0})
    md.checkPositionSafety({md.MOTOR_OMEGA: 180.0, md.MOTOR_KAPPA: 180.0})
    md.setStartScan4D()
    md.setStopScan4D()
    md.setMotorPosition(md.MOTOR_PHI, 0.0, sync=False)
    print("Motor Y limits: " + str(md.getMotorLimits(md.MOTOR_Y)))
    print("Motor Y dynamic limits: " + str(md.getMotorDynamicLimits(md.MOTOR_Y)))
    print("Photodiode 0: " + str(md.readPhotodiodeSignal(0)))
    print("Photodiode 1: " + str(md.readPhotodiodeSignal(1)))

    md.disconnect()
