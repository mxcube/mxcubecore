import logging

from HardwareRepository.BaseHardwareObjects import Equipment


class DiffractometerMockup(Equipment):
    MANUAL3CLICK_MODE = "Manual 3-click"
    C3D_MODE = "Computer automatic"
    #MOVE_TO_BEAM_MODE = "Move to Beam"

    def __init__(self, *args):
        Equipment.__init__(self, *args)

        self.phiMotor = None
        self.phizMotor = None
        self.phiyMotor = None
        self.lightMotor = None
        self.zoomMotor = None
        self.sampleXMotor = None
        self.sampleYMotor = None
        self.camera = None
        self.sampleChanger = None
        self.lightWago = None
        self.currentSampleInfo = None
        self.aperture = None

        self.pixelsPerMmY = None
        self.pixelsPerMmZ = None
        self.imgWidth = None
        self.imgHeight = None

        self.connect(self, 'equipmentReady', self.equipmentReady)
        self.connect(self, 'equipmentNotReady', self.equipmentNotReady)

    def init(self):
        pass

    def setSampleInfo(self, sample_info):
        self.currentSampleInfo = sample_info

    def emitDiffractometerMoved(self, *args):
        self.emit("diffractometerMoved", ())

    def do_auto_loop_centring(self, n, old={"n": None}):
        pass

    def isReady(self):
        return self.isValid()

    def isValid(self):
        return True

    def apertureChanged(self, *args):
        # will trigger minidiffReady signal for update of beam size in video
        self.equipmentReady()

    def equipmentReady(self):
        self.emit('minidiffReady', ())

    def equipmentNotReady(self):
        self.emit('minidiffNotReady', ())

    def wagoLightStateChanged(self, state):
        pass

    def phiMotorStateChanged(self, state):
        self.emit('phiMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))

    def phizMotorStateChanged(self, state):
        self.emit('phizMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))

    def phiyMotorStateChanged(self, state):
        self.emit('phiyMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))

    def getCalibrationData(self, offset):
        if self.zoomMotor is not None:
            if self.zoomMotor.hasObject('positions'):
                for position in self.zoomMotor['positions']:
                    if position.offset == offset:
                        calibrationData = position['calibrationData']
                        return (float(calibrationData.pixelsPerMmY) or 0,
                                float(calibrationData.pixelsPerMmZ) or 0)
        return (None, None)

    def zoomMotorPredefinedPositionChanged(self, positionName, offset):
        self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(offset)
        self.emit('zoomMotorPredefinedPositionChanged',
                  (positionName, offset, ))

    def zoomMotorStateChanged(self, state):
        self.emit('zoomMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))

    def sampleXMotorStateChanged(self, state):
        self.emit('sampxMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))

    def sampleYMotorStateChanged(self, state):
        self.emit('sampyMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))

    def invalidateCentring(self):
        pass

    def phizMotorMoved(self, pos):
        self.invalidateCentring()

    def phiyMotorMoved(self, pos):
        self.invalidateCentring()

    def sampleXMotorMoved(self, pos):
        self.invalidateCentring()

    def sampleYMotorMoved(self, pos):
        self.invalidateCentring()

    def sampleChangerSampleIsLoaded(self, state):
        self.invalidateCentring()

    def moveToBeam(self, x, y):
        try:
            self.phizMotor.moveRelative((y - (self.imgHeight / 2)) /
                                        float(self.pixelsPerMmZ))
            self.phiyMotor.moveRelative((x - (self.imgWidth / 2)) /
                                        float(self.pixelsPerMmY))
        except:
            logging.getLogger("HWR").\
                exception("MiniDiff: could not center to beam, aborting")

    def getAvailableCentringMethods(self):
        pass

    def startCentringMethod(self, method, sample_info=None):
        pass

    def cancelCentringMethod(self, reject=False):
        pass

    def currentCentringMethod(self):
        pass

    def start3ClickCentring(self, sample_info=None):
        pass

    def motor_positions_to_screen(self, centred_positions_dict):
        pass

    def manualCentringDone(self, manual_centring_procedure):
        pass

    def moveToCentredPosition(self, centred_position):
        pass

    def autoCentringDone(self, auto_centring_procedure):
        pass

    def startAutoCentring(self, sample_info=None, loop_only=False):
        pass

    def imageClicked(self, x, y, xi, yi):
        pass

    def emitCentringStarted(self, method):
        pass

    def acceptCentring(self):
        pass

    def rejectCentring(self):
        pass

    def emitCentringMoving(self):
        pass

    def emitCentringFailed(self):
        pass

    def emitCentringSuccessful(self):
        pass

    def emitProgressMessage(self, msg=None):
        #logging.getLogger("HWR").debug("%s: %s", self.name(), msg)
        self.emit('progressMessage', (msg,))

    def getCentringStatus(self):
        pass

    def getPositions(self):
        return {"phi": self.phiMotor.getPosition(),
                "focus": self.focusMotor.getPosition(),
                "phiy": self.phiyMotor.getPosition(),
                "phiz": self.phizMotor.getPosition(),
                "sampx": self.sampleXMotor.getPosition(),
                "sampy": self.sampleYMotor.getPosition()}

    def takeSnapshots(self, wait=False):
        pass

    def snapshotsDone(self, snapshotsProcedure):
        pass

    def simulateAutoCentring(self, sample_info=None):
        pass
