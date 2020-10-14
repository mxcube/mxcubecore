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


class MDEvents(ExporterClient):
    ##########################################################################
    # Constants
    ##########################################################################

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

    ##########################################################################
    # Auxiliary
    ##########################################################################
    def createDictFromStringList(self, list):
        ret = {}
        for str in list:
            tokens = str.split("=")
            ret[tokens[0]] = tokens[1]
        return ret

    ##########################################################################
    # Connection
    ##########################################################################

    started = False

    def start(self):
        self.started = True
        self.reconnect()

    def stop(self):
        self.started = False
        self.disconnect()

    def onConnected(self):
        pass

    def onDisconnected(self):
        if self.started:
            self.reconnect()

    def reconnect(self):
        if self.started:
            try:
                self.disconnect()
                self.connect()
            except Exception:
                # print sys.exc_info()
                t = threading.Timer(1.0, self.onDisconnected)
                t.start()

    ##########################################################################
    # Event receiving and callbacks
    ##########################################################################

    STATE_EVENT = "State"
    STATUS_EVENT = "Status"
    VALUE_EVENT = "Value"
    POSITION_EVENT = "Position"
    MOTOR_STATES_EVENT = "MotorStates"

    def onEvent(self, name, value, timestamp):
        if name == self.MOTOR_STATES_EVENT:
            array = self.parseArray(value)
            value = self.createDictFromStringList(array)
        self.onReceivedEvent(name, value, timestamp)

    def onReceivedEvent(self, name, value, timestamp):
        pass

    ##########################################################################
    # Testing
    ##########################################################################


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 1:
        SERVER_ADDRESS = args[0]

    class Microdiff(MDEvents):
        def onReceivedEvent(self, name, value, timestamp):
            print "     Event: " + name + " = " + str(value)

    md = Microdiff(SERVER_ADDRESS, SERVER_PORT, PROTOCOL.STREAM, TIMEOUT, RETRIES)
    md.start()

    while True:
        time.sleep(1.0)
        if not md.is_connected():
            print "Not Connected"

    md.stop()
